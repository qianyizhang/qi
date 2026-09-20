"""Shared immutable replay results cannot bypass history or lifecycle checks."""

from dataclasses import FrozenInstanceError

import pytest

from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.execution import ReplaySession
from qi_game.trajectory import PythonTrajectory


def test_incremental_execution_reuse_branching_and_eviction():
    calls = []

    class Tracked(PythonTrajectory):
        def __init__(self, snapshot):
            calls.append(("restore", tuple(snapshot.moves)))
            super().__init__(snapshot)

        def step(self, move, expected_hash=None):
            calls.append(("step", move))
            return super().step(move, expected_hash)

        def close(self):
            calls.append(("close",))
            super().close()

    with ReplaySession(Tracked, capacity=2) as session:
        initial = session.inspect(Snapshot())
        first = session.inspect(Snapshot(moves=["b2e2"]))
        assert session.inspect(first.snapshot()) is first
        with pytest.raises(FrozenInstanceError):
            first.board = "bad"
        snapshot = first.snapshot()
        snapshot.moves.clear()
        assert first.moves == ("b2e2",)
        second = session.inspect(Snapshot(moves=["b2e2", "b9c7"]))
        assert len(session._views) == 2
        assert session.inspect(Snapshot()) == initial  # evicted: validate again
        assert session.inspect(second.snapshot()) is second
        branch = session.inspect(Snapshot(moves=["a3a4"]))
        assert branch.moves == ("a3a4",)
        with pytest.raises(GameError):
            session.inspect(Snapshot(moves=["a3a4", "a0a1"]))
        assert session.inspect(branch.snapshot()) == branch
        with pytest.raises(ValueError, match="identity"):
            session.inspect(Snapshot().model_copy(update={"ruleset": "wrong"}))
    assert calls.count(("step", "b2e2")) == 1
    assert calls.count(("step", "b9c7")) == 1
    session.close()
    with pytest.raises(RuntimeError, match="closed"):
        session.inspect(Snapshot())


def test_failed_restore_preserves_session_and_rejects_broken_backend():
    with ReplaySession(PythonTrajectory) as session:
        previous = session.inspect(Snapshot(moves=["b2e2"]))
        with pytest.raises(GameError):
            session.inspect(Snapshot(moves=["bad"]))
        assert session.inspect(previous.snapshot()) is previous

    class Broken(PythonTrajectory):
        def inspect(self):
            result = super().inspect()
            result.snapshot.moves.append("a3a4")
            return result

    with ReplaySession(Broken) as session:
        with pytest.raises(ValueError, match="different replay"):
            session.inspect(Snapshot())
        with pytest.raises(RuntimeError, match="closed"):
            session.inspect(Snapshot())
