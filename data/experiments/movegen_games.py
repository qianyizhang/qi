"""AB-EVAL-007 follow-up: shared evaluation runner with a timing-calibrated node cap."""

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from time import perf_counter

from qi.artifacts import provenance, write_json
from qi.benchmark.models import Book
from qi.evaluation import EvalGame, EvalRun, EvalSpec, run_evaluation, summarize_evaluation
from qi.game import legal_moves, replay
from qi.players import PlayerConfig, bind_config
from qi.players.catalog import get_player


class DeadlineReached(Exception):
    pass


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory):
    manifest = json.loads((directory / "games-manifest.json").read_text())
    for path, expected in manifest["frozen_files"].items():
        if sha(directory / path) != expected:
            raise ValueError(f"Frozen input changed: {path}")
    results = {}
    completed = failed = 0
    for name in manifest["runs"]:
        path = directory / f"games-{name}.json"
        run = EvalRun.model_validate_json(path.read_text())
        summary = summarize_evaluation(run).model_dump(mode="json")
        costs = {}
        for who in ("a", "b"):
            choices = [
                t.choice for g in run.games if g.match for t in g.match.turns if (t.side == g.a_side) == (who == "a")
            ]
            n = len(choices)
            costs[who] = {
                "decisions": n,
                "mean_move_ms": sum(c.elapsed_ms for c in choices) / n if n else None,
                "mean_completed_depth": sum(c.completed_depth for c in choices) / n if n else None,
                "fallbacks": sum(c.completed_depth == 0 for c in choices if c.engine is None),
                "qi_nodes": sum(c.nodes for c in choices),
                "engine_nodes": sum(c.engine.reported_nodes or 0 for c in choices if c.engine),
            }
        completed += summary["players"]["a"]["completed_games"]
        failed += summary["players"]["a"]["failed_games"]
        results[name] = {
            "summary": summary,
            "costs": costs,
            "terminations": dict(Counter(g.match.reason for g in run.games if g.match)),
            "sha256": sha(path),
        }
    result = {
        "id": "movegen-20260915",
        "planned_games": 40,
        "completed_games": completed,
        "failed_games": failed,
        "selected_nodes": manifest["selected_nodes"],
        "game_elapsed_seconds": manifest.get("game_elapsed_seconds"),
        "runs": results,
        "verified": True,
        "manifest_sha256": sha(directory / "games-manifest.json"),
    }
    write_json(directory / "games-summary.json", result, indent=2)
    return result


def execute(directory):
    performance = json.loads((directory / "performance.json").read_text())
    if not performance["adoption_speed_criterion_passed"]:
        raise ValueError("The fixed speed criterion must pass before follow-up games.")
    hashes = json.loads((directory / "after-hashes.json").read_text())
    for path, expected in hashes.items():
        if sha(Path(path)) != expected:
            raise ValueError(f"Runtime source changed since measurement: {path}")
    book = Book.model_validate_json(Path("data/evaluation/human-openings-v1/development.json").read_text())
    if book.use != "development":
        raise ValueError("Only development books are allowed.")
    starts = []
    families = set()
    for start in book.starts:
        if start.family not in families:
            families.add(start.family)
            starts.append(start)
        if len(starts) == 20:
            break
    if len(starts) != 20:
        raise ValueError("Insufficient development families.")
    old = json.loads((directory / "probe-starts.json").read_text())
    assert [s.id for s in starts[:12]] == [s["id"] for s in old]
    fresh = starts[12:20]
    selected = performance["selected_nodes"]
    if selected == 1024:
        raise ValueError("No larger cap fits the latency envelope; identical self-play is not the planned control.")
    candidate = bind_config(PlayerConfig("alphabeta-pvs", seed=7, nodes=selected, depth=4))
    opponents = {
        "small": bind_config(
            PlayerConfig("pikafish-benchmark", seed=7, nodes=1000, depth=3, work_semantics="engine_native")
        ),
        "large": bind_config(
            PlayerConfig("pikafish-benchmark", seed=7, nodes=100000, depth=8, work_semantics="engine_native")
        ),
        "control": bind_config(PlayerConfig("alphabeta-pvs", seed=7, nodes=1024, depth=4)),
    }
    info = provenance()
    specs = {}
    manifest = {
        "id": "movegen-20260915",
        "selected_nodes": selected,
        "runs": list(opponents),
        "provenance": info,
        "frozen_files": {
            name: sha(directory / name)
            for name in ["performance.json", "equivalence.json", "after-hashes.json", "probe-starts.json"]
        },
        "start_selection": "Next eight unique development families after the 12 prior starts; first four for control.",
    }
    if (directory / "games-manifest.json").exists():
        raise ValueError("A fresh game execution is required.")
    shutil.copy2(Path(__file__), directory / "movegen_games.py")
    for name in ("movegen_games.py", "movegen_optimization.py", "before-hashes.json"):
        manifest["frozen_files"][name] = sha(directory / name)
    for label in ("before", "after"):
        for path, expected in json.loads((directory / f"{label}-hashes.json").read_text()).items():
            manifest["frozen_files"][f"{label}/{path}"] = expected
        for path in directory.glob(f"{label}-*.json"):
            manifest["frozen_files"][path.name] = sha(path)
    for name, opponent in opponents.items():
        chosen = fresh[:4] if name == "control" else fresh
        spec = EvalSpec(
            schema_version=2 if opponent.binding_sha256 else 1,
            corpus=book.corpus([s.id for s in chosen]),
            player_a=candidate,
            player_b=opponent,
        )
        specs[name] = spec
        run = EvalRun(
            schema_version=spec.schema_version,
            spec=spec,
            spec_sha256=spec.digest,
            provenance=info,
            player_versions={"a": get_player(candidate.kind).info.version, "b": get_player(opponent.kind).info.version},
            games=[EvalGame(opening_id=s.id, a_side=side) for s in chosen for side in ("red", "black")],
        )
        write_json(directory / f"games-{name}.json", run.model_dump(mode="json"))
        write_json(directory / f"spec-{name}.json", spec.model_dump(mode="json"), indent=2)
        manifest["frozen_files"][f"spec-{name}.json"] = sha(directory / f"spec-{name}.json")
    write_json(directory / "games-manifest.json", manifest, indent=2)
    start_time = perf_counter()
    deadline = start_time + 1800
    for name, spec in specs.items():
        prior_complete = 0

        def persist(run, name=name):
            nonlocal prior_complete
            expired = perf_counter() >= deadline and any(g.status == "running" for g in run.games)
            if expired:
                for entry in run.games:
                    if entry.status == "running":
                        entry.status = "pending"
            write_json(directory / f"games-{name}.json", run.model_dump(mode="json"))
            complete = [g for g in run.games if g.match]
            if len(complete) > prior_complete:
                last = complete[-1]
                result = "D" if last.match.winner is None else "W" if last.match.winner == last.a_side else "L"
                print(
                    f"{name} {len(complete)}/{len(run.games)} {result} {last.match.reason} "
                    f"{len(last.match.turns)} plies; {perf_counter() - start_time:.1f}s",
                    flush=True,
                )
                prior_complete = len(complete)
            if expired:
                raise DeadlineReached
            if any(g.status == "running" for g in run.games):
                legal_moves.cache_clear()
                replay.cache_clear()

        try:
            run = run_evaluation(spec, save=persist)
            if any(g.status in ("failed", "incomplete") for g in run.games):
                break
        except DeadlineReached:
            break
    manifest["game_elapsed_seconds"] = perf_counter() - start_time
    manifest["frozen_files"].update({f"games-{name}.json": sha(directory / f"games-{name}.json") for name in specs})
    write_json(directory / "games-manifest.json", manifest, indent=2)
    result = verify(directory)
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.run), indent=2))
    else:
        execute(args.run)
