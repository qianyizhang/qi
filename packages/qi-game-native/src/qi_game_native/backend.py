"""Replay-safe Python boundary for optional C++ execution."""

from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from qi_game.contracts import Position, Result, Snapshot
from qi_game.core import RULESET, START_FEN, GameError

try:
    from qi_game_native import _native
except ImportError as exc:
    raise ImportError("Native execution requires qi-game-native; install with `uv sync --extra native`.") from exc

_ERRORS = {
    1: ("game_over", "This game has already ended."),
    2: ("invalid_move", "Use coordinates such as b2e2."),
    3: ("wrong_player", "The move belongs to the other side."),
    4: ("illegal_move", "That move is not legal in this position."),
}


class NativeTrajectory:
    """An exclusively owned native game; close releases its state immediately."""

    def __init__(self, snapshot: Snapshot):
        snapshot = Snapshot.model_validate(snapshot.model_dump())
        # Restore through the same rule-error boundary as normal stepping.
        self._state = _native.State([])
        if snapshot.moves:
            try:
                self._state = _native.State(snapshot.moves)
            except ValueError:
                # Failed restoration has no published handle. Replay only the
                # rejected history to recover its exact public GameError code.
                for move in snapshot.moves:
                    self.step(move)
                raise

    @staticmethod
    def identity() -> dict[str, str]:
        return {
            "backend": "minimal-cpp",
            "version": version("qi-game-native"),
            "binary_sha256": sha256(Path(_native.__file__).read_bytes()).hexdigest(),
            "compiler": _native.compiler,
        }

    def _require_open(self):
        if self._state is None:
            raise RuntimeError("Trajectory is closed.")
        return self._state

    def inspect(self) -> Position:
        board, red, result, checked, legal, moves = self._require_open().inspect()
        turn = "red" if red else "black"
        outcome = None
        if result:
            outcome = Result(
                winner=("black" if red else "red") if result in (1, 2) else None,
                reason={1: "checkmate", 2: "stalemate", 3: "repetition", 4: "ply_limit"}[result],
            )
        return Position(
            snapshot=Snapshot(moves=moves),
            board=board,
            turn=turn,
            ply=len(moves),
            state_hash=sha256("|".join((RULESET, START_FEN, *moves)).encode()).hexdigest(),
            legal_moves=legal,
            in_check=checked,
            outcome=outcome,
        )

    def step(self, move: str, expected_hash: str | None = None) -> Position:
        return step_many([self], [move], [expected_hash])[0]

    def close(self) -> None:
        self._state = None


def step_many(
    games: list[NativeTrajectory], moves: list[str], expected_hashes: list[str | None] | None = None
) -> list[Position]:
    """Atomically advance 1..128 distinct games, once each, in caller order.

    Inputs are Python coordinate strings, copied at the binding. All stale guards
    precede action checks; the first invalid action in caller order is reported.
    Any rejected batch leaves every game unchanged. Results own their data.
    """
    if not 1 <= len(games) <= 128 or len(moves) != len(games):
        raise ValueError("Batch needs 1..128 games and exactly one action per game.")
    if len({id(game) for game in games}) != len(games):
        raise ValueError("Batch games must be distinct.")
    if expected_hashes is not None and len(expected_hashes) != len(games):
        raise ValueError("Provide one guard per game.")
    states = [game._require_open() for game in games]
    for game, guard in zip(games, expected_hashes or [None] * len(games), strict=True):
        if guard is not None and guard != game.inspect().state_hash:
            raise GameError("stale_state", "The position changed. Inspect it again before moving.")
    if any(not isinstance(move, str) for move in moves):
        raise TypeError("Actions must be coordinate strings.")
    index, error = _native.step_many(states, moves)
    if error:
        code, message = _ERRORS[error]
        raise GameError(code, f"Batch item {index}: {message}")
    return [game.inspect() for game in games]


class NativeReferee:
    def inspect(self, snapshot: Snapshot) -> Position:
        game = NativeTrajectory(snapshot)
        try:
            return game.inspect()
        finally:
            game.close()

    def apply(self, snapshot: Snapshot, move: str, expected_hash: str) -> Position:
        game = NativeTrajectory(snapshot)
        try:
            return game.step(move, expected_hash)
        finally:
            game.close()
