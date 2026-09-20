"""Match artifacts preserve reproducible decisions and replayable outcomes."""

import json
import subprocess
from dataclasses import asdict, replace

import pytest
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import Game, replay, restore

from qi.arena import play_match
from qi.players import PlayerConfig


def test_seeded_match_repeats_except_measured_timing() -> None:
    config = PlayerConfig("random", seed=17)
    first, second = play_match(config, config), play_match(config, config)
    assert first.snapshot == second.snapshot
    assert first.winner == second.winner
    assert first.reason == second.reason
    final = restore(first.snapshot)
    assert final.outcome.winner == first.winner
    assert final.outcome.reason == first.reason
    for a, b in zip(first.turns, second.turns, strict=True):
        x, y = asdict(a), asdict(b)
        x["choice"].pop("elapsed_ms")
        y["choice"].pop("elapsed_ms")
        assert x == y


def test_match_resumes_opening_without_counting_it_as_player_decisions() -> None:
    opening = replay(("b2e2", "b9c7"))
    record = play_match(PlayerConfig("random"), PlayerConfig("random"), opening)
    assert record.opening.moves == list(opening.moves)
    assert record.snapshot.moves[:2] == list(opening.moves)
    assert record.turns[0].ply == 3
    assert record.turns[0].choice.seed == 2
    assert len(record.turns) == len(record.snapshot.moves) - 2


def test_terminal_opening_rejected() -> None:
    game = replay(("b0c2", "b9c7", "c2b0", "c7b9") * 2)
    with pytest.raises(GameError):
        play_match(PlayerConfig(), PlayerConfig(), game)


def test_cli_choice_and_match(tmp_path) -> None:
    path = tmp_path / "opening.json"
    path.write_text(Snapshot().model_dump_json())
    result = subprocess.run(
        ["qi", "choose", "--state", str(path), "--nodes", "1"], capture_output=True, text=True, check=True
    )
    choice = json.loads(result.stdout)
    assert choice["nodes"] == 1
    assert choice["completed_depth"] == 0
    result = subprocess.run(
        ["qi", "match", "--red", "random", "--black", "random", "--seed", "7"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert not result.stderr
    record = json.loads(result.stdout)
    game = restore(Snapshot.model_validate(record["snapshot"]))
    assert record["reason"] == game.outcome.reason
    assert record["winner"] == game.outcome.winner
    assert record["red"]["seed"] == 7
    assert record["black"]["seed"] == 8


def test_arena_rejects_an_opening_not_reconstructible_from_its_history() -> None:
    forged = replace(Game(), turn="black")
    with pytest.raises(GameError, match="Opening must replay"):
        play_match(PlayerConfig("random"), PlayerConfig("random"), forged)
