"""Extensions are path-local allowances, including checks at the root."""

from qi_game.reference import Game
from qi_game.test_game import board_at

from qi.players.components.extensions import CheckExtensions


def test_check_consumes_one_allowance_and_siblings_keep_their_own_copy():
    board = board_at(e0="K", d9="k", e3="r", a0="R", e5="P")
    checked = Game(board=board, positions=(board + "red",))
    policy = CheckExtensions(2)
    assert policy.apply(checked, 0, 2) == (1, 1)
    assert policy.apply(checked, 0, 1) == (1, 0)
    assert policy.apply(checked, 0, 0) == (0, 0)
    assert policy.apply(checked, 0, 2) == (1, 1)
    assert policy.apply(Game(), 2, 2) == (2, 2)
