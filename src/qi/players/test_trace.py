"""Recording is observational, complete for charged work, and explicitly bounded."""

from dataclasses import asdict

import pytest

from qi.game import Game
from qi.players import PlayerConfig, choose
from qi.players.trace import Recorder, recording

PLAYERS = [
    "alphabeta",
    "quiescence",
    "alphabeta-ordered",
    "alphabeta-positional",
    "alphabeta-see",
    "alphabeta-checks",
    "alphabeta-tt",
    "alphabeta-enhanced",
    "alphabeta-lean",
    "alphabeta-pvs",
    "mcts",
    "mcts-quiescence",
]


def deterministic(choice):
    result = asdict(choice)
    result.pop("elapsed_ms")
    return result


@pytest.mark.parametrize("player", PLAYERS)
@pytest.mark.parametrize("nodes", [1, 64, 512])
def test_trace_preserves_choices_and_accounts_for_every_visit(player, nodes):
    game = Game().apply("b2e2").apply("b9c7")
    config = PlayerConfig(player, seed=7, nodes=nodes, depth=3)
    expected = deterministic(choose(game, config))
    recorder = Recorder()
    with recording(recorder):
        actual = deterministic(choose(game, config))
    assert actual == expected
    assert recorder.export()["complete"]
    assert [item["visit"] for item in recorder.events if item["kind"] == "work"] == list(range(1, actual["nodes"] + 1))
    assert all(item["parent"] is None or item["parent"] < item["id"] for item in recorder.events)
    if actual["search_stats"] is not None:
        assert sum(item["kind"] == "cache-hit" for item in recorder.events) == actual["search_stats"]["tt_hits"]
    if player.startswith("mcts"):
        retained = [item for item in recorder.events if item["kind"] == "mcts-tree"]
        assert retained[0]["visits"] == actual["mcts"]["simulations"]
        assert (
            sum(item["visits"] for item in retained if item["parent"] == retained[0]["id"])
            == actual["mcts"]["simulations"]
        )


def test_recording_limit_does_not_interrupt_search_or_claim_full_trace():
    config = PlayerConfig("alphabeta-enhanced", nodes=128)
    expected = deterministic(choose(Game(), config))
    recorder = Recorder(3)
    with recording(recorder):
        actual = deterministic(choose(Game(), config))
    assert actual == expected
    assert len(recorder.events) == 3
    assert recorder.dropped > 0 and not recorder.export()["complete"]
    assert deterministic(choose(Game(), config)) == expected


def test_trace_captures_exchange_quiescence_and_interrupted_iterations():
    recorder = Recorder()
    with recording(recorder):
        choose(Game(), PlayerConfig("alphabeta-enhanced", nodes=256, depth=3))
    kinds = {item["kind"] for item in recorder.events}
    assert {"exchange", "exchange-step", "quiescence", "iteration", "alpha-beta"} <= kinds
    assert any(item.get("interruption") == "BudgetExhausted" for item in recorder.events)
