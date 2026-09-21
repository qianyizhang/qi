"""Replay fixed actions to separate maintained native boundary cost from generation."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from evidence import write_new
from qi_game.contracts import Snapshot
from qi_game.reference import legal_moves, replay
from qi_game.trajectory import PythonTrajectory

from qi.artifacts import digest


def projection(view):
    result = view.outcome
    code = 0 if result is None else {"checkmate": 1, "stalemate": 2, "repetition": 3, "ply_limit": 4}[result.reason]
    return view.board, view.turn == "red", code, view.in_check, view.legal_moves


def measure(records, arm, repeats):
    if repeats < 1 or arm not in ("python", "native", "raw-native") or not records["games"]:
        raise ValueError("Require games, a known arm and positive repeats.")
    if any(row["game"]["initial"]["moves"] for row in records["games"]):
        raise ValueError("Action diagnostic requires games starting from the initial board.")
    if arm == "python":
        factory = PythonTrajectory
    else:
        from qi_game_native import _native
        from qi_game_native.backend import NativeTrajectory

        factory = NativeTrajectory
    elapsed, signatures = [], []
    actions = [row["game"]["snapshot"]["moves"] for row in records["games"]]
    for _ in range(repeats):
        legal_moves.cache_clear()
        replay.cache_clear()
        observed = []
        tick = perf_counter()
        for moves in actions:
            game = _native.State([]) if arm == "raw-native" else factory(Snapshot())
            try:
                observed.append(game.inspect())
                for move in moves:
                    if arm == "raw-native":
                        if game.step(move) != 0:
                            raise ValueError(f"Native core rejected {move}.")
                        observed.append(game.inspect())
                    else:
                        observed.append(game.step(move))
            finally:
                if arm != "raw-native":
                    game.close()
        elapsed.append(perf_counter() - tick)
        values = observed if arm == "raw-native" else [projection(view) for view in observed]
        signatures.append(digest(values))
        if arm != "raw-native":
            # Hash/history validation is outside timing and independent of the backend.
            for view in observed:
                if view.state_hash != replay(tuple(view.moves)).state_hash:
                    raise ValueError("History hash differs from independent replay.")
        del observed, values
    if len(set(signatures)) != 1:
        raise ValueError("Semantic mismatch between repeats.")
    return {
        "arm": arm,
        "elapsed_seconds": elapsed,
        "repeats": repeats,
        "games_per_repeat": len(actions),
        "plies_per_repeat": sum(map(len, actions)),
        "semantic_sha256": signatures[0],
        "boundary": "raw-native omits Python history/hash/GameView management; all arms inspect every position",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=["python", "native", "raw-native"], required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    result = measure(json.loads(args.input.read_text()), args.arm, args.repeats)
    write_new(args.output / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
