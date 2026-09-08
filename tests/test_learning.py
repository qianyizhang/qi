"""Optional torch integration: optimization, artifact integrity, and player adapters."""

import json
import subprocess

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.arena import play_match
from qi.game import Game, GameError, legal_moves
from qi.players import PlayerConfig, choose
from qi.protocol import Snapshot

torch = pytest.importorskip("torch", reason="Install the learning extra to run policy integration tests.")
from qi.learning.train import train  # noqa: E402
from qi.players.policy.encoding import action_id  # noqa: E402
from qi.players.policy.runtime import load_checkpoint  # noqa: E402


@pytest.fixture
def fitted(tmp_path, tiny_dataset):
    path = tmp_path / "policy.pt"
    report = train(tiny_dataset, path, steps=100, diagnostic_examples=4)
    return path, report


def test_overfit_reload_and_teacher_free_adapters(fitted, monkeypatch, tmp_path):
    path, report = fitted
    assert report["train"]["agreement"] == 1
    assert report["final_loss"] < report["initial_loss"] / 10
    assert report["reload_predictions_equal"]
    assert report["validation"]["legal_outputs"] == report["validation"]["positions"]
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(path))
    monkeypatch.setattr("qi.arena.platform", lambda: "test-platform")
    # INVARIANT: In-process policy play cannot call an external teacher.
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("Teacher subprocess during inference"))
    choice = choose(Game(), PlayerConfig("policy"))
    assert choice.move in legal_moves(Game().board, "red")
    assert choice.checkpoint_sha256 == report["checkpoint_sha256"]
    assert choice.model_calls == 1 and choice.nodes == 0
    with TestClient(create_app()) as client:
        metadata = client.get("/api/players").json()[-1]
        assert metadata["id"] == "policy" and metadata["checkpoint_sha256"] == choice.checkpoint_sha256
        response = client.post(
            "/api/opponent",
            json={"snapshot": Snapshot().model_dump(), "expected_state_hash": Game().state_hash, "player": "policy"},
        )
        assert response.status_code == 200
        assert response.json()["choice"]["move"] == choice.move
        stale = client.post(
            "/api/opponent",
            json={"snapshot": Snapshot().model_dump(), "expected_state_hash": "0" * 64, "player": "policy"},
        )
        assert stale.status_code == 409
    match = play_match(PlayerConfig("policy"), PlayerConfig("random", seed=9))
    assert match.snapshot.game().outcome.reason == match.reason
    assert match.red.checkpoint_sha256 == choice.checkpoint_sha256


def test_policy_cli_has_checkpoint_identity(fitted, monkeypatch, tmp_path):
    path, report = fitted
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(path))
    state = tmp_path / "game.json"
    state.write_text(Snapshot().model_dump_json())
    result = subprocess.run(
        ["qi", "choose", "--state", str(state), "--player", "policy"], text=True, capture_output=True, check=True
    )
    assert json.loads(result.stdout)["checkpoint_sha256"] == report["checkpoint_sha256"]


@pytest.mark.parametrize("corruption", ["architecture", "shape", "nan", "overlap", "garbage", "missing"])
def test_corrupt_checkpoints_fail_explicitly(fitted, tmp_path, corruption):
    original, _ = fitted
    path = tmp_path / f"{corruption}.pt"
    payload = torch.load(original, weights_only=True)
    if corruption == "architecture":
        payload["metadata"]["architecture"] = "unknown"
    elif corruption == "shape":
        payload["state_dict"]["0.weight"] = torch.zeros(1)
    elif corruption == "nan":
        payload["state_dict"]["0.weight"][0, 0] = float("nan")
    elif corruption == "overlap":
        payload["metadata"]["validation_inputs"] = payload["metadata"]["train_inputs"]
    if corruption == "garbage":
        path.write_bytes(b"not a checkpoint")
    elif corruption != "missing":
        torch.save(payload, path)
    with pytest.raises(GameError) as error:
        load_checkpoint(str(path))
    assert error.value.code == "invalid_checkpoint"


def test_mask_excludes_highest_illegal_logit_and_checkpoint_stays_pinned(fitted, monkeypatch):
    path, report = fitted
    payload = torch.load(path, weights_only=True)
    for tensor in payload["state_dict"].values():
        tensor.zero_()
    payload["state_dict"]["2.bias"][action_id("a0a9")] = 1000
    payload["state_dict"]["2.bias"][action_id("b2e2")] = 100
    other = path.with_name("mask.pt")
    torch.save(payload, other)
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(other))
    choice = choose(Game(), PlayerConfig("policy"))
    assert choice.move == "b2e2"
    other.write_bytes(b"replaced after loading")
    again = choose(Game(), PlayerConfig("policy"))
    assert (again.move, again.checkpoint_sha256) == (choice.move, choice.checkpoint_sha256)
    with pytest.raises(GameError, match="pinned"):
        choose(Game(), PlayerConfig("policy", checkpoint_sha256=report["checkpoint_sha256"]))
