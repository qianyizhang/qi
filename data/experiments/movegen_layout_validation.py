"""AB-EVAL-008 frozen equivalence and isolated baseline/ablation/final timings.

Run --prepare after implementing a candidate, then --measure. Outputs must be
fresh. Depends on the retained AB-EVAL-007 inputs and its shared timing worker.
"""

import argparse
import importlib.util
import json
import shutil
import statistics
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from movegen_optimization import ROOT, deterministic, load_before, measured, save, sha


def deep_size(value, seen=None):
    """Reachable Python object sizes, deduplicated; not process RSS."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (tuple, list)):
        size += sum(deep_size(v, seen) for v in value)
    return size


def prepare(run):
    outputs = ("after", "after-hashes.json", "equivalence.json", "replay-histories.json", "manifest.json")
    if any((run / name).exists() for name in outputs):
        raise ValueError("Use a fresh preparation output directory; existing evidence must be preserved.")
    import qi.game as current
    from qi.evaluation import EvalRun
    from qi.players.components.positional import breakdown

    before = load_before(run)
    for relative, expected in json.loads((run / "before-hashes.json").read_text()).items():
        assert sha(run / "before" / relative) == expected
    spec = importlib.util.spec_from_file_location(
        "before_positional", run / "before/src/qi/players/components/positional/__init__.py"
    )
    old_evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_evaluation)
    old_evaluation.legal_moves = before.legal_moves
    inputs = json.loads((run / "positions.json").read_text())
    boards = [*inputs["boards"], *inputs["arbitrary_boards"]]
    for i, board in enumerate(boards):
        for side in ("red", "black"):
            assert current.in_check(board, side) == before.in_check(board, side), (i, side, "check")
            assert current.legal_moves(board, side) == before.legal_moves(board, side), (i, side, "moves")
            game = current.Game(board=board, turn=side)
            assert breakdown(game) == old_evaluation.breakdown(game), (i, side, "evaluation")
    for i, board in enumerate(inputs["arbitrary_boards"]):
        for side in ("red", "black"):
            for target in range(90):
                expected = any(
                    piece != "." and before.owner(piece) == side and before.reaches(board, source, target)
                    for source, piece in enumerate(board)
                )
                assert current.is_attacked(board, target, side) == expected, (i, side, target)
    histories = inputs["prior_histories"].copy()
    prior = ROOT / "artifacts/experiments/movegen-20260915"
    for label in ("small", "large", "control"):
        evidence = EvalRun.model_validate_json((prior / f"games-{label}.json").read_text())
        for entry in evidence.games:
            assert entry.match is not None
            histories.append(list(entry.match.snapshot.moves))
    for history in histories:
        old, new = before.replay(tuple(history)), current.replay(tuple(history))
        assert (old.board, old.turn, asdict(old.outcome)) == (new.board, new.turn, asdict(new.outcome))

    def perft(module, game, depth):
        moves = module.legal_moves(game.board, game.turn)
        if depth == 1:
            return len(moves)
        return sum(perft(module, game.apply(move), depth - 1) for move in moves)

    counts = {name: perft(module, module.Game(), 3) for name, module in (("before", before), ("after", current))}
    assert counts == {"before": 79666, "after": 79666}
    setup = {}
    for name, module in (("before", before), ("after", current)):
        times = []
        for _ in range(100):
            started = perf_counter()
            module._movement_tables()
            if hasattr(module, "_safety_tables"):
                module._safety_tables()
            times.append((perf_counter() - started) * 1000)
        tables = [module._STEPS, module._RAYS, module._ATTACKERS, module._SQUARES]
        if hasattr(module, "_SAFETY"):
            tables.extend((module._SAFETY, module._BITS))
        setup[name] = {"rows_ms": times, "median_ms": statistics.median(times), "table_python_bytes": deep_size(tables)}
    result = {
        "board_side_queries": len(boards) * 2,
        "ordered_moves_equal": True,
        "checks_equal": True,
        "evaluation_breakdowns_equal": True,
        "arbitrary_target_queries": len(inputs["arbitrary_boards"]) * 180,
        "arbitrary_target_attacks_equal": True,
        "complete_games_replayed": len(histories),
        "terminal_outcomes_equal": True,
        "perft_depth_three": counts,
        "setup": setup,
    }
    save(run / "equivalence.json", result)
    save(run / "replay-histories.json", histories)
    after = run / "after"
    after.mkdir(exist_ok=False)
    paths = [*ROOT.joinpath("src/qi").rglob("*.py"), ROOT / "pyproject.toml", ROOT / "uv.lock"]
    for path in paths:
        target = after / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    save(run / "after-hashes.json", {str(p.relative_to(ROOT)): sha(p) for p in paths})
    for script in (
        Path(__file__),
        Path(__file__).with_name("movegen_layout.py"),
        Path(__file__).with_name("movegen_optimization.py"),
    ):
        shutil.copy2(script, run / script.name)
    save(
        run / "manifest.json",
        {
            "produced_by": "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15",
            "files": {str(p.relative_to(run)): sha(p) for p in run.glob("*.json") if p.name != "manifest.json"},
        },
    )
    print({k: v for k, v in result.items() if k != "setup"}, flush=True)
    print({k: {x: y for x, y in v.items() if x != "rows_ms"} for k, v in setup.items()}, flush=True)


def measure(run):
    rounds = []
    for repeat in range(3):
        pair = {}
        labels = ("before", "masks-only", "after") if repeat % 2 == 0 else ("after", "masks-only", "before")
        for label in labels:
            pair[label] = {"legal": measured(run, label, "legal", 1024, repeat)}
            for nodes in (1024, 4096):
                pair[label][str(nodes)] = measured(run, label, "search", nodes, repeat)
        record = {}
        for mode in ("legal", "1024", "4096"):
            baseline = pair["before"][mode]["rows"]
            record[mode] = {}
            for label in labels:
                rows = pair[label][mode]["rows"]
                for old, new in zip(baseline, rows, strict=True):
                    if mode == "legal":
                        assert (old["board"], old["side"], old["moves"]) == (new["board"], new["side"], new["moves"])
                    else:
                        assert old["start"] == new["start"] and deterministic(old["choice"]) == deterministic(
                            new["choice"]
                        )
                times = [row["ms"] for row in rows]
                record[mode][label] = {
                    "mean_ms": statistics.mean(times),
                    "median_ms": statistics.median(times),
                    "observations": len(times),
                    "total_speedup": sum(row["ms"] for row in baseline) / sum(times),
                }
        rounds.append(record)
        print("round", repeat, json.dumps(record), flush=True)
    adopted = all(
        r[mode]["after"]["median_ms"] < r[mode]["before"]["median_ms"] for r in rounds for mode in ("1024", "4096")
    ) and all(
        sum(r[mode]["after"]["mean_ms"] for r in rounds) < 0.95 * sum(r[mode]["before"]["mean_ms"] for r in rounds)
        for mode in ("1024", "4096")
    )
    save(
        run / "performance.json",
        {
            "rounds": rounds,
            "fixed_budget_equivalent_start_budget_cases": 24,
            "adoption_criterion_passed": adopted,
            "limitations": "Repeated fixed local development workloads; no new playing-strength evidence.",
        },
    )
    print("adoption", adopted, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--measure", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.run)
    else:
        measure(args.run)
