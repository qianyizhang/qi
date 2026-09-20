"""Bounded, run-owned replay validation shared by execution and its consumers."""

from collections import OrderedDict
from contextlib import AbstractContextManager

from qi_game.contracts import Snapshot
from qi_game.core import RULESET, START_FEN
from qi_game.trajectory import GameView, Trajectory, TrajectoryFactory


class ReplaySession(AbstractContextManager):
    """Validate each full history once, advancing a single native/reference cursor.

    Cached views establish legality only, never persistence. A collection still
    checks its own persisted prefix and transaction outcome on every write.
    Only backend results enter this bounded cache; caller-supplied views cannot.
    """

    def __init__(self, factory: TrajectoryFactory, *, capacity: int = 301):
        if not 1 <= capacity <= 301:
            raise ValueError("Replay cache capacity must be between 1 and 301.")
        self.factory, self.capacity = factory, capacity
        self._views: OrderedDict[tuple[str, ...], GameView] = OrderedDict()
        self._cursor: Trajectory | None = None
        self._moves: tuple[str, ...] | None = None
        self._closed = False

    def inspect(self, snapshot: Snapshot) -> GameView:
        if self._closed:
            raise RuntimeError("Replay session is closed.")
        if snapshot.schema_version != 1 or snapshot.ruleset != RULESET or snapshot.initial_fen != START_FEN:
            raise ValueError("Unsupported replay identity.")
        moves = tuple(snapshot.moves)
        if moves in self._views:
            self._views.move_to_end(moves)
            return self._views[moves]
        if self._cursor is not None and moves and moves[:-1] == self._moves:
            view = self._cursor.step(moves[-1])
        else:
            candidate = self.factory(snapshot)
            try:
                view = candidate.inspect()
            except BaseException:
                candidate.close()
                raise
            if self._cursor is not None:
                self._cursor.close()
            self._cursor = candidate
        self._moves = moves
        if view.moves != moves:
            # A broken implementation must never publish a result for another history.
            self.close()
            raise ValueError("Referee returned a different replay history.")
        self._views[moves] = view
        if len(self._views) > self.capacity:
            self._views.popitem(last=False)
        return view

    def close(self) -> None:
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None
        self._views.clear()
        self._closed = True

    def __exit__(self, *_exc):
        self.close()
