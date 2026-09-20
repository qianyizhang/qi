"""Persistent reference lifecycle and rejection semantics."""

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
    result.snapshot.moves.clear()
    result.legal_moves.clear()
    assert game.inspect().snapshot.moves == ["b2e2", "b9c7"]
    game.close()
    game.close()
    with pytest.raises(RuntimeError, match="closed"):
        game.inspect()
