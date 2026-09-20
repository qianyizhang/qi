"""Persistent replay execution; caller-owned actors supply every action."""

from typing import Protocol

from qi_game.contracts import Position, Snapshot


class Trajectory(Protocol):
    """One exclusively owned game. Inspection is detached; close is idempotent.

    Step validates the stale guard before the action and leaves state unchanged
    on rejection. Terminal positions expose no actions. No implicit reset occurs.
    """

    def inspect(self) -> Position: ...
    def step(self, move: str, expected_hash: str | None = None) -> Position: ...
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

    def inspect(self) -> Position:
        from qi_game.reference import inspect

        return inspect(self._require_open())

    def step(self, move: str, expected_hash: str | None = None) -> Position:
        from qi_game.reference import inspect

        next_game = self._require_open().apply(move, expected_hash)
        result = inspect(next_game)
        self._game = next_game
        return result

    def close(self) -> None:
        self._game = None
