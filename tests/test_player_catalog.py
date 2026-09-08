"""A registered player reaches selection, arena, CLI, and HTTP without dispatch edits."""

import json
import subprocess
from dataclasses import asdict
from types import MappingProxyType

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.arena import play_match
from qi.game import Game, GameError, legal_moves
from qi.players import Decision, Player, PlayerConfig, PlayerInfo, catalog, choose, list_players


def register_test_player(monkeypatch, decision=None):
    def select(game, config):
        return decision if decision is not None else Decision(legal_moves(game.board, game.turn)[0])

    player = Player(PlayerInfo("test-player", "test-v1", "Test player", "Test-only catalog extension.", False), select)
    monkeypatch.setattr(catalog, "PLAYERS", MappingProxyType({**catalog.PLAYERS, player.info.id: player}))


def test_registered_player_is_discovered_and_runs_a_replayable_match(monkeypatch) -> None:
    register_test_player(monkeypatch)
    config = PlayerConfig("test-player")
    assert choose(Game(), config).player_version == "test-v1"
    match = play_match(config, PlayerConfig("random"))
    assert match.snapshot.game().outcome.reason == match.reason
    with TestClient(create_app()) as client:
        assert "test-player" in [p["id"] for p in client.get("/api/players").json()]
        initial = client.post("/api/new").json()
        response = client.post(
            "/api/opponent",
            json={
                "snapshot": initial["snapshot"],
                "expected_state_hash": initial["state_hash"],
                "player": "test-player",
            },
        )
        assert response.status_code == 200
        assert response.json()["choice"]["player_version"] == "test-v1"


@pytest.mark.parametrize("decision", [Decision("a0a9"), Decision("b2e2", nodes=129), Decision("b2e2", qnodes=1)])
def test_common_boundary_rejects_invalid_player_results(monkeypatch, decision) -> None:
    register_test_player(monkeypatch, decision)
    with pytest.raises(GameError) as error:
        choose(Game(), PlayerConfig("test-player"))
    assert error.value.code == "invalid_player_result"


def test_unknown_player_rejected_at_selection() -> None:
    with pytest.raises(GameError) as error:
        choose(Game(), PlayerConfig("unknown"))
    assert error.value.code == "invalid_player"


def test_catalog_cli_and_api_have_identical_metadata() -> None:
    result = subprocess.run(["qi", "players"], text=True, capture_output=True, check=True)
    assert not result.stderr
    expected = [asdict(player) for player in list_players()]
    assert json.loads(result.stdout) == expected
    with TestClient(create_app()) as client:
        assert client.get("/api/players").json() == expected
    assert {p["id"] for p in expected} == {
        "random",
        "alphabeta",
        "quiescence",
        "mcts",
        "alphabeta-ordered",
        "alphabeta-positional",
        "alphabeta-see",
        "alphabeta-checks",
        "alphabeta-tt",
        "alphabeta-enhanced",
        "mcts-quiescence",
    }


def test_quiescence_cli_returns_budget_and_replay_guard(tmp_path) -> None:
    state = tmp_path / "state.json"
    state.write_text('{"moves": []}')
    result = subprocess.run(
        ["qi", "choose", "--state", str(state), "--player", "quiescence", "--nodes", "128"],
        text=True,
        capture_output=True,
        check=True,
    )
    choice = json.loads(result.stdout)
    assert choice["qnodes"] > 0 and choice["max_qply"] > 0
    assert Game().apply(choice["move"], choice["state_hash"]).moves == (choice["move"],)


def test_catalog_rejects_duplicate_ids_and_reserved_human_mode() -> None:
    from dataclasses import replace

    player = catalog.get_player("random")
    with pytest.raises(ValueError, match="unique"):
        catalog.build_catalog((player, player))
    with pytest.raises(ValueError, match="human"):
        catalog.build_catalog((replace(player, info=replace(player.info, id="human")),))
