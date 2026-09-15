"""Fast generation must match the independent exhaustive movement-geometry oracle."""

import random

import pytest

from qi.game import Game, in_check, is_attacked, legal_moves, moved, other, owner, reaches, square
from qi.test_game import board_at


def exhaustive_check(board, side):
    king = "K" if side == "red" else "k"
    if king not in board:
        return True
    target = board.index(king)
    return any(
        piece != "." and owner(piece) != side and reaches(board, source, target) for source, piece in enumerate(board)
    )


def exhaustive_moves(board, side):
    return tuple(
        square(source) + square(target)
        for source, piece in enumerate(board)
        if piece != "." and owner(piece) == side
        for target in range(90)
        if board[target].upper() != "K"
        and reaches(board, source, target)
        and not exhaustive_check(moved(board, source, target), side)
    )


def arbitrary_boards(count, seed=714):
    rng = random.Random(seed)
    for _ in range(count):
        board = ["."] * 90
        squares = rng.sample(range(90), rng.randrange(2, 35))
        board[squares[0]], board[squares[1]] = "K", "k"
        for target in squares[2:]:
            board[target] = rng.choice("RNCBAPrncbap")
        yield "".join(board)


def test_arbitrary_positions_match_exhaustive_geometry_in_order():
    # Off-palace kings/pieces exercise the public geometry boundary too.
    for board in arbitrary_boards(160):
        for side in ("red", "black"):
            assert in_check(board, side) == exhaustive_check(board, side)
            assert legal_moves(board, side) == exhaustive_moves(board, side)


@pytest.mark.parametrize("seed", range(8))
def test_reachable_positions_match_exhaustive_geometry(seed):
    rng = random.Random(seed)
    game = Game()
    for _ in range(100):
        for side in (game.turn, other(game.turn)):
            assert in_check(game.board, side) == exhaustive_check(game.board, side)
            assert legal_moves(game.board, side) == exhaustive_moves(game.board, side)
        if game.outcome:
            break
        game = game.apply(rng.choice(legal_moves(game.board, game.turn)))


@pytest.mark.parametrize("blockers", [dict(), dict(e3="P"), dict(e3="p", e5="P")])
def test_cannon_check_counts_both_friendly_and_enemy_screens(blockers):
    board = board_at(e0="K", d9="k", e8="c", **blockers)
    assert in_check(board, "red") == (len(blockers) == 1)
    assert legal_moves(board, "red") == exhaustive_moves(board, "red")


@pytest.mark.parametrize("side", ["red", "black"])
def test_missing_king_is_checked_and_has_no_legal_moves(side):
    board = board_at(a0="R", a9="r")
    assert in_check(board, side)
    assert legal_moves(board, side) == ()


def test_arbitrary_target_attacks_match_exhaustive_reaches():
    # Include empty targets and attackers' own pieces: cannon/flying-king
    # behavior here differs from checks against an occupied enemy king square.
    for board in arbitrary_boards(80, seed=815):
        for side in ("red", "black"):
            for target in range(90):
                expected = any(
                    piece != "." and owner(piece) == side and reaches(board, source, target)
                    for source, piece in enumerate(board)
                )
                assert is_attacked(board, target, side) == expected


@pytest.mark.parametrize(
    ("pieces", "move", "allowed"),
    [
        (dict(e0="K", d9="k", e8="c", a3="R"), "a3e3", False),
        (dict(e0="K", d9="k", e8="c", e3="P", a2="R"), "a2e2", True),
        (dict(e0="K", d9="k", e8="c", e3="P", a8="R"), "a8e8", True),
        (dict(e0="K", d9="k", d2="n", d1="R"), "d1c1", False),
        (dict(e0="K", d9="k", d2="n", d1="R"), "d1d2", True),
        (dict(e0="K", d9="k", f8="r"), "e0f0", False),
    ],
)
def test_occupancy_changes_and_captured_attackers(pieces, move, allowed):
    board = board_at(**pieces)
    assert (move in legal_moves(board, "red")) == allowed
    assert legal_moves(board, "red") == exhaustive_moves(board, "red")
