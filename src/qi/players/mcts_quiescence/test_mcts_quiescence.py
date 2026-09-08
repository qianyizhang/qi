"""Tactical leaf work is budgeted and incomplete values never enter the MCTS tree."""

from qi.game import Game
from qi.players import PlayerConfig, choose
from qi.players.common import NodeBudget
from qi.players.mcts import material_value, search
from qi.players.mcts_quiescence import tactical_value
from qi.test_game import board_at


def test_tactical_leaf_sees_a_poisoned_capture_recapture():
    board = board_at(e0="K", d9="k", a0="R", b5="r", a5="p", e5="P")
    game = Game(board=board, positions=(board + "red",)).apply("a0a5")
    budget = NodeBudget(100, nodes=1)
    assert material_value(game) < 0
    assert tactical_value(game, budget) > 0
    assert budget.nodes > 1


def test_exhausted_leaf_does_not_backup_a_partial_value():
    def expensive_leaf(game, budget):
        budget.visit()
        budget.visit()
        return 1.0

    result = search(Game(), PlayerConfig("mcts", nodes=3, rollout_plies=0), budgeted_leaf=expensive_leaf)
    assert result.nodes == 3
    assert result.mcts.leaf_nodes == 1 and result.mcts.leaf_aborts == 1
    assert result.mcts.simulations == 0
    assert all(row.visits == 0 and row.mean_value is None for row in result.mcts.root_moves)


def test_variant_accounts_for_every_leaf_node_under_the_shared_limit():
    for nodes in (1, 2, 32, 512):
        choice = choose(Game(), PlayerConfig("mcts-quiescence", nodes=nodes))
        stats = choice.mcts
        assert stats.tree_visits + stats.rollout_steps + stats.leaf_nodes == choice.nodes <= nodes
        assert sum(row.visits for row in stats.root_moves) == stats.simulations
        assert choice.qnodes <= choice.nodes
