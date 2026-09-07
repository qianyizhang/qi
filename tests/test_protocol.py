"""Shared CLI/HTTP replay and rejection contracts."""

import json
import subprocess

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from qi.api import create_app
from qi.protocol import Snapshot


@pytest.fixture
def client():
    return TestClient(create_app())


def test_api_move_save_replay_and_stale_guard(client) -> None:
    initial = client.post("/api/new").json()
    request = {"snapshot": initial["snapshot"], "move": "b2e2", "expected_state_hash": initial["state_hash"]}
    result = client.post("/api/apply", json=request)
    assert result.status_code == 200
    position = result.json()
    assert position["turn"] == "black"
    assert position["ply"] == 1
    assert client.post("/api/inspect", json={"snapshot": position["snapshot"]}).json() == position
    request["snapshot"] = position["snapshot"]
    stale = client.post("/api/apply", json=request)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_state"


def test_reject_illegal_history_and_wrong_ruleset(client) -> None:
    snapshot = Snapshot().model_dump()
    snapshot["moves"] = ["a0a9"]
    assert client.post("/api/inspect", json={"snapshot": snapshot}).json()["error"]["code"] == "illegal_move"
    snapshot["ruleset"] = "future"
    assert client.post("/api/inspect", json={"snapshot": snapshot}).status_code == 422
    assert client.post("/api/apply", json={}).json()["error"]["code"] == "invalid_request"


def test_snapshot_forbids_derived_state_and_overlong_history() -> None:
    with pytest.raises(ValidationError):
        Snapshot.model_validate({"board": "fake"})
    with pytest.raises(ValidationError):
        Snapshot(moves=["a0a1"] * 301)


def test_cli_api_parity_and_clean_error_streams(tmp_path, client) -> None:
    file = tmp_path / "game.json"
    new = subprocess.run(["qi", "new"], text=True, capture_output=True, check=True)
    file.write_text(new.stdout)
    assert not new.stderr
    inspect = subprocess.run(["qi", "inspect", "--state", str(file)], text=True, capture_output=True, check=True)
    position = json.loads(inspect.stdout)
    assert position == client.post("/api/new").json()
    applied = subprocess.run(
        ["qi", "apply", "--state", str(file), "--move", "b2e2", "--expected-state-hash", position["state_hash"]],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(applied.stdout)["moves"] == ["b2e2"]
    assert json.loads(file.read_text())["moves"] == []
    file.write_text('{"moves":["a0a9"]}')
    invalid = subprocess.run(["qi", "inspect", "--state", str(file)], text=True, capture_output=True)
    assert invalid.returncode == 1
    assert not invalid.stdout
    assert json.loads(invalid.stderr)["error"]["code"] == "illegal_move"
