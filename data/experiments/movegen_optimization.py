"""AB-EVAL-007: frozen-source equivalence, isolated timings and timing-only node calibration.

Each worker imports the explicitly supplied source tree before importing qi.
The controller and worker are separate processes so imported function bindings
and referee caches cannot leak between old and new implementations.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(args):
    sys.path.insert(0, str(args.source.resolve() / "src"))
    import qi.game as referee
    from qi.game import legal_moves, replay
    from qi.players import PlayerConfig, choose
    from qi.protocol import Snapshot

    directory = args.run.resolve()
    if Path(referee.__file__).resolve() != (args.source / "src/qi/game.py").resolve():
        raise ValueError("Worker did not import its frozen source tree.")
    rows = []
    if args.mode == "legal":
        boards = json.loads((directory / "timing-boards.json").read_text())
        legal_moves.cache_clear()
        for board in boards:
            for side in ("red", "black"):
                started = perf_counter()
                moves = legal_moves(board, side)
                rows.append({"board": board, "side": side, "ms": (perf_counter() - started) * 1000, "moves": moves})
    else:
        for start in json.loads((directory / "probe-starts.json").read_text()):
            game = Snapshot.model_validate(start["snapshot"]).game()
            legal_moves.cache_clear()
            replay.cache_clear()
            started = perf_counter()
            choice = choose(game, PlayerConfig("alphabeta-pvs", seed=7, nodes=args.nodes, depth=4))
            rows.append({"start": start["id"], "ms": (perf_counter() - started) * 1000, "choice": asdict(choice)})
    save(args.output, {"source": str(args.source.resolve()), "mode": args.mode, "nodes": args.nodes, "rows": rows})


def load_before(directory):
    path = directory / "before/src/qi/game.py"
    spec = importlib.util.spec_from_file_location("qi_before_game", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare(directory):
    outputs = (
        "after",
        "after-hashes.json",
        "equivalence.json",
        "positions.json",
        "probe-starts.json",
        "timing-boards.json",
    )
    if any((directory / name).exists() for name in outputs):
        raise ValueError("Use a fresh preparation output directory; existing evidence must be preserved.")
    from qi.evaluation import EvalRun
    from qi.game import in_check, legal_moves
    from qi.test_move_generation import arbitrary_boards

    before = load_before(directory)
    prior = ROOT / "artifacts/experiments/enhanced-potential-20260915"
    starts = json.loads((prior / "starts.json").read_text())
    manifest = json.loads((prior / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if sha(prior / name) != expected:
            raise ValueError(f"Changed prior evidence: {name}")
    boards, histories = {}, []
    games = 0
    for name in manifest["runs"]:
        run = EvalRun.model_validate_json((prior / f"{name}.json").read_text())
        for entry in run.games:
            if entry.match is None:
                raise ValueError("Prior study must have complete game evidence.")
            match = entry.match
            game = match.opening.game()
            for turn in match.turns:
                boards.setdefault(game.board, list(game.moves))
                game = game.apply(turn.choice.move)
            boards.setdefault(game.board, list(game.moves))
            old_end = before.replay(tuple(match.snapshot.moves))
            assert (game.board, game.turn, game.outcome.winner, game.outcome.reason) == (
                old_end.board,
                old_end.turn,
                old_end.outcome.winner,
                old_end.outcome.reason,
            )
            histories.append(list(match.snapshot.moves))
            games += 1
    arbitrary = list(arbitrary_boards(1000))
    queries = 0
    for index, board in enumerate([*boards, *arbitrary]):
        for side in ("red", "black"):
            assert in_check(board, side) == before.in_check(board, side), (index, side, "check")
            assert legal_moves(board, side) == before.legal_moves(board, side), (index, side, "ordered moves")
            queries += 1

    def perft(module, game, depth):
        moves = module.legal_moves(game.board, game.turn)
        if depth == 1:
            return len(moves)
        return sum(perft(module, game.apply(move), depth - 1) for move in moves)

    import qi.game as current

    old_perft = perft(before, before.Game(), 3)
    new_perft = perft(current, current.Game(), 3)
    assert old_perft == new_perft
    selected = list(boards)
    sampled = [selected[i * (len(selected) - 1) // 255] for i in range(256)]
    assert len(set(sampled)) == 256
    save(directory / "positions.json", {"prior_histories": histories, "boards": boards, "arbitrary_boards": arbitrary})
    save(directory / "timing-boards.json", sampled)
    save(directory / "probe-starts.json", starts)
    save(
        directory / "equivalence.json",
        {
            "prior_games_replayed": games,
            "distinct_prior_boards": len(boards),
            "arbitrary_boards": len(arbitrary),
            "board_side_queries": queries,
            "ordered_moves_equal": True,
            "checks_equal": True,
            "terminal_outcomes_equal": True,
            "initial_perft_depth_3": {"before": old_perft, "after": new_perft},
        },
    )
    after = directory / "after"
    after.mkdir(exist_ok=False)
    source_paths = [*ROOT.joinpath("src/qi").rglob("*.py"), ROOT / "pyproject.toml", ROOT / "uv.lock"]
    for path in source_paths:
        target = after / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    save(directory / "after-hashes.json", {str(p.relative_to(ROOT)): sha(p) for p in source_paths})
    shutil.copy2(Path(__file__), directory / "movegen_optimization.py")
    print((directory / "equivalence.json").read_text(), flush=True)


def measured(directory, label, mode, nodes, round_id):
    output = directory / f"{label}-{mode}-{nodes}-r{round_id}.json"
    if output.exists():
        raise ValueError(f"Fresh measurement required: {output}")
    env = os.environ.copy()
    env.pop("QI_PLAYERS_CONFIG", None)
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--source",
            str(directory / label),
            "--run",
            str(directory),
            "--mode",
            mode,
            "--nodes",
            str(nodes),
            "--output",
            str(output),
        ],
        env=env,
        check=True,
        cwd=ROOT,
    )
    result = json.loads(output.read_text())
    return result


def deterministic(choice):
    return {key: value for key, value in choice.items() if key != "elapsed_ms"}


def measure(directory):
    evidence = json.loads((directory / "equivalence.json").read_text())
    rounds = []
    old_samples = []
    for round_id in range(3):
        pair = {}
        for label in ("before", "after") if round_id % 2 == 0 else ("after", "before"):
            pair[label] = {mode: measured(directory, label, mode, 1024, round_id) for mode in ("legal", "search")}
        for mode in ("legal", "search"):
            for old, new in zip(pair["before"][mode]["rows"], pair["after"][mode]["rows"], strict=True):
                if mode == "legal":
                    assert (old["board"], old["side"], old["moves"]) == (new["board"], new["side"], new["moves"])
                else:
                    assert old["start"] == new["start"] and deterministic(old["choice"]) == deterministic(new["choice"])
        record = {"round": round_id}
        for mode in ("legal", "search"):
            old = [x["ms"] for x in pair["before"][mode]["rows"]]
            new = [x["ms"] for x in pair["after"][mode]["rows"]]
            record[mode] = {
                "before_mean_ms": statistics.mean(old),
                "after_mean_ms": statistics.mean(new),
                "before_median_ms": statistics.median(old),
                "after_median_ms": statistics.median(new),
                "median_speedup": statistics.median(old) / statistics.median(new),
                "total_speedup": sum(old) / sum(new),
                "observations_per_implementation": len(old),
            }
            if mode == "search":
                old_samples.extend(old)
        rounds.append(record)
        print("timing", json.dumps(record), flush=True)
    # 128-visit control plus 1024 controls above cover 24 distinct start/budget decisions.
    a = measured(directory, "before", "search", 128, 0)
    b = measured(directory, "after", "search", 128, 0)
    assert all(
        deterministic(x["choice"]) == deterministic(y["choice"]) for x, y in zip(a["rows"], b["rows"], strict=True)
    )
    calibration = {}
    for nodes in (2048, 4096, 8192):
        rows = []
        for repeat in range(3):
            rows.extend(measured(directory, "after", "search", nodes, repeat)["rows"])
        calibration[str(nodes)] = {
            "mean_ms": statistics.mean(r["ms"] for r in rows),
            "median_ms": statistics.median(r["ms"] for r in rows),
            "mean_completed_depth": statistics.mean(r["choice"]["completed_depth"] for r in rows),
            "fallbacks": sum(r["choice"]["completed_depth"] == 0 for r in rows),
            "observations": len(rows),
        }
        print("calibration", nodes, calibration[str(nodes)], flush=True)
    baseline = statistics.mean(old_samples)
    selected = max([1024, *[int(n) for n, c in calibration.items() if c["mean_ms"] <= baseline]])
    adopted = all(r["search"]["after_median_ms"] < r["search"]["before_median_ms"] for r in rounds)
    result = {
        "equivalence": evidence,
        "fixed_budget_equivalent_start_budget_cases": 24,
        "rounds": rounds,
        "calibration": calibration,
        "baseline_mean_ms": baseline,
        "selected_nodes": selected,
        "adoption_speed_criterion_passed": adopted,
        "limitations": (
            "Paired isolated-process timings, three repeats; calibration on 12 development starts, "
            "not clock-controlled play."
        ),
    }
    save(directory / "performance.json", result)
    print("selected_nodes", selected, "adoption criterion", adopted, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--mode", choices=["legal", "search"])
    parser.add_argument("--nodes", type=int, default=1024)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args)
    elif args.prepare:
        prepare(args.run)
    elif args.measure:
        measure(args.run)
    else:
        parser.error("Choose --prepare or --measure.")
