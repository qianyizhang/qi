"""Bounded, isolated native-backend study; no production registrations or defaults."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib
import json
import platform
import resource
import shutil
import subprocess
import sys
import time
from collections import Counter
from functools import partial
from pathlib import Path

from qi_game.contracts import Position, Result, Snapshot
from qi_game.core import RULESET, START_BOARD, START_FEN, GameError
from qi_game.reference import Game, in_check, legal_moves, parse_move, replay

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = ROOT / "artifacts/native-backends-20260921"
FIXTURES = ROOT / "packages/qi-game/src/qi_game/fixtures/referee-v1.json"
REASONS = {1: "checkmate", 2: "stalemate", 3: "repetition", 4: "ply_limit"}
ERRORS = {1: "game_over", 2: "invalid_move", 3: "wrong_player", 4: "illegal_move"}
ARMS = [
    "python",
    "import",
    "minimal-scalar",
    "minimal-batch-1",
    "minimal-batch-8",
    "minimal-batch-32",
    "minimal-batch-128",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value) -> None:
    """Study JSON consists of heterogeneous evidence records, not runtime DTOs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def next_rng(value: int) -> int:
    value ^= (value << 13) & 0xFFFFFFFF
    value ^= value >> 17
    value ^= (value << 5) & 0xFFFFFFFF
    return value


def seeds(count: int, base: int) -> list[int]:
    return [((base + i * 2654435761) & 0xFFFFFFFF) or 1 for i in range(count)]


def move_string(value: int) -> str:
    source, target = divmod(value, 90)
    return f"{chr(97 + source % 9)}{source // 9}{chr(97 + target % 9)}{target // 9}"


def state_hash(moves: list[str]) -> str:
    return hashlib.sha256("|".join((RULESET, START_FEN, *moves)).encode()).hexdigest()


class State:
    """Study-local scalar adapter; subclasses own execution and mutable state."""

    moves: list[str]

    def close(self) -> None:
        pass

    def position(self) -> Position:
        result = self.result()
        return Position(
            snapshot=Snapshot(moves=self.moves.copy()),
            board=self.board,
            turn=self.turn,
            ply=len(self.moves),
            state_hash=state_hash(self.moves),
            legal_moves=[] if result else self.actions(),
            in_check=self.checked(),
            outcome=Result(
                winner=("black" if self.turn == "red" else "red") if result < 3 else None, reason=REASONS[result]
            )
            if result
            else None,
        )

    def record(self) -> dict:
        return {"board": self.board, "turn": self.turn, "moves": self.moves.copy(), "result": self.result()}


class PythonState(State):
    def __init__(self):
        self.game = Game()
        self.moves = []

    @property
    def board(self):
        return self.game.board

    @property
    def turn(self):
        return self.game.turn

    def checked(self):
        return in_check(self.board, self.turn)

    def result(self):
        outcome = self.game.outcome
        return next((code for code, reason in REASONS.items() if outcome and reason == outcome.reason), 0)

    def actions(self):
        return list(legal_moves(self.board, self.turn)) if not self.result() else []

    def apply(self, move):
        self.game = self.game.apply(move)
        self.moves.append(move)


def board_fen(board: str, turn: str) -> str:
    ranks = []
    for rank in reversed(range(10)):
        text, empty = "", 0
        for piece in board[rank * 9 : rank * 9 + 9]:
            if piece == ".":
                empty += 1
            else:
                text += (str(empty) if empty else "") + piece
                empty = 0
        ranks.append(text + (str(empty) if empty else ""))
    return "/".join(ranks) + (" w" if turn == "red" else " b") + " - - 0 1"


def fen_board(fen: str) -> str:
    return "".join(
        "".join("." * int(c) if c.isdigit() else c for c in rank) for rank in reversed(fen.split()[0].split("/"))
    )


class ImportState(State):
    def __init__(self):
        self.engine = importlib.import_module("pyffish")
        self.fen = self.engine.start_fen("xiangqi")
        self.board, self.turn, self.moves = START_BOARD, "red", []
        self.counts = Counter({self.board + self.turn: 1})
        self.cached = None

    def raw_actions(self):
        if self.cached is None:
            import re

            actions = []
            for move in self.engine.legal_moves("xiangqi", self.fen, []):
                match = re.fullmatch(r"([a-i])(10|[1-9])([a-i])(10|[1-9])", move)
                if not match:
                    raise ValueError(f"Unexpected pyffish move: {move}")
                a, b, c, d = match.groups()
                actions.append(f"{a}{int(b) - 1}{c}{int(d) - 1}")
            self.cached = sorted(actions, key=parse_move)
        return self.cached

    def checked(self):
        return self.engine.gives_check("xiangqi", self.fen, [])

    def result(self):
        if not self.raw_actions():
            return 1 if self.checked() else 2
        if self.counts[self.board + self.turn] >= 3:
            return 3
        return 4 if len(self.moves) >= 300 else 0

    def actions(self):
        return self.raw_actions().copy() if not self.result() else []

    def apply(self, move):
        if self.result():
            raise GameError("game_over", "Game ended")
        source, _ = parse_move(move)
        if self.board[source] != "." and self.board[source].isupper() != (self.turn == "red"):
            raise GameError("wrong_player", "Wrong side")
        if move not in self.raw_actions():
            raise GameError("illegal_move", "Illegal move")
        native = f"{move[0]}{int(move[1]) + 1}{move[2]}{int(move[3]) + 1}"
        fen = self.engine.get_fen("xiangqi", self.fen, [native])
        self.fen, self.board = fen, fen_board(fen)
        self.turn = "black" if self.turn == "red" else "red"
        self.moves.append(move)
        self.counts[self.board + self.turn] += 1
        self.cached = None


def native_library():
    # ctypes declares this small experimental C ABI; no generated binding dependency.
    lib = ctypes.CDLL(str(ARTIFACTS / "minimal.dylib"))
    for name, result, args in [
        ("new", ctypes.c_void_p, []),
        ("free", None, [ctypes.c_void_p]),
        ("board", ctypes.c_char_p, [ctypes.c_void_p]),
        ("turn", ctypes.c_int, [ctypes.c_void_p]),
        ("result", ctypes.c_int, [ctypes.c_void_p]),
        ("check", ctypes.c_int, [ctypes.c_void_p]),
        ("apply", ctypes.c_int, [ctypes.c_void_p, ctypes.c_char_p]),
        ("legal", ctypes.c_int, [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]),
        ("diagram", ctypes.c_int, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
        ("perft", ctypes.c_uint64, [ctypes.c_int]),
        ("rollouts", ctypes.c_void_p, [ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]),
        ("release", None, [ctypes.c_void_p]),
    ]:
        fn = getattr(lib, "nb_" + name)
        fn.restype, fn.argtypes = result, args
    return lib


class MinimalState(State):
    library = None

    def __init__(self):
        if self.library is None:
            type(self).library = native_library()
        self.lib = self.library
        self.handle = self.lib.nb_new()
        self.buffer = (ctypes.c_int * 8100)()
        self.moves = []

    def close(self):
        if self.handle:
            self.lib.nb_free(self.handle)
            self.handle = None

    @property
    def board(self):
        return self.lib.nb_board(self.handle).decode()

    @property
    def turn(self):
        return "red" if self.lib.nb_turn(self.handle) else "black"

    def checked(self):
        return bool(self.lib.nb_check(self.handle))

    def result(self):
        return self.lib.nb_result(self.handle)

    def actions(self):
        size = self.lib.nb_legal(self.handle, self.buffer, len(self.buffer))
        if size < 0:
            raise RuntimeError("Native action buffer too small")
        return [move_string(self.buffer[i]) for i in range(size)]

    def apply(self, move):
        # Preserve Python string semantics, including embedded NULs, at the C boundary.
        if self.result():
            raise GameError("game_over", "Game ended")
        parse_move(move)
        error = self.lib.nb_apply(self.handle, move.encode())
        if error:
            raise GameError(ERRORS[error], "Native move rejected")
        self.moves.append(move)


FACTORIES = {"python": PythonState, "import": ImportState, "minimal-scalar": MinimalState}


class RefereeAdapter:
    def __init__(self, arm: str):
        self.factory = FACTORIES[arm]

    def operate(self, snapshot: Snapshot, move=None, expected_hash=None) -> Position:
        state = self.factory()
        try:
            for previous in snapshot.moves:
                state.apply(previous)
            if move is not None:
                if state_hash(state.moves) != expected_hash:
                    raise GameError("stale_state", "Stale snapshot")
                state.apply(move)
            return state.position()
        finally:
            state.close()

    def inspect(self, snapshot: Snapshot) -> Position:
        return self.operate(snapshot)

    def apply(self, snapshot: Snapshot, move: str, expected_hash: str) -> Position:
        return self.operate(snapshot, move, expected_hash)


def native_batch(game_seeds: list[int], max_plies: int, batch_size: int) -> list[dict]:
    lib = MinimalState.library
    if lib is None:
        MinimalState.library = lib = native_library()
    result = []
    for start in range(0, len(game_seeds), batch_size):
        batch = game_seeds[start : start + batch_size]
        values = (ctypes.c_uint32 * len(batch))(*batch)
        ptr = lib.nb_rollouts(values, len(batch), max_plies)
        if not ptr:
            raise RuntimeError("Native batch rejected")
        try:
            result.extend(json.loads(ctypes.string_at(ptr)))
        finally:
            lib.nb_release(ptr)
    return result


def trajectories(arm: str, game_seeds: list[int], max_plies: int) -> list[dict]:
    if arm.startswith("minimal-batch-"):
        return native_batch(game_seeds, max_plies, int(arm.rsplit("-", 1)[1]))
    records = []
    for seed in game_seeds:
        state = FACTORIES[arm]()
        rng = seed
        try:
            for _ in range(max_plies):
                actions = state.actions()
                if not actions:
                    break
                rng = next_rng(rng)
                state.apply(actions[rng % len(actions)])
            records.append(state.record())
        finally:
            state.close()
    return records


def expected_error(call, code: str) -> None:
    try:
        call()
    except GameError as error:
        assert error.code == code, (error.code, code)
    else:
        raise AssertionError(f"Expected {code}")


def validate() -> dict:
    fixtures = json.loads(FIXTURES.read_text())
    counts = Counter()
    for arm in ("import", "minimal-scalar"):
        adapter = RefereeAdapter(arm)
        for case in fixtures["replays"]:
            expected = case["position"]
            snapshot = Snapshot.model_validate(expected["snapshot"])
            actual = adapter.inspect(snapshot).model_dump()
            assert actual == expected, (arm, case["name"], actual, expected)
            if snapshot.moves:
                parent = Snapshot(moves=snapshot.moves[:-1])
                result = adapter.apply(parent, snapshot.moves[-1], state_hash(parent.moves))
                assert result.model_dump() == expected
            counts[arm + " frozen replays"] += 1
        for case in fixtures["diagrams"]:
            given = case["state"]
            state = FACTORIES[arm]()
            try:
                state.moves = given["moves"].copy()
                if arm == "import":
                    state.board, state.turn = given["board"], given["turn"]
                    state.fen = board_fen(state.board, state.turn)
                    state.counts = Counter(given["positions"])
                else:
                    assert (
                        state.lib.nb_diagram(
                            state.handle,
                            given["board"].encode(),
                            given["turn"] == "red",
                            len(state.moves),
                            given["positions"].count(given["board"] + given["turn"]),
                        )
                        == 0
                    )
                assert state.position().model_dump() == case["position"], (arm, case["name"])
                counts[arm + " terminal diagrams"] += 1
            finally:
                state.close()
        snapshot = Snapshot()
        before = adapter.inspect(snapshot).model_dump()
        for move, guard, code in [
            ("bad", "stale", "stale_state"),
            ("bad", state_hash([]), "invalid_move"),
            ("a9a8", state_hash([]), "wrong_player"),
            ("a0a9", state_hash([]), "illegal_move"),
            ("a0a1\x00junk", state_hash([]), "invalid_move"),
        ]:
            expected_error(partial(adapter.apply, snapshot, move, guard), code)
            assert adapter.inspect(snapshot).model_dump() == before and snapshot.moves == []
            counts[arm + " guarded errors"] += 1
        mutated = adapter.inspect(snapshot)
        mutated.legal_moves.clear()
        mutated.snapshot.moves.append("a3a4")
        assert adapter.inspect(snapshot).model_dump() == before
        terminal = Snapshot.model_validate(fixtures["replays"][2]["position"]["snapshot"])
        expected_error(partial(adapter.apply, terminal, "bad", state_hash(terminal.moves)), "game_over")
        expected_error(partial(adapter.apply, terminal, "bad", "stale"), "stale_state")
        invalid = Snapshot(moves=[*terminal.moves, "a3a4"])
        expected_error(partial(adapter.inspect, invalid), "game_over")
        expected_error(partial(adapter.apply, invalid, "bad", "stale"), "game_over")
        counts[arm + " isolation and history controls"] += 5
    dev_seeds = seeds(64, 12345)
    records = []
    for seed in dev_seeds:
        states = [PythonState(), ImportState(), MinimalState()]
        rng = seed
        try:
            for _ in range(97):
                expected = states[0].position().model_dump()
                for state in states[1:]:
                    assert state.position().model_dump() == expected, (seed, states[0].moves, type(state).__name__)
                counts["development positions"] += 1
                actions = expected["legal_moves"]
                if not actions or len(states[0].moves) == 96:
                    break
                rng = next_rng(rng)
                for state in states:
                    state.apply(actions[rng % len(actions)])
            records.append(states[0].record())
        finally:
            for state in states:
                state.close()
    for size in (1, 8, 32, 128):
        assert native_batch(dev_seeds, 96, size) == records
        counts["native batch matching trajectories"] += len(records)
    native_count = MinimalState.library.nb_perft(3)
    assert native_count == 79666, native_count
    counts["native perft depth 3"] = native_count
    return {"passed": True, "counts": dict(counts), "fixture_sha256": digest(FIXTURES), "development_seeds": dev_seeds}


def worker(arm: str, output: Path, input_path: Path) -> None:
    config = json.loads(input_path.read_text())
    started = time.perf_counter()
    if arm.startswith("minimal"):
        MinimalState.library = native_library()
    elif arm == "import":
        importlib.import_module("pyffish")
    startup = time.perf_counter() - started
    legal_moves.cache_clear()
    replay.cache_clear()
    before_wall, before_cpu = time.perf_counter(), time.process_time()
    records = trajectories(arm, config["seeds"], config["max_plies"])
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    elapsed, cpu = time.perf_counter() - before_wall, time.process_time() - before_cpu
    plies = sum(len(record["moves"]) for record in records)
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_new(
        output,
        {
            "arm": arm,
            "elapsed_seconds": elapsed,
            "cpu_seconds": cpu,
            "backend_startup_seconds": startup,
            "peak_rss_bytes": maxrss if sys.platform == "darwin" else maxrss * 1024,
            "games": len(records),
            "plies": plies,
            "plies_per_second": plies / elapsed,
            "completed_games": sum(bool(record["result"]) for record in records),
            "truncated_games": sum(not record["result"] for record in records),
            "trajectory_sha256": hashlib.sha256(encoded).hexdigest(),
            "input_sha256": digest(input_path),
            "records": records,
        },
    )


def main():
    global ARTIFACTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["validate", "worker", "run"])
    parser.add_argument("--artifacts", type=Path, default=ARTIFACTS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    ARTIFACTS = args.artifacts.resolve()
    sys.path.insert(0, str(ARTIFACTS / "deps"))
    if args.operation == "validate":
        write_new(args.output, validate())
    elif args.operation == "worker":
        worker(args.arm, args.output, args.inputs)
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        config = {"seeds": seeds(128, 987654321), "max_plies": 300, "rounds": 3, "arms": ARMS}
        inputs = args.output / "inputs.json"
        write_new(inputs, config)
        source_files = [
            *Path(__file__).parent.glob("*.py"),
            *Path(__file__).parent.glob("*.cpp"),
            Path(__file__).parent / "requirements.txt",
            FIXTURES,
            ROOT / "uv.lock",
            *sorted((ROOT / "packages/qi-game/src/qi_game").glob("*.py")),
        ]
        binaries = [
            ARTIFACTS / "minimal.dylib",
            *sorted(p for p in (ARTIFACTS / "deps").rglob("*") if p.is_file() and "__pycache__" not in p.parts),
        ]
        hashes = {str(p.relative_to(ROOT)): digest(p) for p in [*source_files, *binaries]}
        for source in [*source_files, *binaries]:
            destination = args.output / "frozen" / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        write_new(
            args.output / "manifest.json",
            {
                "hashes": hashes,
                "python": sys.version,
                "platform": platform.platform(),
                "machine": platform.machine(),
                "compiler": subprocess.check_output(["clang++", "--version"], text=True),
                "build_flags": "-std=c++17 -O3 -DNDEBUG -Wall -Wextra -Werror -fPIC -shared",
                "imported_build": (
                    "Pinned PyPI pyffish 0.0.90 wheel; upstream compiler/flags unknown; installed bytes retained"
                ),
                "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            },
        )
        # Validation is untimed, in a separate process, before the timing workers.
        base = [sys.executable, str(Path(__file__).resolve())]
        validation = subprocess.run(
            [*base, "validate", "--artifacts", str(ARTIFACTS), "--output", str(args.output / "validation.json")],
            capture_output=True,
            text=True,
            timeout=300,
        )
        write_new(
            args.output / "validation-attempt.json",
            {"returncode": validation.returncode, "stdout": validation.stdout, "stderr": validation.stderr},
        )
        if validation.returncode:
            raise RuntimeError("Conformance failed; see validation-attempt.json")
        rows = []
        expected_digest = None
        for round_index in range(config["rounds"]):
            arms = ARMS if round_index % 2 == 0 else ARMS[::-1]
            for arm in arms:
                output = args.output / f"round-{round_index + 1}-{arm}.json"
                command = [
                    *base,
                    "worker",
                    "--artifacts",
                    str(ARTIFACTS),
                    "--output",
                    str(output),
                    "--arm",
                    arm,
                    "--inputs",
                    str(inputs),
                ]
                print(f"round={round_index + 1} arm={arm}", flush=True)
                attempt_start = time.perf_counter()
                try:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                except subprocess.TimeoutExpired as error:
                    write_new(
                        output.with_suffix(".failed.json"),
                        {"command": command, "failure": "timeout", "detail": str(error)},
                    )
                    raise
                if result.returncode:
                    write_new(
                        output.with_suffix(".failed.json"),
                        {
                            "command": command,
                            "returncode": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                        },
                    )
                    raise RuntimeError(f"Worker failed: {output}")
                row = json.loads(output.read_text())
                if expected_digest is None:
                    expected_digest = row["trajectory_sha256"]
                assert row["trajectory_sha256"] == expected_digest, (round_index, arm, "trajectory mismatch")
                rows.append(
                    {
                        "round": round_index + 1,
                        "process_wall_seconds": time.perf_counter() - attempt_start,
                        **{key: value for key, value in row.items() if key != "records"},
                    }
                )
                assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in [*source_files, *binaries]}, (
                    "Source changed"
                )
        write_new(args.output / "summary.json", {"complete": True, "rows": rows, "inputs": config})


if __name__ == "__main__":
    main()
