"""Pair denominators, perspective, and unavailable scores are explicit."""

import pytest

from qi.scoring import GameScore, score_pairs


def test_only_complete_pairs_score_and_latency_is_decision_weighted():
    games = [
        GameScore(pair_id="one", a_side="red", status="complete", result="win", decisions=2, elapsed_ms=10),
        GameScore(pair_id="one", a_side="black", status="complete", result="draw", decisions=3, elapsed_ms=30),
        GameScore(pair_id="two", a_side="red", status="complete", result="loss", decisions=1, elapsed_ms=999),
        GameScore(pair_id="two", a_side="black", status="failed"),
        GameScore(pair_id="three", a_side="red", status="running"),
        GameScore(pair_id="three", a_side="black", status="pending"),
    ]
    score = score_pairs(games)
    assert (score.wins, score.draws, score.losses, score.score_rate) == (1, 1, 0, 0.75)
    assert (score.completed_pairs, score.planned_pairs) == (1, 3)
    assert (score.completed_games, score.failed_games, score.incomplete_games) == (3, 1, 2)
    assert score.unpaired_completed_games == 1
    assert score.decisions == 5 and score.mean_elapsed_ms == 8


def test_missing_score_differs_from_a_zero_score():
    games = [GameScore(pair_id="one", a_side=side, status="pending") for side in ("red", "black")]
    assert score_pairs(games).score_rate is None
    losses = [game.model_copy(update={"status": "complete", "result": "loss"}) for game in games]
    assert score_pairs(losses).score_rate == 0
    assert score_pairs([]).score_rate is None


def test_duplicate_colors_missing_slots_and_fabricated_draws_are_rejected():
    game = GameScore(pair_id="one", a_side="red", status="pending")
    for games in ([game], [game, game]):
        with pytest.raises(ValueError, match="both color"):
            score_pairs(games)
    with pytest.raises(ValueError, match="completed"):
        GameScore(pair_id="one", a_side="red", status="incomplete", result="draw")
    with pytest.raises(ValueError):
        GameScore(pair_id="one", a_side="red", status="complete", result="draw", elapsed_ms=float("nan"))
