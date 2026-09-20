"""Tactical continuations, check evasions, and bounded incomplete search."""

import pytest
from qi_game.reference import Game, in_check, legal_moves, replay
from qi_game.test_game import board_at

from qi.players import PlayerConfig, choose
from qi.players.alphabeta import Search
from qi.players.common import MATE, BudgetExhausted, NodeBudget, evaluate
from qi.players.quiescence import quiesce


def run_quiescence(game: Game, nodes: int = 1000, alpha: int = -2 * MATE, beta: int = 2 * MATE):
    budget = NodeBudget(nodes)
    budget.visit()
    return quiesce(game, alpha, beta, 0, budget), budget


def test_opening_capture_accounts_for_recapture() -> None:
    after_capture = Game().apply("b2b9")
    assert evaluate(after_capture) == -400  # Black appears to have lost a horse.
    score, _ = run_quiescence(after_capture)
    assert score == 50  # Black can take the 450-point cannon with a rook.
    baseline = choose(Game(), PlayerConfig("alphabeta", depth=1, nodes=128))
    improved = choose(Game(), PlayerConfig("quiescence", depth=1, nodes=128))
    assert baseline.move == "b2b9" and baseline.score == 400
    assert improved.move not in ("b2b9", "h2h9")
    assert improved.completed_depth == 1 and improved.score == 0


def test_frontier_and_capture_child_count_once_each() -> None:
    board = board_at(e0="K", d9="k", a0="R", a5="r")
    game = Game(board=board, positions=(board + "red",))
    score, budget = run_quiescence(game)
    assert score == 900
    assert (budget.nodes, budget.qnodes, budget.max_qply) == (2, 2, 1)


def test_in_check_searches_quiet_evasion_without_stand_pat_cutoff() -> None:
    board = board_at(e0="K", d9="k", e3="r", a0="R", e5="P")
    game = Game(board=board, positions=(board + "red",))
    assert in_check(game.board, game.turn)
    assert evaluate(game) > 0
    assert "e0f0" in legal_moves(game.board, game.turn)
    # A beta cutoff on the current material score would incorrectly avoid the evasion.
    with pytest.raises(BudgetExhausted):
        run_quiescence(game, nodes=1, beta=0)
    _, budget = run_quiescence(game, beta=0)
    assert budget.qnodes > 1


def test_terminal_values_precede_material_and_preserve_history() -> None:
    draw = replay(("b0c2", "b9c7", "c2b0", "c7b9") * 2)
    assert draw.board == Game().board and draw.turn == Game().turn
    assert run_quiescence(draw, nodes=1)[0] == 0
    with pytest.raises(BudgetExhausted):
        run_quiescence(Game(), nodes=1)
    board = board_at(e9="k", e0="K", e5="P", d8="R", f8="R")
    mate = Game(board=board, turn="black", positions=(board + "black",))
    assert run_quiescence(mate, nodes=1)[0] == -MATE


@pytest.mark.parametrize("nodes", [1, 10, 64, 128, 512])
def test_shared_budget_includes_quiescence_and_aborted_iterations(nodes) -> None:
    game = Game()
    choice = choose(game, PlayerConfig("quiescence", depth=4, nodes=nodes))
    assert game == Game()
    assert choice.move in legal_moves(game.board, game.turn)
    assert 0 <= choice.qnodes <= choice.nodes <= nodes
    assert choice.max_qply <= choice.qnodes
    if choice.completed_depth == 0:
        assert choice.score is None


def test_unfinished_iteration_cannot_replace_completed_result() -> None:
    first = choose(Game(), PlayerConfig("quiescence", depth=1, nodes=10000))
    limited = choose(Game(), PlayerConfig("quiescence", depth=3, nodes=first.nodes + 5))
    assert limited.completed_depth == 1
    assert (limited.move, limited.score) == (first.move, first.score)
    assert limited.nodes == first.nodes + 5
    assert limited.qnodes > first.qnodes


def test_checked_frontier_cannot_be_reported_as_completed_on_budget_exhaustion() -> None:
    board = board_at(e0="K", d9="k", e3="r", a0="R", e5="P")
    game = Game(board=board, positions=(board + "red",))
    budget = NodeBudget(1)
    with pytest.raises(BudgetExhausted):
        Search(budget, quiesce).visit(game, 0, -MATE, 0, 0)
    assert budget.nodes == budget.qnodes == 1
