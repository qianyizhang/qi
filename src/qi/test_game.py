"""Movement, adjudication, and replay invariants."""

import random
from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qi.game import Game, GameError, in_check, legal_moves, parse_move, reaches, replay


def board_at(**pieces: str) -> str:
    board = ["."] * 90
    for square, piece in pieces.items():
        index, _ = parse_move(square + square)
        board[index] = piece
    return "".join(board)


def can(board: str, move: str) -> bool:
    return reaches(board, *parse_move(move))


@pytest.mark.parametrize("move,allowed", [("b0c2", True), ("b0d1", True), ("b0c1", False)])
def test_horse_geometry(move: str, allowed: bool) -> None:
    assert can(board_at(b0="N"), move) == allowed


def test_horse_leg_blocks_only_its_two_destinations() -> None:
    board = board_at(b0="N", b1="P")
    assert not can(board, "b0c2")
    assert not can(board, "b0a2")
    assert can(board, "b0d1")


def test_elephant_eye_and_river() -> None:
    assert can(board_at(c0="B"), "c0e2")
    assert not can(board_at(c0="B", d1="P"), "c0e2")
    assert not can(board_at(c4="B"), "c4e6")
    assert not can(board_at(c5="b"), "c5e3")
    assert can(board_at(c9="b"), "c9e7")


def test_cannon_requires_exactly_one_screen_for_capture() -> None:
    assert can(board_at(b2="C"), "b2b7")
    assert not can(board_at(b2="C", b7="r"), "b2b7")
    assert can(board_at(b2="C", b4="P", b7="r"), "b2b7")
    assert not can(board_at(b2="C", b4="P", b5="p", b7="r"), "b2b7")
    assert not can(board_at(b2="C", b4="P"), "b2b7")
    assert not can(board_at(b2="C", b4="P", b7="R"), "b2b7")


def test_chariot_blocking() -> None:
    assert can(board_at(a0="R", a3="p"), "a0a3")
    assert not can(board_at(a0="R", a2="P", a3="p"), "a0a3")
    assert not can(board_at(a0="R"), "a0b1")


def test_palace_restrictions() -> None:
    assert can(board_at(e0="K"), "e0e1")
    assert not can(board_at(d0="K"), "d0c0")
    assert not can(board_at(e2="K"), "e2e3")
    assert can(board_at(d0="A"), "d0e1")
    assert not can(board_at(d0="A"), "d0c1")
    assert not can(board_at(e7="k"), "e7e6")


@pytest.mark.parametrize(
    "piece,start,forward,sideways,backward,crossed",
    [
        ("P", "e3", "e4", "d3", "e2", False),
        ("P", "e5", "e6", "d5", "e4", True),
        ("p", "e6", "e5", "d6", "e7", False),
        ("p", "e4", "e3", "d4", "e5", True),
    ],
)
def test_soldier_direction_and_river(piece, start, forward, sideways, backward, crossed) -> None:
    board = board_at(**{start: piece})
    assert can(board, start + forward)
    assert can(board, start + sideways) == crossed
    assert not can(board, start + backward)


def test_flying_generals_and_self_check() -> None:
    board = board_at(e0="K", e9="k", e5="R")
    assert not in_check(board, "red")
    assert "e5d5" not in legal_moves(board, "red")
    assert "e5e6" in legal_moves(board, "red")
    assert in_check(board_at(e0="K", e9="k"), "red")
    assert in_check(board_at(e0="K", e9="k"), "black")
    board = board_at(e0="K", d9="k", e1="R", e8="r")
    assert "e1d1" not in legal_moves(board, "red")


def test_initial_position_and_perft_two() -> None:
    game = Game()
    moves = legal_moves(game.board, game.turn)
    assert len(moves) == 44
    assert sum(len(legal_moves((child := game.apply(move)).board, child.turn)) for move in moves) == 1920


def test_errors_preserve_immutable_state() -> None:
    game = Game()
    for move, code in [
        ("b2e2", "stale_state"),
        ("bad", "invalid_move"),
        ("a9a8", "wrong_player"),
        ("a0a9", "illegal_move"),
    ]:
        with pytest.raises(GameError) as error:
            game.apply(move, "wrong" if code == "stale_state" else game.state_hash)
        assert error.value.code == code
        assert game == Game()


def test_threefold_counts_initial_and_ends_game() -> None:
    cycle = ("b0c2", "b9c7", "c2b0", "c7b9")
    first = replay(cycle)
    assert first.board == Game().board
    assert first.state_hash != Game().state_hash
    assert first.outcome is None
    end = replay(cycle * 2)
    assert end.outcome.reason == "repetition"
    assert end.outcome.winner is None
    with pytest.raises(GameError, match="already ended"):
        end.apply("a3a4")


def test_repetition_identity_includes_side() -> None:
    game = Game()
    wrong_turn = game.board + "black"
    assert replace(game, positions=(wrong_turn, wrong_turn, game.board + "red")).outcome is None


@pytest.mark.parametrize("mate", [False, True])
def test_no_moves_loses_even_at_ply_limit(mate: bool) -> None:
    pieces = dict(e9="k", e0="K", e5="P", d8="R", f8="R")
    if mate:
        pieces["e8"] = "R"
    board = board_at(**pieces)
    game = Game(board, "black", ("a0a1",) * 300, (board + "black",) * 3)
    assert game.outcome.winner == "red"
    assert game.outcome.reason == ("checkmate" if mate else "stalemate")


def test_ply_limit_at_exactly_300() -> None:
    game = replace(Game(), moves=("a0a1",) * 299)
    assert game.outcome is None
    end = game.apply("a3a4")
    assert end.outcome.reason == "ply_limit"
    assert end.outcome.winner is None


@given(st.lists(st.integers(min_value=0, max_value=10000), max_size=35))
@settings(max_examples=12, deadline=None)
def test_legal_trajectories_keep_king_safe_and_replay_exactly(choices: list[int]) -> None:
    game = Game()
    for choice in choices:
        if game.outcome:
            break
        moves = legal_moves(game.board, game.turn)
        previous = game
        game = game.apply(moves[choice % len(moves)])
        assert not in_check(game.board, previous.turn)
        assert len(game.moves) == len(previous.moves) + 1
    assert replay(game.moves) == game


def test_complete_300_ply_trajectory_replays_from_empty_cache() -> None:
    rng = random.Random(12)
    game = Game()
    while not game.outcome:
        game = game.apply(rng.choice(legal_moves(game.board, game.turn)))
    assert len(game.moves) == 300
    assert game.outcome.reason == "ply_limit"
    replay.cache_clear()
    assert replay(game.moves) == game
