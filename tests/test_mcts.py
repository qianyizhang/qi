"""MCTS diagnostics survive CLI, HTTP, arena serialization, and shared validation."""

import json
import subprocess
from dataclasses import replace
from types import MappingProxyType

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.evaluation import Corpus, EvaluationRecord, Opening, evaluate_batch
from qi.game import Game, GameError
from qi.players import Player, PlayerConfig, PlayerInfo, catalog, choose
from qi.players.mcts import search
from qi.protocol import Snapshot


def test_cli_http_parity_including_rollout_budget_and_root_statistics(tmp_path):
    snapshot = Snapshot(moves=["b2e2", "b9c7"])
    path = tmp_path / "game.json"
    path.write_text(snapshot.model_dump_json())
    cli = subprocess.run(
        [
            "qi",
            "choose",
            "--state",
            str(path),
            "--player",
            "mcts",
            "--seed",
            "9",
            "--nodes",
            "128",
            "--rollout-plies",
            "3",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    expected = json.loads(cli.stdout)
    assert not cli.stderr
    with TestClient(create_app()) as client:
        metadata = next(row for row in client.get("/api/players").json() if row["id"] == "mcts")
        assert (metadata["default_nodes"], metadata["default_rollout_plies"]) == (512, 8)
        payload = {
            "snapshot": snapshot.model_dump(),
            "expected_state_hash": snapshot.game().state_hash,
            "player": "mcts",
            "seed": 7,
            "nodes": 128,
            "rollout_plies": 3,
        }
        response = client.post("/api/opponent", json=payload)
        assert response.status_code == 200
        actual = response.json()["choice"]
        actual.pop("elapsed_ms")
        expected.pop("elapsed_ms")
        assert actual == expected
        assert Snapshot.model_validate(response.json()["position"]["snapshot"]).game() == snapshot.game().apply(
            actual["move"]
        )
        for limit in (-1, 65, True):
            assert client.post("/api/opponent", json={**payload, "rollout_plies": limit}).status_code == 422


def test_paired_arena_records_replay_and_summarize_mcts_work():
    corpus = Corpus(
        id="mcts-test",
        provenance="Hermetic test opening",
        openings=[Opening(id="initial", description="Start", snapshot=Snapshot())],
    )
    record = evaluate_batch(
        corpus, PlayerConfig("mcts", seed=7, nodes=16, rollout_plies=2), PlayerConfig("random", seed=8)
    )
    restored = EvaluationRecord.model_validate_json(record.model_dump_json())
    choices = []
    for game in restored.games:
        assert game.match.snapshot.game().outcome.reason == game.match.reason
        choices.extend(turn.choice for turn in game.match.turns if turn.side == game.a_side)
    summary = restored.summary["a"]
    assert summary.simulations == sum(choice.mcts.simulations for choice in choices)
    assert summary.rollout_steps == sum(choice.mcts.rollout_steps for choice in choices)
    assert summary.terminal_simulations + summary.heuristic_cutoffs == summary.simulations
    assert restored.summary["b"].simulations == 0
    assert all(choice.nodes <= 16 for choice in choices)
    assert restored.player_a.rollout_plies == 2


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("visits", "MCTS simulation totals disagree"),
        ("steps", "MCTS work does not partition total nodes"),
        ("nan", "finite mean value"),
        ("illegal", "root actions differ from referee"),
        ("duplicate", "root actions contain duplicates"),
    ],
)
def test_shared_boundary_rejects_inconsistent_mcts_diagnostics(monkeypatch, fault, reason):
    decision = search(Game(), PlayerConfig("mcts", nodes=10))
    stats = decision.mcts
    if fault == "visits":
        stats = replace(stats, simulations=stats.simulations + 1)
    elif fault == "steps":
        stats = replace(stats, rollout_steps=stats.rollout_steps + 1)
    else:
        roots = list(stats.root_moves)
        visited = next(index for index, row in enumerate(roots) if row.visits)
        if fault == "nan":
            roots[visited] = replace(roots[visited], mean_value=float("nan"))
        elif fault == "illegal":
            roots[visited] = replace(roots[visited], move="a0a9")
        else:
            roots.append(roots[0])
        stats = replace(stats, root_moves=tuple(roots))
    fake = Player(
        PlayerInfo("bad-mcts", "test-v1", "Test", "Test", True), lambda game, config: replace(decision, mcts=stats)
    )
    monkeypatch.setattr(catalog, "PLAYERS", MappingProxyType({**catalog.PLAYERS, "bad-mcts": fake}))
    with pytest.raises(GameError, match=reason) as error:
        choose(Game(), PlayerConfig("bad-mcts"))
    assert error.value.code == "invalid_player_result"
