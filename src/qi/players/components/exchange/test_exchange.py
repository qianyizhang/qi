"""Xiangqi exchange geometry and explicit heuristic-work accounting."""

import pytest

from qi.game import Game, GameError, legal_moves
from qi.players.common import BudgetExhausted, NodeBudget
from qi.players.components.exchange import estimate
from qi.test_game import board_at


def test_poisoned_opening_capture_accounts_for_recapture():
    budget = NodeBudget(10)
    assert estimate(Game().board, "red", "b2b9", budget) == -50
    assert budget.nodes == budget.see_nodes == 2


def test_moving_a_screen_enables_a_cannon_recapture():
    board = board_at(e0="K", d9="k", e9="c", e7="p", e6="R", e5="p")
    assert estimate(board, "red", "e6e5") == -800


def test_pinned_defender_cannot_recapture():
    board = board_at(d0="K", e9="k", e1="R", e5="r", a4="R", a5="p")
    assert "a4a5" in legal_moves(board, "red")
    assert estimate(board, "red", "a4a5") == 100


def test_quiet_moves_cost_no_exchange_visits_and_illegal_moves_fail():
    budget = NodeBudget(1)
    assert estimate(Game().board, "red", "b2e2", budget) == 0
    assert budget.nodes == 0
    with pytest.raises(GameError):
        estimate(Game().board, "red", "a0a9", budget)


def test_exchange_budget_cannot_overshoot():
    budget = NodeBudget(1)
    with pytest.raises(BudgetExhausted):
        estimate(Game().board, "red", "b2b9", budget)
    assert budget.nodes == budget.see_nodes == 1
