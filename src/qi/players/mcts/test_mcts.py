"""Search perspective, referee history, and accounting under exact work limits."""

from dataclasses import replace
from random import Random

import pytest
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves, replay
from qi_game.test_game import board_at

from qi.players import PlayerConfig, choose
from qi.players.common import NodeBudget
from qi.players.mcts import Node, Search, backup, search, value


@pytest.mark.parametrize("side", ["red", "black"])
def test_uct_selects_against_child_perspective(side):
    game = Game(turn=side)
    root = Node(game, [], visits=20)
    opponent = "black" if side == "red" else "red"
    good_for_opponent = Node(Game(turn=opponent), [], visits=10, total_value=8)
    bad_for_opponent = Node(Game(turn=opponent), [], visits=10, total_value=-8)
    root.children = {"a0a1": good_for_opponent, "a0a2": bad_for_opponent}
    assert root.select_child() is bad_for_opponent


def test_backup_alternates_perspectives_on_every_ply():
    root = Node.create(Game(), Random(0))
    child = Node.create(root.game.apply("b2e2"), Random(0))
    grandchild = Node.create(child.game.apply("b9c7"), Random(0))
    backup([root, child, grandchild], 0.75)
    assert [node.mean_value for node in (root, child, grandchild)] == [0.75, -0.75, 0.75]
    assert [node.visits for node in (root, child, grandchild)] == [1, 1, 1]


def test_uct_explores_an_under_visited_child():
    root = Node(Game(), [], visits=101)
    root.children = {
        "a0a1": Node(Game(turn="black"), [], visits=100, total_value=-90),
        "a0a2": Node(Game(turn="black"), [], visits=1, total_value=0),
    }
    assert root.select_child() is root.children["a0a2"]


@pytest.mark.parametrize("nodes", [1, 2, 3, 10, 11, 128, 512])
@pytest.mark.parametrize("rollout_plies", [0, 8])
def test_all_work_is_bounded_and_root_visits_equal_completed_simulations(nodes, rollout_plies):
    game = Game()
    choice = choose(game, PlayerConfig("mcts", nodes=nodes, rollout_plies=rollout_plies))
    stats = choice.mcts
    assert choice.nodes == nodes == stats.tree_visits + stats.rollout_steps
    assert stats.simulations == sum(move.visits for move in stats.root_moves)
    assert stats.simulations == stats.terminal_simulations + stats.rollout_cutoffs + stats.budget_cutoffs
    assert {row.move for row in stats.root_moves} == set(legal_moves(game.board, game.turn))
    assert choice.completed_depth == 0 and choice.score is None
    assert game == Game()
    if nodes == 1:
        assert stats.simulations == 0 and stats.unfinished_simulations == 1
        assert choice.move == sorted(legal_moves(game.board, game.turn))[0]
        assert all(row.mean_value is None for row in stats.root_moves)
    else:
        winner = max(
            stats.root_moves, key=lambda row: (row.visits, row.mean_value if row.mean_value is not None else -2)
        )
        assert choice.move == winner.move


def test_expansion_covers_each_root_move_before_revisiting():
    moves = legal_moves(Game().board, "red")
    decision = search(Game(), PlayerConfig("mcts", nodes=2 * len(moves), rollout_plies=0))
    assert all(row.visits == 1 for row in decision.mcts.root_moves)
    assert decision.mcts.max_tree_depth == 1


def test_tree_revisits_are_charged_even_when_no_new_state_is_created(monkeypatch):
    calls = 0
    original = Game.apply

    def counted(game, move, expected_state_hash=None):
        nonlocal calls
        calls += 1
        return original(game, move, expected_state_hash)

    monkeypatch.setattr(Game, "apply", counted)
    decision = search(Game(), PlayerConfig("mcts", nodes=512, rollout_plies=0))
    assert calls < decision.mcts.tree_visits - decision.mcts.simulations
    assert decision.mcts.rollout_steps == 0
    assert decision.nodes == 512


def test_seed_reproduces_decisions_and_depth_does_not_limit_mcts():
    config = PlayerConfig("mcts", seed=7, nodes=512)
    a, b = choose(Game(), config), choose(Game(), replace(config, depth=8))
    assert replace(a, elapsed_ms=0) == replace(b, elapsed_ms=0)
    c = choose(Game(), replace(config, seed=8))
    assert c.mcts.root_moves != a.mcts.root_moves


def test_rollout_preserves_repetition_history_and_stops_at_actual_draw(monkeypatch):
    cycle = ("b0c2", "b9c7", "c2b0", "c7b9")
    recent = replay(cycle[:3])
    repeated = replay(cycle + cycle[:3])
    assert recent.board == repeated.board and recent.turn == repeated.turn
    rng = Random(0)
    monkeypatch.setattr(rng, "choice", lambda moves: "c7b9")
    first = Search(NodeBudget(1), rng, 1, lambda game: 0.75)
    second = Search(NodeBudget(1), rng, 1, lambda game: pytest.fail("Terminal state reached evaluator"))
    assert first.rollout(recent) == -0.75
    assert second.rollout(repeated) == 0
    assert first.rollout_cutoffs == second.terminal_simulations == 1
    assert second.rollout_steps == 1


def test_budget_cutoff_uses_leaf_estimate_without_pretending_it_is_a_draw():
    decision = search(Game(), PlayerConfig("mcts", nodes=2), leaf=lambda game: 0.5)
    row = next(row for row in decision.mcts.root_moves if row.visits)
    assert row.mean_value == -0.5
    assert decision.mcts.budget_cutoffs == 1
    assert decision.mcts.terminal_simulations == 0


def test_terminal_results_override_leaf_and_terminal_selection_is_rejected():
    board = board_at(e9="k", e0="K", e5="P", d8="R", f8="R")
    mate = Game(board=board, turn="black", positions=(board + "black",))
    assert mate.outcome.winner == "red"
    assert value(mate, lambda game: pytest.fail("Terminal state reached evaluator")) == -1
    with pytest.raises(GameError, match="terminal"):
        search(mate, PlayerConfig("mcts"))


def test_search_prefers_a_proven_one_move_win():
    board = board_at(e9="k", e0="K", e5="P", d7="R", f8="R")
    game = Game(board=board, positions=(board + "red",))
    decision = search(game, PlayerConfig("mcts", nodes=1024, rollout_plies=0))
    assert game.apply(decision.move).outcome.winner == "red"
    assert decision.mcts.terminal_simulations > 0
    selected = next(row for row in decision.mcts.root_moves if row.move == decision.move)
    assert selected.mean_value == 1


@pytest.mark.parametrize("estimate", [float("nan"), float("inf"), 1.01, -1.01])
def test_leaf_contract_rejects_nonfinite_or_unbounded_estimates(estimate):
    with pytest.raises(GameError) as error:
        search(Game(), PlayerConfig("mcts", nodes=2), leaf=lambda game: estimate)
    assert error.value.code == "invalid_evaluator"


@pytest.mark.parametrize("rollout_plies", [-1, 65])
def test_rollout_limits_are_validated(rollout_plies):
    with pytest.raises(GameError, match="Rollout"):
        PlayerConfig("mcts", rollout_plies=rollout_plies)
