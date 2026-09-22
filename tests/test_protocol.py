"""Shared CLI/HTTP replay and rejection contracts."""

import json
import subprocess

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from qi_game.contracts import Snapshot
from qi_game.reference import restore

from qi.api import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_http_uses_injected_referee_without_owning_its_representation(monkeypatch):
    from qi_game.reference import PythonReferee

    initial = PythonReferee().inspect(Snapshot())
    child = PythonReferee().apply(Snapshot(), "b2e2", initial.state_hash)
    calls = []

    class Backend:
        def inspect(self, snapshot):
            calls.append(("inspect", snapshot.model_dump()))
            return child if snapshot.moves else initial

        def apply(self, snapshot, move, expected_hash):
            calls.append(("apply", snapshot.model_dump(), move, expected_hash))
            return child

    def forbidden(*args):
        pytest.fail("The transport must delegate game operations to the injected referee")

    monkeypatch.setattr("qi.api.restore", forbidden)
    with TestClient(create_app(referee=Backend())) as client:
        assert client.post("/api/new").json() == initial.model_dump()
        assert client.post("/api/inspect", json={"snapshot": child.snapshot.model_dump()}).json() == child.model_dump()
        response = client.post(
            "/api/apply",
            json={
                "snapshot": initial.snapshot.model_dump(),
                "move": "b2e2",
                "expected_state_hash": initial.state_hash,
            },
        )
        assert response.json() == child.model_dump()
    assert calls == [
        ("inspect", initial.snapshot.model_dump()),
        ("inspect", child.snapshot.model_dump()),
        ("apply", initial.snapshot.model_dump(), "b2e2", initial.state_hash),
    ]


def test_game_types_have_one_owner_without_legacy_reexports():
    from importlib.util import find_spec

    from qi import protocol

    assert find_spec("qi.game") is None
    for name in ("Snapshot", "Position", "Result", "inspect"):
        assert not hasattr(protocol, name)


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


@pytest.mark.parametrize("player", ["random", "alphabeta", "quiescence"])
def test_player_choice_matches_python_and_replays(client, player) -> None:
    from dataclasses import asdict

    from qi.players import PlayerConfig, choose

    snapshot = Snapshot(moves=["b2e2"])
    game = restore(snapshot)
    response = client.post(
        "/api/play/choose",
        json={
            "snapshot": snapshot.model_dump(),
            "expected_state_hash": game.state_hash,
            "controller": {
                "player": player,
                "settings": {"seed": 7} if player == "random" else {"nodes": 64, "depth": 2},
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    actual = data["choice"]
    expected = asdict(choose(game, PlayerConfig(player, seed=8 if player == "random" else 1, depth=2, nodes=64)))
    actual.pop("elapsed_ms")
    expected.pop("elapsed_ms")
    assert actual == expected
    position = data["position"]
    assert position["snapshot"]["moves"] == ["b2e2", actual["move"]]
    assert client.post("/api/inspect", json={"snapshot": position["snapshot"]}).json() == position
    assert snapshot.moves == ["b2e2"]


def test_player_stale_guard_precedes_search(client, monkeypatch) -> None:
    def forbidden(*args):
        pytest.fail("Stale requests must not start search")

    monkeypatch.setattr("qi.api.choose", forbidden)
    response = client.post(
        "/api/play/choose",
        json={
            "snapshot": Snapshot().model_dump(),
            "expected_state_hash": "0" * 64,
            "controller": {"player": "alphabeta"},
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_state"


@pytest.mark.parametrize(
    "settings",
    [{"nodes": 100001}, {"depth": 9}, {"seed": -1}, {"seed": True}, {"player": "teacher"}, {"engine": "/tmp/anything"}],
)
def test_browser_player_rejects_unbounded_or_external_settings(client, settings) -> None:
    initial = client.post("/api/new").json()
    response = client.post(
        "/api/play/choose",
        json={
            "snapshot": initial["snapshot"],
            "expected_state_hash": initial["state_hash"],
            "controller": {"player": "alphabeta", "settings": settings},
        },
    )
    assert response.status_code in (409, 422)


def test_browser_player_rejects_terminal_game(client) -> None:
    snapshot = Snapshot(moves=["b0c2", "b9c7", "c2b0", "c7b9"] * 2)
    response = client.post(
        "/api/play/choose",
        json={
            "snapshot": snapshot.model_dump(),
            "expected_state_hash": restore(snapshot).state_hash,
            "controller": {"player": "alphabeta"},
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "game_over"


def test_http_errors_preserve_messages_and_status(client):
    response = client.get("/api/benchmarks/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Unknown benchmark."}}
    response = client.put("/api/new")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    assert "POST" in response.headers["allow"]
