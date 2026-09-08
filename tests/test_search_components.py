"""All recipes reach external adapters and paired replayable play."""

import json
import subprocess
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.arena import play_match
from qi.game import Game
from qi.players import PlayerConfig, choose
from qi.players.enhanced import PLAYERS
from qi.protocol import Snapshot

RECIPES = [player.info.id for player in PLAYERS] + ["mcts-quiescence"]


@pytest.mark.parametrize("name", RECIPES)
def test_recipe_cli_and_http_use_the_same_composition(name, tmp_path):
    path = tmp_path / "game.json"
    path.write_text(Snapshot().model_dump_json())
    result = subprocess.run(
        ["qi", "choose", "--state", str(path), "--player", name, "--nodes", "128"],
        text=True,
        capture_output=True,
        check=True,
    )
    cli = json.loads(result.stdout)
    expected = json.loads(json.dumps(asdict(choose(Game(), PlayerConfig(name, nodes=128)))))
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/opponent",
            json={
                "snapshot": Snapshot().model_dump(),
                "expected_state_hash": Game().state_hash,
                "player": name,
                "nodes": 128,
            },
        )
        assert response.status_code == 200
        actual = response.json()["choice"]
    for record in (cli, actual, expected):
        record.pop("elapsed_ms")
    assert cli == actual == expected


@pytest.mark.parametrize("name", RECIPES)
def test_recipe_plays_both_colors_and_every_result_replays(name):
    config, opponent = PlayerConfig(name, seed=7, nodes=16), PlayerConfig("random", seed=8)
    for red, black in ((config, opponent), (opponent, config)):
        match = play_match(red, black)
        assert (match.snapshot.game().outcome.winner, match.snapshot.game().outcome.reason) == (
            match.winner,
            match.reason,
        )
        assert all(turn.choice.nodes <= 16 for turn in match.turns if turn.choice.player_version != "random-v1")
