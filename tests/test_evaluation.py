"""Batch identities, repeatability, rejection, and independent aggregate checks."""

import json
import subprocess

import pytest
from pydantic import ValidationError

from qi.evaluation import Corpus, EvaluationRecord, evaluate_batch
from qi.players import PlayerConfig


def corpus() -> Corpus:
    return Corpus.model_validate(
        {
            "id": "test-v1",
            "provenance": "Test opening near a repetition draw.",
            "openings": [
                {
                    "id": "loop",
                    "description": "One cycle before repetition.",
                    "snapshot": {"moves": ["b0c2", "b9c7", "c2b0", "c7b9"]},
                }
            ],
        }
    )


def test_batch_pairs_colors_replays_and_recomputes_summary() -> None:
    a, b = PlayerConfig("random", seed=8), PlayerConfig("random", seed=9)
    first = evaluate_batch(corpus(), a, b)
    second = evaluate_batch(corpus(), a, b)
    assert [g.a_side for g in first.games] == ["red", "black"]
    assert first.games[0].match.red == first.games[1].match.black == a
    assert first.games[0].match.black == first.games[1].match.red == b
    assert first.corpus_sha256 == corpus().digest
    assert sum(first.termination_reasons.values()) == 2
    for one, two in zip(first.games, second.games, strict=True):
        assert one.match.snapshot == two.match.snapshot
        assert one.match.snapshot.game().outcome.winner == one.match.winner
        assert one.match.snapshot.game().outcome.reason == one.match.reason
        for left, right in zip(one.match.turns, two.match.turns, strict=True):
            assert left.choice.move == right.choice.move
            assert left.choice.seed == right.choice.seed
    for player in ("a", "b"):
        stats = first.summary[player]
        wins = draws = losses = 0
        choices = []
        for game in first.games:
            side = game.a_side if player == "a" else {"red": "black", "black": "red"}[game.a_side]
            winner = game.match.snapshot.game().outcome.winner
            wins += winner == side
            draws += winner is None
            losses += winner is not None and winner != side
            choices.extend(turn.choice for turn in game.match.turns if turn.side == side)
        assert (stats.wins, stats.draws, stats.losses) == (wins, draws, losses)
        assert stats.decisions == len(choices)
        assert stats.nodes == sum(choice.nodes for choice in choices)
        assert stats.elapsed_ms == sum(choice.elapsed_ms for choice in choices)
        assert stats.mean_completed_depth == sum(c.completed_depth for c in choices) / len(choices)
    restored = EvaluationRecord.model_validate_json(first.model_dump_json())
    assert restored == first


@pytest.mark.parametrize("change", ["duplicate-id", "duplicate-history", "terminal", "illegal", "training", "empty"])
def test_corpus_rejects_invalid_inputs(change) -> None:
    data = corpus().model_dump()
    opening = data["openings"][0]
    if change == "duplicate-id":
        data["openings"].append({**opening, "snapshot": {"moves": []}})
    elif change == "duplicate-history":
        data["openings"].append({**opening, "id": "other"})
    elif change == "terminal":
        opening["snapshot"]["moves"] *= 2
    elif change == "illegal":
        opening["snapshot"]["moves"] = ["a0a9"]
    elif change == "training":
        data["purpose"] = "training"
    else:
        data["openings"] = []
    with pytest.raises((ValidationError, ValueError)):
        Corpus.model_validate(data)


def test_evaluation_cli(tmp_path) -> None:
    path = tmp_path / "corpus.json"
    path.write_text(corpus().model_dump_json())
    result = subprocess.run(
        ["qi", "evaluate", "--corpus", str(path), "--player-a", "random", "--seed", "8"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert not result.stderr
    data = json.loads(result.stdout)
    assert len(data["games"]) == 2
    assert data["summary"]["a"]["wins"] == data["summary"]["b"]["losses"]
