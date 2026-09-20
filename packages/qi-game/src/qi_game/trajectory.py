"""Persistent replay execution; caller-owned actors supply every action."""

from dataclasses import dataclass
from typing import Protocol

from qi_game.contracts import Position, Result, Snapshot
from qi_game.core import Outcome, Side


@dataclass(frozen=True, slots=True)
class GameView:
    """Immutable referee result; wire contracts are constructed only when needed."""

    board: str
    turn: Side
    moves: tuple[str, ...]
    state_hash: str
    legal_moves: tuple[str, ...]
    in_check: bool
    outcome: Outcome | None

    @classmethod
    def from_position(cls, position: Position) -> "GameView":
        result = position.outcome
        return cls(
            position.board,
            position.turn,
            tuple(position.snapshot.moves),
            position.state_hash,
            tuple(position.legal_moves),
            position.in_check,
            Outcome(result.winner, result.reason) if result else None,
        )

    def snapshot(self) -> Snapshot:
        return Snapshot(moves=list(self.moves))

    def to_position(self) -> Position:
        return Position(
            snapshot=self.snapshot(),
            board=self.board,
            turn=self.turn,
            ply=len(self.moves),
            state_hash=self.state_hash,
            legal_moves=list(self.legal_moves),
            in_check=self.in_check,
            outcome=Result(winner=self.outcome.winner, reason=self.outcome.reason) if self.outcome else None,
        )


class Trajectory(Protocol):
    """One exclusively owned game. Inspection is immutable; close is idempotent.

    Step validates the stale guard before the action and leaves state unchanged
    on rejection. Terminal positions expose no actions. No implicit reset occurs.
    """

    def inspect(self) -> GameView: ...
    def step(self, move: str, expected_hash: str | None = None) -> GameView: ...
    def close(self) -> None: ...


class TrajectoryFactory(Protocol):
    def __call__(self, snapshot: Snapshot) -> Trajectory: ...
    def identity(self) -> dict[str, str]: ...


class PythonTrajectory:
    """Lazy reference implementation of the persistent execution contract."""

    def __init__(self, snapshot: Snapshot):
        from qi_game.reference import restore

        self._game = restore(snapshot)

    @staticmethod
    def identity() -> dict[str, str]:
        return {"backend": "python-reference", "version": "1"}

    def _require_open(self):
        if self._game is None:
            raise RuntimeError("Trajectory is closed.")
        return self._game

    def inspect(self) -> GameView:
        from qi_game.reference import in_check, legal_moves

        game = self._require_open()
        outcome = game.outcome
        return GameView(
            game.board,
            game.turn,
            game.moves,
            game.state_hash,
            () if outcome else legal_moves(game.board, game.turn),
            in_check(game.board, game.turn),
            outcome,
        )

    def step(self, move: str, expected_hash: str | None = None) -> GameView:
        self._game = self._require_open().apply(move, expected_hash)
        return self.inspect()

    def close(self) -> None:
        self._game = None
