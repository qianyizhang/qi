"""Observation and action coordinates are independent of torch and game history."""

import subprocess
import sys

import pytest
from qi_game.core import GameError
from qi_game.reference import Game

from qi.players import PlayerConfig, choose, list_players
from qi.players.policy.encoding import action_id, encode


def test_board_planes_and_turn_bit():
    red = encode(Game())
    black = encode(Game().apply("b2e2"))
    assert len(red) == len(black) == 1261
    assert sum(red) == 32 and sum(black) == 33
    assert red[-1] == 0 and black[-1] == 1
    assert action_id("a0i9") == 89
    assert action_id("i9a0") == 89 * 90


def test_missing_checkpoint_does_not_fallback(monkeypatch):
    monkeypatch.delenv("QI_POLICY_CHECKPOINT", raising=False)
    assert "policy" not in {player.id for player in list_players()}
    with pytest.raises(GameError, match="QI_POLICY_CHECKPOINT"):
        choose(Game(), PlayerConfig("policy"))


def test_baseline_imports_do_not_load_torch():
    result = subprocess.run(
        [sys.executable, "-c", "import qi.cli, sys; assert 'torch' not in sys.modules"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
