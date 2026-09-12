"""Frozen, bounded teacher diagnostics for the architecture surfaces study."""

import argparse
import json
import shutil
import statistics
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from qi.artifacts import write_json
from qi.game import legal_moves
from qi.learning.snapshot import SnapshotTensors
from qi.learning.teacher_quality_scores import candidates, disadvantage
from qi.players.policy.encoding import input_key
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity, TeacherSession, digest
from qi.training_data.store import Collection

ROOT = Path(__file__).resolve().parents[4]
PHASES = ("repeat-100k", "single-1m", "all-legal-1m")
SOURCE_PATHS = (
    "data/experiments/learning/architecture-surfaces-v1/teacher_probe.py",
    "src/qi/teacher.py",
    "src/qi/learning/teacher_quality_scores.py",
    "src/qi/protocol.py",
    "src/qi/game.py",
    "src/qi/players/policy/encoding.py",
)


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ratio(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def distribution(values):
    return {
        "n": len(values),
        "min": min(values) if values else None,
        "median": statistics.median(values) if values else None,
        "mean": statistics.mean(values) if values else None,
        "max": max(values) if values else None,
    }


def check_protocol(config):
    require(config["version"] == "architecture-surfaces-v1", "Unsupported study version.")
    settings = config["teacher"]
    expected = {
        "per_cell": 8,
        "selection_salt": "architecture-surfaces-v1:",
        "nodes": [100000, 1000000],
        "multipv_nodes": 1000000,
        "threads": 1,
        "timeout_seconds": 20,
        "total_seconds": 900,
    }
    require(all(settings.get(k) == v for k, v in expected.items()), "Teacher settings differ from the frozen policy.")


def prepare(config):
    """Deterministic development-only selection; preserve the original history and answer."""
    check_protocol(config)
    spec = config["data"]
    cache_path = ROOT / spec["cache"]
    require(digest(cache_path / "manifest.json") == spec["manifest_sha256"], "Cache manifest changed.")
    cache = SnapshotTensors(cache_path)
    sealed_path = ROOT / spec["sealed_inputs"]
    require(digest(sealed_path) == spec["sealed_sha256"], "Sealed-input list changed.")
    sealed = {r["input"] for r in read(sealed_path)}
    buckets = defaultdict(list)
    for row in cache.rows("validation"):
        require(row["bucket"].startswith("development-"), "Only development rows may enter the probe.")
        require(row["input_hash"] not in sealed, "Development row intersects sealed inputs.")
        buckets[row["bucket"]].append(row)
    require(len(buckets) == 6 and sum(map(len, buckets.values())) == 373, "Development population changed.")
    selected = []
    for bucket, rows in sorted(buckets.items()):
        require(len(rows) >= 8, f"Insufficient development support: {bucket}")
        selected.extend(
            sorted(
                rows, key=lambda r: sha256((config["teacher"]["selection_salt"] + r["input_hash"]).encode()).hexdigest()
            )[:8]
        )
    snapshot = Path(cache.manifest["snapshot"])
    snapshot_manifest = read(snapshot / "manifest.json")
    evidence_path = snapshot / "evidence.sqlite"
    require(digest(evidence_path) == snapshot_manifest["files"]["evidence.sqlite"], "Frozen snapshot evidence changed.")
    preserved = []
    with Collection(evidence_path, readonly=True) as collection:
        for row in selected:
            original = collection.db.execute(
                "SELECT json(payload) FROM analyses WHERE attempt=? AND status='success'", (row["analysis"],)
            ).fetchone()
            require(original is not None, "Missing frozen original analysis.")
            original = TeacherAnalysis.model_validate(json.loads(original[0])["answer"])
            game = original.snapshot.game()
            require(
                (game.board, game.turn, input_key(game), original.move)
                == (row["board"], row["turn"], row["input_hash"], row["move"]),
                "Frozen history does not reproduce the selected row.",
            )
            require(len(game.moves) == row["ply_count"] and not game.outcome, "Invalid query history.")
            preserved.append(
                {
                    "row": row,
                    "snapshot": original.snapshot.model_dump(),
                    "original_analysis": original.model_dump(),
                    "legal_moves": list(legal_moves(game.board, game.turn)),
                }
            )
    inputs = {
        str(cache_path.relative_to(ROOT) / "manifest.json"): digest(cache_path / "manifest.json"),
        str(snapshot.relative_to(ROOT) / "manifest.json"): digest(snapshot / "manifest.json"),
        str(evidence_path.relative_to(ROOT)): digest(evidence_path),
        spec["sealed_inputs"]: digest(sealed_path),
    }
    for name, value in cache.manifest["files"].items():
        inputs[str(cache_path.relative_to(ROOT) / name)] = value
    return preserved, inputs


def receipts(output):
    return {
        str(path.relative_to(output)): digest(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name not in {"receipts.json", "verification.json"}
    }


def preview(config_path, output):
    config = read(config_path)
    selected, inputs = prepare(config)
    require(not output.exists(), "Choose a fresh teacher-probe output; prior evidence is retained.")
    output.mkdir(parents=True)
    write_json(output / "config.json", config, indent=2)
    write_json(output / "selection.json", selected, indent=2)
    for name in SOURCE_PATHS:
        target = output / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    manifest = {
        "version": "architecture-surfaces-teacher-v1",
        "selected_inputs": len(selected),
        "per_bucket": dict(Counter(item["row"]["bucket"] for item in selected)),
        "source_inputs": inputs,
        "source_files": {name: digest(ROOT / name) for name in SOURCE_PATHS},
        "queries": [
            {"name": "repeat-100k", "nodes": 100000, "multipv": 1, "show_wdl": False},
            {"name": "single-1m", "nodes": 1000000, "multipv": 1, "show_wdl": False},
            {"name": "all-legal-1m", "nodes": 1000000, "multipv": "all legal moves", "show_wdl": True},
        ],
        "settings": {"Threads": "1", "Hash": "16", "Ponder": "false", "depth": None},
        "planned_queries": len(selected) * len(PHASES),
        "session_policy": "One fresh TeacherSession per query; no retries or warm state.",
        "near_tie_definition": "Best-minus-second expected score <=0.01; forced positions excluded.",
        "saturation_definition": "Candidate WDL has one component 1000; also report expected score exactly 0 or 1.",
        "limitations": "48 inspected development inputs; finite teacher estimates without a playing-strength claim.",
    }
    write_json(output / "manifest.json", manifest, indent=2)
    write_json(output / "receipts.json", receipts(output), indent=2)
    return {"status": "preview", "selected": 48, "planned_queries": 144, "output": str(output)}


def expected_score(row):
    return (row["wdl"][0] + 0.5 * row["wdl"][1]) / 1000


def assessments(selected, records):
    answers = {(r["input_hash"], r["phase"]): r for r in records}
    result = []
    for item in selected:
        row = item["row"]
        key = row["input_hash"]
        observed = {"original": TeacherAnalysis.model_validate(item["original_analysis"])}
        detail = {
            "input_hash": key,
            "bucket": row["bucket"],
            "legal_count": len(item["legal_moves"]),
            "query_status": {},
        }
        for phase in PHASES:
            record = answers.get((key, phase))
            detail["query_status"][phase] = record["status"] if record else "not-started"
            if record and record["status"] == "success":
                observed[phase] = TeacherAnalysis.model_validate(record["analysis"])
        detail["search"] = {
            name: {
                "move": answer.move,
                "depth": answer.reported_depth,
                "nodes": answer.reported_nodes,
                "score": answer.score.model_dump() if answer.score else None,
            }
            for name, answer in observed.items()
        }
        detail["agreement"] = {}
        for label, first, second in (
            ("original_vs_repeat100k", "original", "repeat-100k"),
            ("repeat100k_vs_single1m", "repeat-100k", "single-1m"),
            ("original_vs_single1m", "original", "single-1m"),
            ("single1m_vs_alllegal1m", "single-1m", "all-legal-1m"),
        ):
            detail["agreement"][label] = (
                observed[first].move == observed[second].move if first in observed and second in observed else None
            )
        reference = (
            candidates(observed["all-legal-1m"])
            if "all-legal-1m" in observed
            else {"status": "unknown", "reason": "No successful all-legal query.", "moves": {}}
        )
        detail["candidate_reference"] = reference
        if reference["status"] == "complete":
            moves = list(reference["moves"].values())
            scores = sorted((expected_score(move) for move in moves), reverse=True)
            gap = scores[0] - scores[1] if len(scores) > 1 else None
            detail["candidate_diagnostic"] = {
                "common_depth": reference["depth"],
                "best_second_expected_score_gap": gap,
                "near_tie": gap <= 0.01 + 1e-12 if gap is not None else None,
                "candidate_count": len(moves),
                "pure_wdl_count": sum(max(move["wdl"]) == 1000 for move in moves),
                "expected_endpoint_count": sum(expected_score(move) in (0.0, 1.0) for move in moves),
                "best_expected_score": scores[0],
                "mate_candidate_count": sum(move["score"]["kind"] == "mate" for move in moves),
            }
        detail["move_estimates"] = {
            name: disadvantage(reference, answer.move) for name, answer in observed.items() if name != "all-legal-1m"
        }
        result.append(detail)
    return result


def aggregate(rows):
    summary = {
        "positions": len(rows),
        "forced_positions": sum(row["legal_count"] == 1 for row in rows),
        "queries": {phase: dict(Counter(row["query_status"][phase] for row in rows)) for phase in PHASES},
        "agreement": {},
        "search": {},
    }
    for label in rows[0]["agreement"] if rows else []:
        values = [row["agreement"][label] for row in rows if row["agreement"][label] is not None]
        summary["agreement"][label] = ratio(sum(values), len(values))
    for name in ("original", *PHASES):
        values = [row["search"][name] for row in rows if name in row["search"]]
        summary["search"][name] = {
            "successful_positions": len(values),
            "depth": distribution([v["depth"] for v in values if v["depth"] is not None]),
            "nodes": distribution([v["nodes"] for v in values if v["nodes"] is not None]),
            "score_status": dict(
                Counter(v["score"]["kind"] + ":" + v["score"]["bound"] if v["score"] else "missing" for v in values)
            ),
        }
    complete = [row["candidate_diagnostic"] for row in rows if "candidate_diagnostic" in row]
    ties = [row["near_tie"] for row in complete if row["near_tie"] is not None]
    candidates_n = sum(row["candidate_count"] for row in complete)
    summary["candidates"] = {
        "complete": ratio(len(complete), len(rows)),
        "unknown_reasons": dict(
            Counter(
                row["candidate_reference"]["reason"]
                for row in rows
                if row["candidate_reference"]["status"] != "complete"
            )
        ),
        "common_depth": distribution([row["common_depth"] for row in complete]),
        "near_tie_nonforced": ratio(sum(ties), len(ties)),
        "pure_wdl": ratio(sum(row["pure_wdl_count"] for row in complete), candidates_n),
        "expected_endpoints": ratio(sum(row["expected_endpoint_count"] for row in complete), candidates_n),
        "mate_candidates": ratio(sum(row["mate_candidate_count"] for row in complete), candidates_n),
    }
    summary["estimated_move_loss"] = {}
    for name in ("original", "repeat-100k", "single-1m"):
        estimates = [row["move_estimates"][name] for row in rows if name in row["move_estimates"]]
        summary["estimated_move_loss"][name] = {
            "expected_score": distribution(
                [v["expected_score_loss"] for v in estimates if v["expected_score_loss"] is not None]
            ),
            "cp_gap_cp_only_positions": distribution([v["cp_gap"] for v in estimates if v["cp_gap"] is not None]),
            "unknown": sum(v["status"] == "unknown" for v in estimates),
        }
    return summary


def summarize(selected, records):
    rows = assessments(selected, records)
    return rows, {
        "all": aggregate(rows),
        "by_bucket": {
            bucket: aggregate([r for r in rows if r["bucket"] == bucket])
            for bucket in sorted({r["bucket"] for r in rows})
        },
        "scope": "Descriptive teacher stability and finite candidate estimates on 48 selected development inputs.",
    }


def verify_preview(config_path, output):
    config = read(config_path)
    require(config == read(output / "config.json"), "Protocol differs from preview.")
    saved_receipts = read(output / "receipts.json")
    for name, expected in saved_receipts.items():
        require(digest(output / name) == expected, f"Receipt mismatch: {name}")
    selected, inputs = prepare(config)
    require(selected == read(output / "selection.json"), "Selection/history changed.")
    manifest = read(output / "manifest.json")
    require(inputs == manifest["source_inputs"], "Frozen source input identity changed.")
    for name, expected in manifest["source_files"].items():
        require(digest(ROOT / name) == expected, f"Probe implementation changed: {name}")
        require(digest(output / "source" / name) == expected, f"Preserved source changed: {name}")
    return config, selected


def run(config_path, output):
    started = perf_counter()
    config, selected = verify_preview(config_path, output)
    require(not (output / "status.json").exists(), "Probe already started; no retries or automatic extensions.")
    settings = config["teacher"]
    deadline = started + settings["total_seconds"]
    base = TeacherConfig(
        ROOT / settings["engine"], ROOT / settings["network"], depth=None, nodes=100000, timeout_seconds=20
    )
    identity = TeacherIdentity.read(base)
    require(
        (identity.engine_sha256, identity.network_sha256) == (settings["engine_sha256"], settings["network_sha256"]),
        "Teacher files differ from the protocol.",
    )
    records = []
    state = {"status": "running", "planned_queries": 144, "started_queries": 0, "successful_queries": 0, "seconds": 0}

    def save():
        state["seconds"] = perf_counter() - started
        state["successful_queries"] = sum(r["status"] == "success" for r in records)
        write_json(output / "status.json", state, indent=2)

    save()
    try:
        with (output / "answers.jsonl").open("x") as log, (output / "events.jsonl").open("x") as events:
            for item in selected:
                game = Snapshot.model_validate(item["snapshot"]).game()
                for phase in PHASES:
                    remaining = deadline - perf_counter()
                    if remaining <= 0:
                        state["status"] = "deadline"
                        break
                    tick = perf_counter()
                    query = TeacherConfig(
                        base.engine,
                        base.network,
                        nodes=100000 if phase == "repeat-100k" else 1000000,
                        depth=None,
                        timeout_seconds=min(20, remaining),
                        multipv=len(item["legal_moves"]) if phase == "all-legal-1m" else 1,
                        show_wdl=phase == "all-legal-1m",
                        threads=1,
                    )
                    record = {
                        "input_hash": item["row"]["input_hash"],
                        "bucket": item["row"]["bucket"],
                        "phase": phase,
                        "started_at_seconds": tick - started,
                        "timeout_seconds": query.timeout_seconds,
                    }
                    events.write(json.dumps({**record, "event": "query-start"}) + "\n")
                    events.flush()
                    state["started_queries"] += 1
                    save()
                    interrupted = False
                    try:
                        with TeacherSession(query, identity=identity) as session:
                            answer = session.analyze(game, query)
                        record.update(status="success", analysis=answer.model_dump())
                    except BaseException as exc:
                        interrupted = isinstance(exc, (KeyboardInterrupt, SystemExit))
                        record.update(
                            status="interrupted" if interrupted else "failed",
                            error={"type": type(exc).__name__, "message": str(exc)},
                        )
                    record["seconds"] = perf_counter() - tick
                    log.write(json.dumps(record) + "\n")
                    log.flush()
                    records.append(record)
                    save()
                    print(
                        json.dumps(
                            {
                                "query": len(records),
                                "phase": phase,
                                "status": record["status"],
                                "seconds": round(state["seconds"], 3),
                            }
                        ),
                        flush=True,
                    )
                    if interrupted:
                        state["status"] = "interrupted"
                        break
                if state["status"] != "running":
                    break
        if state["status"] == "running":
            state["status"] = "complete" if all(r["status"] == "success" for r in records) else "complete-with-failures"
        require(TeacherIdentity.read(base) == identity, "Teacher identity changed during execution.")
    except BaseException as exc:
        state.update(
            status="interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed",
            error={"type": type(exc).__name__, "message": str(exc)},
        )
    finally:
        state["query_work_seconds"] = perf_counter() - started
        rows, summary = summarize(selected, records)
        write_json(output / "assessments.json", rows, indent=2)
        write_json(output / "summary.json", summary, indent=2)
        save()
        write_json(output / "receipts.json", receipts(output), indent=2)
    return state


def verify(config_path, output):
    config, selected = verify_preview(config_path, output)
    if not (output / "status.json").exists():
        result = {"verified": True, "scope": "preview-selection-history-hashes", "selected": len(selected)}
        write_json(output / "verification.json", result, indent=2)
        return result
    state = read(output / "status.json")
    records = [json.loads(line) for line in (output / "answers.jsonl").read_text().splitlines()]
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    require(len(events) == len(records) == state["started_queries"], "Started/completed attempt accounting mismatch.")
    lookup = {item["row"]["input_hash"]: item for item in selected}
    expected_order = [(item["row"]["input_hash"], phase) for item in selected for phase in PHASES]
    require(
        [(r["input_hash"], r["phase"]) for r in records] == expected_order[: len(records)],
        "Query order differs from frozen order.",
    )
    for record, event in zip(records, events, strict=True):
        require(
            event
            == {
                **{k: record[k] for k in ("input_hash", "bucket", "phase", "started_at_seconds", "timeout_seconds")},
                "event": "query-start",
            },
            "Query-start receipt mismatch.",
        )
        require(
            0 <= record["started_at_seconds"] < 900
            and 0 < record["timeout_seconds"] <= min(20, 900 - record["started_at_seconds"]) + 0.001,
            "Query exceeded scheduling allowance.",
        )
        require(record["status"] in {"success", "failed", "interrupted"}, "Unknown query status.")
        if record["status"] != "success":
            require(bool(record.get("error")), "Failed query lost its error.")
            continue
        item = lookup[record["input_hash"]]
        answer = TeacherAnalysis.model_validate(record["analysis"])
        game = answer.snapshot.game()
        multi = record["phase"] == "all-legal-1m"
        require(
            answer.snapshot.model_dump() == item["snapshot"]
            and input_key(game) == record["input_hash"]
            and answer.state_hash == game.state_hash,
            "Teacher answer input/history changed.",
        )
        require(answer.move in item["legal_moves"], "Teacher move is illegal.")
        require(
            (answer.engine_sha256, answer.network_sha256)
            == (config["teacher"]["engine_sha256"], config["teacher"]["network_sha256"]),
            "Teacher answer identity mismatch.",
        )
        require(
            answer.requested_nodes == (100000 if record["phase"] == "repeat-100k" else 1000000)
            and answer.requested_depth is None
            and answer.timeout_seconds == record["timeout_seconds"],
            "Teacher answer budget mismatch.",
        )
        require(
            answer.settings["Threads"] == "1"
            and answer.settings["Hash"] == "16"
            and answer.settings["MultiPV"] == str(len(item["legal_moves"]) if multi else 1),
            "Teacher answer settings mismatch.",
        )
        require((answer.settings.get("UCI_ShowWDL") == "true") == multi, "WDL settings mismatch.")
    require(
        state["successful_queries"] == sum(r["status"] == "success" for r in records), "Success denominator mismatch."
    )
    if state["status"] in {"complete", "complete-with-failures"}:
        require(len(records) == 144, "Incomplete matrix labeled complete.")
    if state["status"] == "complete":
        require(all(r["status"] == "success" for r in records), "Failed queries labeled complete.")
    rows, summary = summarize(selected, records)
    require(
        rows == read(output / "assessments.json") and summary == read(output / "summary.json"),
        "Independent raw-answer reparsing differs from retained assessments.",
    )
    result = {
        "verified": True,
        "status": state["status"],
        "queries": len(records),
        "successful_queries": state["successful_queries"],
        "selected": len(selected),
        "scope": "Receipts, selection, replay, query settings/order, candidate reparsing and denominators; offline.",
    }
    write_json(output / "verification.json", result, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("preview", "run", "verify"), required=True)
    args = parser.parse_args()
    functions = {"preview": preview, "run": run, "verify": verify}
    print(json.dumps(functions[args.stage](args.config.resolve(), args.output.resolve())), flush=True)


if __name__ == "__main__":
    main()
