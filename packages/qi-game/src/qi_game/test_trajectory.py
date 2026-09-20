"""Persistent reference lifecycle and rejection semantics."""

from dataclasses import FrozenInstanceError

import pytest

from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.trajectory import PythonTrajectory


def test_detached_views_atomic_rejection_and_close():
    game = PythonTrajectory(Snapshot(moves=["b2e2"]))
    before = game.inspect()
    for move, guard, code in [("bad", "stale", "stale_state"), ("bad", None, "invalid_move")]:
        with pytest.raises(GameError) as error:
            game.step(move, guard)
        assert error.value.code == code
        assert game.inspect() == before
    result = game.step("b9c7", before.state_hash)
    with pytest.raises(FrozenInstanceError):
        result.board = "changed"
    wire = result.to_position()
    wire.snapshot.moves.clear()
    wire.legal_moves.clear()
    assert game.inspect().moves == ("b2e2", "b9c7")
    assert before.moves == ("b2e2",)
    game.close()
    game.close()
    with pytest.raises(RuntimeError, match="closed"):
        game.inspect()
