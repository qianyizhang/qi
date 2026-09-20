"""Configured engine participation shares the referee and identity boundary."""

import json
import sys
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import restore
from test_teacher import fake_teacher

from qi.api import create_app
from qi.players import PlayerConfig, bind_config, bindings, choose, list_players, policy, resolve_selection
from qi.players.validation import validate_decision


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
    game = restore(Snapshot(moves=["b2e2"]))
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
        choose(restore(Snapshot()), PlayerConfig("trained"))


@pytest.mark.parametrize("boundary", ["http", "python"])
def test_requested_resources_resolve_once_per_decision(tmp_path, monkeypatch, boundary):
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
                    },
                    {
                        "id": "unused",
                        "label": "Unavailable unused policy",
                        "implementation": "policy",
                        "checkpoint": str(tmp_path / "missing.pt"),
                    },
                ]
            }
        )
    )
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(config_file))
    pinned = bind_config(PlayerConfig("pika", nodes=10, depth=2))
    configuration_reads = Mock(wraps=bindings.configured_bindings)
    resource_reads = Mock(wraps=bindings.file_identity)
    monkeypatch.setattr(bindings, "configured_bindings", configuration_reads)
    monkeypatch.setattr(bindings, "file_identity", resource_reads)
    monkeypatch.setattr("qi.teacher.digest", lambda *_: pytest.fail("Engine hashed after resolution"))
    snapshot = Snapshot(moves=["b2e2"])
    game = restore(snapshot)

    for _ in range(2):
        configuration_reads.reset_mock()
        resource_reads.reset_mock()
        if boundary == "http":
            with TestClient(create_app()) as client:
                response = client.post(
                    "/api/play/choose",
                    json={
                        "snapshot": snapshot.model_dump(),
                        "expected_state_hash": game.state_hash,
                        "controller": {
                            "player": "pika",
                            "binding_sha256": pinned.binding_sha256,
                            "settings": {"nodes": 10, "depth": 2},
                        },
                    },
                )
            assert response.status_code == 200, response.json()
            result = response.json()
            assert result["config"]["seed"] == 1
            assert result["config"]["work_semantics"] == "engine_native"
            assert result["choice"]["binding_sha256"] == pinned.binding_sha256
        else:
            assert choose(game, pinned).binding_sha256 == pinned.binding_sha256
        assert configuration_reads.call_count == 1
        assert [call.args[0] for call in resource_reads.call_args_list] == [
            str(teacher.engine),
            str(teacher.network),
        ]


def test_resolved_operation_keeps_implementation_and_next_operation_rechecks(tmp_path, monkeypatch):
    config_file = tmp_path / "players.json"

    def configure(implementation):
        config_file.write_text(
            json.dumps({"players": [{"id": "selected", "label": "Selected", "implementation": implementation}]})
        )

    configure("random")
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(config_file))
    pinned = bind_config(PlayerConfig("selected"))
    resolved = resolve_selection("selected", {"seed": 5}, pinned.binding_sha256)
    configure("alphabeta")
    game = restore(Snapshot())
    choice = choose(game, resolved)
    expected = choose(game, PlayerConfig("random", seed=5))
    assert (choice.move, choice.player_version, choice.nodes) == (expected.move, expected.player_version, 0)
    assert choice.binding_sha256 == pinned.binding_sha256
    with pytest.raises(GameError, match="differ"):
        choose(game, pinned)


def test_named_checkpoint_replacement_is_checked_before_cached_inference(tmp_path, monkeypatch):
    checkpoint = tmp_path / "policy.pt"
    checkpoint.write_bytes(b"original checkpoint")
    config_file = tmp_path / "players.json"
    config_file.write_text(
        json.dumps(
            {
                "players": [
                    {"id": "trained", "label": "Trained", "implementation": "policy", "checkpoint": str(checkpoint)}
                ]
            }
        )
    )
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(config_file))
    pinned = bind_config(PlayerConfig("trained"))
    loaded = SimpleNamespace(sha256=pinned.checkpoint_sha256, predict=lambda _: "b2e2")
    load = Mock(return_value=loaded)
    monkeypatch.setattr(policy, "load_model", load)
    game = restore(Snapshot())
    assert choose(game, pinned).checkpoint_sha256 == pinned.checkpoint_sha256
    load.assert_called_once_with(str(checkpoint), pinned.checkpoint_sha256)
    checkpoint.write_bytes(b"replacement checkpoint")
    with pytest.raises(GameError, match="differ"):
        choose(game, pinned)
    assert load.call_count == 1
    current = next(entry for entry in list_players() if entry.id == "trained")
    assert current.available
    assert current.binding_sha256 != pinned.binding_sha256
    assert current.checkpoint_sha256 == sha256(checkpoint.read_bytes()).hexdigest()


def test_default_checkpoint_catalog_reports_process_pin_without_loading_runtime(tmp_path, monkeypatch):
    checkpoint = tmp_path / "default.pt"
    original = b"original checkpoint"
    checkpoint.write_bytes(original)
    monkeypatch.delenv("QI_PLAYERS_CONFIG", raising=False)
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(checkpoint))
    monkeypatch.setitem(sys.modules, "qi.players.policy.runtime", None)
    monkeypatch.setattr(policy, "_pinned_checkpoints", {})

    def metadata():
        return next(entry for entry in list_players() if entry.id == "policy")

    advertised = metadata()
    assert advertised.available and advertised.checkpoint_sha256 == sha256(original).hexdigest()
    resolved = resolve_selection("policy", {}, None, advertised.checkpoint_sha256)
    assert resolved.config.checkpoint_sha256 == advertised.checkpoint_sha256
    loaded = SimpleNamespace(sha256=advertised.checkpoint_sha256, predict=lambda _: "b2e2")
    load = Mock(return_value=loaded)
    monkeypatch.setattr(policy, "load_model", load)
    game = restore(Snapshot())
    choice = choose(game, resolved)
    assert choice.checkpoint_sha256 == advertised.checkpoint_sha256
    assert load.call_count == 1

    checkpoint.write_bytes(b"replacement checkpoint")
    stale = metadata()
    assert not stale.available
    assert stale.checkpoint_sha256 == choice.checkpoint_sha256
    assert "Restart" in stale.unavailable_reason
    with pytest.raises(GameError, match="Restart"):
        resolve_selection("policy", {}, None, stale.checkpoint_sha256)
    assert load.call_count == 1
    assert choose(game, PlayerConfig("policy")).checkpoint_sha256 == choice.checkpoint_sha256

    checkpoint.unlink()
    missing = metadata()
    assert not missing.available and missing.checkpoint_sha256 == choice.checkpoint_sha256
    assert "restart" in missing.unavailable_reason
    checkpoint.write_bytes(original)
    restored = metadata()
    assert restored.available and restored.checkpoint_sha256 == choice.checkpoint_sha256
