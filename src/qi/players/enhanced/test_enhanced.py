"""Ablations preserve minimax semantics; composed features obey one work budget."""

from itertools import product

import pytest

from qi.game import Game, in_check, legal_moves
from qi.players import PlayerConfig, choose
from qi.players.alphabeta import Search, SearchOptions, search
from qi.players.common import MATE, BudgetExhausted, NodeBudget, evaluate, terminal_score
from qi.players.components.extensions import CheckExtensions
from qi.test_game import board_at


def minimax(game, depth, extra=0, ply=0):
    if (score := terminal_score(game, ply)) is not None:
        return score
    if extra and in_check(game.board, game.turn):
        depth, extra = depth + 1, extra - 1
    if depth == 0:
        return evaluate(game)
    return max(-minimax(game.apply(move), depth - 1, extra, ply + 1) for move in legal_moves(game.board, game.turn))


@pytest.mark.parametrize("ordering,exchange,table", list(product((False, True), repeat=3)))
def test_ordering_exchange_and_table_preserve_fixed_depth_score(ordering, exchange, table):
    board = board_at(e0="K", d9="k", a0="R", a5="r")
    game = Game(board=board, positions=(board + "red",))
    result = search(
        game,
        PlayerConfig(depth=2, nodes=100_000),
        options=SearchOptions(ordering=ordering, exchange=exchange, table_capacity=128 if table else 0),
    )
    assert result.completed_depth == 2
    assert result.score == minimax(game, 2)


def test_extensions_match_an_exhaustive_path_bounded_reference():
    board = board_at(e0="K", d9="k", e3="r", a0="R", e5="P")
    game = Game(board=board, positions=(board + "red",))
    result = search(game, PlayerConfig(depth=1, nodes=100_000), options=SearchOptions(extensions=CheckExtensions(2)))
    assert result.completed_depth == 1
    assert result.score == minimax(game, 1, 2)
    assert 0 < result.search_stats.max_extensions <= 2


def test_table_reuse_is_charged_and_unfinished_root_is_never_stored():
    worker = Search(NodeBudget(10_000), options=SearchOptions(table_capacity=128))
    score = worker.visit(Game(), 1, -MATE * 2, MATE * 2, 0)
    before = worker.budget.nodes
    assert worker.visit(Game(), 1, -MATE * 2, MATE * 2, 0) == score
    assert worker.budget.nodes == before + 1 and worker.tt_cutoffs == 1
    aborted = Search(NodeBudget(1), options=SearchOptions(table_capacity=128))
    with pytest.raises(BudgetExhausted):
        aborted.visit(Game(), 1, -MATE * 2, MATE * 2, 0)
    assert aborted.table.probe(Game()) is None


@pytest.mark.parametrize(
    "name",
    [
        "alphabeta-ordered",
        "alphabeta-positional",
        "alphabeta-see",
        "alphabeta-checks",
        "alphabeta-tt",
        "alphabeta-enhanced",
    ],
)
@pytest.mark.parametrize("nodes", [1, 32, 512])
def test_each_recipe_is_playable_with_a_hard_budget(name, nodes):
    choice = choose(Game(), PlayerConfig(name, nodes=nodes))
    assert choice.move in legal_moves(Game().board, "red")
    assert choice.nodes <= nodes
    assert choice.search_stats.see_nodes + choice.qnodes <= choice.nodes
    if not choice.completed_depth:
        assert choice.score is None


def test_cutoff_memory_is_recreated_for_each_decision():
    config = PlayerConfig("alphabeta-enhanced", nodes=512)
    a, b = choose(Game(), config), choose(Game(), config)
    assert (a.move, a.score, a.nodes, a.search_stats) == (b.move, b.score, b.nodes, b.search_stats)


def test_table_cannot_override_a_history_dependent_terminal_result():
    from qi.game import replay
    from qi.players.components.transpositions import Entry

    cycle = ("b0c2", "b9c7", "c2b0", "c7b9")
    live, drawn = replay(cycle), replay(cycle * 2)
    assert live.board == drawn.board and live.outcome is None
    worker = Search(NodeBudget(10), options=SearchOptions(table_capacity=128))
    worker.table.store(live, Entry(1, 0, 900, "exact", "b2e2"))
    assert worker.visit(drawn, 1, -MATE * 2, MATE * 2, 0) == 0
    assert worker.table.hits == 0
