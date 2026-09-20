"""One frozen real-teacher generation cell with OS/SQL accounting and data verification."""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from time import perf_counter

from qi_game.reference import restore

from qi.artifacts import provenance, write_json
from qi.training_data.contracts import Example
from qi.training_data.generation_runner import PolicyGenerationConfig, SessionProvider, generate_policies, pin_teachers
from qi.training_data.resource_probe import ResourceProbe
from qi.training_data.store import AnalysisPayload, Collection


def verify(store: Collection, result: dict) -> dict:
    assert store.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not store.db.execute("PRAGMA foreign_key_check").fetchall()
    games = analyses = 0
    outcomes, reasons, phases, referee = Counter(), Counter(), Counter(), Counter()
    interventions = eligible_interventions = 0
    plies = 0
    for row in store.db.execute("SELECT id,stop_reason FROM games WHERE status='complete' ORDER BY id"):
        source = store.game(row[0])
        replayed = restore(source.snapshot)
        referee[replayed.outcome.reason if replayed.outcome else "unfinished"] += 1
        generation = source.actor["generation_result"]
        count = len(source.snapshot.moves) - len(source.initial.moves)
        assert len(generation["decisions"]) == count
        for decision in generation["decisions"]:
            assert source.snapshot.moves[decision["ply"]] == decision["move"]
        plies += count
        reasons.update(generation["decision_reasons"])
        phases.update(generation["sampling"]["actual"])
        if generation["policy"] == "intervention":
            eligible_interventions += 1
            interventions += generation["intervention_applied"]
            assert sum(d["intervention"] for d in generation["decisions"]) <= 1
        for phase, requested in generation["sampling"]["requested"].items():
            assert requested == generation["sampling"]["actual"][phase] + generation["sampling"]["shortfall"][phase]
        outcomes[row[1]] += 1
        games += 1
    for row in store.db.execute("SELECT occurrence_id,json(payload) FROM analyses WHERE status='success'"):
        payload = AnalysisPayload.model_validate_json(row[1])
        assert payload.answer.snapshot == store.snapshot(row[0])
        Example(analysis=payload.answer, source_ids=["verification"])
        analyses += 1
    assert games == result["games"]
    selected = store.db.execute(
        "SELECT count(*) FROM position_occurrences WHERE json_extract(payload,'$.metadata.selected')=1"
    ).fetchone()[0]
    unique = store.db.execute(
        "SELECT count(DISTINCT input_hash) FROM position_occurrences "
        "WHERE json_extract(payload,'$.metadata.selected')=1"
    ).fetchone()[0]
    assert selected == sum(result["selected_by_phase"].values())
    return {
        "games": games,
        "successful_analyses": analyses,
        "selected": selected,
        "unique_selected": unique,
        "continuation_plies": plies,
        "stop_reasons": dict(outcomes),
        "referee_outcomes": dict(referee),
        "decision_reasons": dict(reasons),
        "phases": dict(phases),
        "interventions": interventions,
        "intervention_games": eligible_interventions,
        "pragma": {
            name: store.db.execute("PRAGMA " + name).fetchone()[0]
            for name in ("journal_mode", "synchronous", "page_size", "cache_size", "wal_autocheckpoint")
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = PolicyGenerationConfig.model_validate_json(args.config.read_text()).resolve(args.config.resolve().parent)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "config.json", config.model_dump(), indent=2)
    origin = provenance()
    write_json(args.output / "provenance.json", origin, indent=2)
    root = Path(__file__).resolve().parents[1]
    for path in [
        *sorted((root / "src/qi").rglob("*.py")),
        Path(__file__).resolve(),
        root / "pyproject.toml",
        root / "uv.lock",
    ]:
        target = args.output / "source" / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    path = args.output / "collection.sqlite"
    probe = ResourceProbe(path)
    checkpoints = []
    total = sum(source.games for source in config.sources)
    result = {"status": "failed"}
    try:
        with (
            Collection(path) as store,
            SessionProvider(pin_teachers(config)) as provider,
            (args.output / "games.jsonl").open("x") as journal,
        ):
            store.db.set_trace_callback(probe.trace)
            count = 0

            def event(value):
                nonlocal count
                if value["kind"] != "completed-game":
                    return
                count += 1
                game = value["result"]
                pids = [session.engine.process.pid for session in provider.sessions.values() if session.engine]
                sample = probe.snapshot(pids)
                journal.write(
                    json.dumps(
                        {
                            "game": count,
                            "source": game["source"],
                            "sampling": game["sampling"],
                            "decision_reasons": game["decision_reasons"],
                            "resource": sample,
                        }
                    )
                    + "\n"
                )
                journal.flush()
                if count in {8, 32, total}:
                    selected = store.db.execute(
                        "SELECT count(DISTINCT input_hash) FROM position_occurrences "
                        "WHERE json_extract(payload,'$.metadata.selected')=1"
                    ).fetchone()[0]
                    checkpoint = {"games": count, "unique_selected": selected, "resource": sample}
                    checkpoints.append(checkpoint)
                    write_json(args.output / "progress.json", checkpoint, indent=2)
                    print(
                        json.dumps(
                            {
                                "cell": config.name,
                                "games": count,
                                "unique_selected": selected,
                                "seconds": round(sample["elapsed_seconds"], 2),
                                "disk_written": sample["disk_write_bytes"],
                                "db_wal": sample["files"],
                            }
                        ),
                        flush=True,
                    )
                if (
                    sample["peak_sampled_combined_rss_bytes"] > 1_500_000_000
                    or (sample["disk_write_bytes"] or 0) > 4_000_000_000
                ):
                    raise RuntimeError("Predeclared per-cell memory or OS write guard exceeded.")

            started = perf_counter()
            result = generate_policies(store, config, provider=provider, event=event)
            result["generation_wall_seconds"] = perf_counter() - started
            result["generation_resource"] = probe.snapshot(
                [s.engine.process.pid for s in provider.sessions.values() if s.engine]
            )
            store.db.set_trace_callback(None)
            tick = perf_counter()
            result["verification"] = verify(store, result)
            result["verification_seconds"] = perf_counter() - tick
            tick = perf_counter()
            result["checkpoint"] = list(store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
            result["checkpoint_seconds"] = perf_counter() - tick
        result["closed_resource"] = probe.snapshot()
        with Collection(path, readonly=True) as store:
            assert store.counts()["games"] == total
            assert store.db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        result["checkpoints"] = checkpoints
    except BaseException as exc:
        result.update(
            status="failed",
            failure=f"{type(exc).__name__}: {exc}",
            failure_resource=probe.snapshot(),
            checkpoints=checkpoints,
        )
        raise
    finally:
        result["source_sha256"] = origin["source_sha256"]
        result["source_changed"] = provenance()["source_sha256"] != origin["source_sha256"]
        write_json(args.output / "results.json", result, indent=2)
        print(
            json.dumps({"cell": config.name, "status": result["status"], "results": str(args.output / "results.json")}),
            flush=True,
        )


if __name__ == "__main__":
    main()
