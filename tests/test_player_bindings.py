"""Configured engine participation shares the referee and identity boundary."""

import json
import sys
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from test_teacher import fake_teacher

from qi.api import create_app
from qi.game import GameError
from qi.players import PlayerConfig, bind_config, choose, list_players
from qi.players.validation import validate_decision
from qi.protocol import Snapshot


def test_pikafish_native_work_history_and_resource_pinning(tmp_path, monkeypatch):
    teacher = fake_teacher(tmp_path)
    config_file = tmp_path / "players.json"
    config_file.write_text(
        json.dumps(
            {
                "players": [
                    {
                        "id": "pika",
                        "label": "Test Pikafish",
                        "implementation": "pikafish",
                        "engine": str(teacher.engine),
                        "network": str(teacher.network),
                        "threads": 2,
                        "hash_mb": 32,
                    }
                ]
            }
        )
    )
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(config_file))
    metadata = next(entry for entry in list_players() if entry.id == "pika")
    assert metadata.implementation_id == "pikafish" and metadata.settings["nodes"].unit == "native nodes"
    config = bind_config(PlayerConfig("pika", nodes=10, depth=2))
    game = Snapshot(moves=["b2e2"]).game()
    choice = choose(game, config)
    assert choice.nodes == 0 and choice.completed_depth == 0
    assert choice.engine.reported_nodes == 42 > config.nodes
    assert choice.engine.reported_depth == 3 > config.depth
    assert choice.engine.score.kind == "mate" and choice.engine.score.bound == "upperbound"
    assert choice.binding_sha256 == config.binding_sha256
    commands = (tmp_path / "commands").read_text()
    assert "position startpos moves b2e2" in commands
    assert "setoption name Threads value 2" in commands
    assert "setoption name Hash value 32" in commands
    with TestClient(create_app()) as client:
        selection = {"player": "pika", "binding_sha256": metadata.binding_sha256, "settings": {"timeout_seconds": 0.15}}
        assert client.post("/api/play/controller/inspect", json=selection).status_code == 409
        selection["settings"]["timeout_seconds"] = 0.2
        assert client.post("/api/play/controller/inspect", json=selection).status_code == 200
    with pytest.raises(ValueError, match="semantics"):
        validate_decision(replace(choice, engine=None), config, game)
    with pytest.raises(ValueError, match="cannot claim"):
        validate_decision(replace(choice, nodes=1), config, game)
    teacher.network.write_bytes(b"changed")
    with pytest.raises(GameError, match="differ"):
        choose(game, config)
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/play/choose",
            json={
                "snapshot": Snapshot(moves=["b2e2"]).model_dump(),
                "expected_state_hash": game.state_hash,
                "controller": {"player": "pika", "binding_sha256": metadata.binding_sha256},
            },
        )
        assert response.status_code == 409


def test_named_checkpoint_without_learning_extra_has_a_clear_error(tmp_path, monkeypatch):
    checkpoint = tmp_path / "policy.pt"
    checkpoint.write_bytes(b"local checkpoint")
    config = tmp_path / "players.json"
    config.write_text(
        json.dumps(
            {
                "players": [
                    {"id": "trained", "label": "Trained", "implementation": "policy", "checkpoint": str(checkpoint)}
                ]
            }
        )
    )
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(config))
    monkeypatch.setitem(sys.modules, "qi.players.policy.runtime", None)
    with pytest.raises(GameError, match="learning extra"):
        choose(Snapshot().game(), PlayerConfig("trained"))
