"""Baseline legality, search budget, and value-perspective contracts."""

from dataclasses import replace

import pytest
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves, replay
from qi_game.test_game import board_at

from qi.players import PlayerConfig, choose
from qi.players.alphabeta import Search
from qi.players.common import MATE, NodeBudget, evaluate


@pytest.mark.parametrize("nodes", [1, 10, 45, 60, 128])
def test_budget_is_hard_and_move_is_always_legal(nodes: int) -> None:
    game = Game()
    choice = choose(game, PlayerConfig(nodes=nodes, depth=4))
    assert choice.nodes <= nodes
    assert choice.move in legal_moves(game.board, game.turn)
    if nodes < 45:
        assert choice.completed_depth == 0
        assert choice.score is None


def test_partial_iteration_preserves_completed_depth_one() -> None:
    game = Game()
    shallow = choose(game, PlayerConfig(depth=1, nodes=1000))
    limited = choose(game, PlayerConfig(depth=4, nodes=shallow.nodes + 1))
    assert limited.completed_depth == 1
    assert limited.move == shallow.move
    assert limited.score == shallow.score


def test_alpha_beta_prefers_free_material() -> None:
    board = board_at(e0="K", d9="k", e5="P", a0="R", a5="r")
    game = Game(board=board, positions=(board + "red",))
    choice = choose(game, PlayerConfig(depth=1, nodes=1000))
    assert choice.move == "a0a5"


def test_material_score_reverses_with_player_perspective() -> None:
    game = Game(board=board_at(e0="K", d9="k", a0="R"))
    assert evaluate(game) == 900
    assert evaluate(replace(game, turn="black")) == -900


def test_terminal_search_uses_referee_and_not_material() -> None:
    board = board_at(e9="k", e0="K", e5="P", d8="R", f8="R")
    game = Game(board=board, turn="black", positions=(board + "black",))
    assert Search(NodeBudget(10)).visit(game, 0, -2 * MATE, 2 * MATE, 2) == -MATE + 2
    draw = replay(("b0c2", "b9c7", "c2b0", "c7b9") * 2)
    assert Search(NodeBudget(10)).visit(draw, 2, -2 * MATE, 2 * MATE, 1) == 0
    with pytest.raises(GameError, match="game ends"):
        choose(draw, PlayerConfig())


def test_alpha_beta_finds_mate_in_one() -> None:
    board = board_at(e9="k", e0="K", e5="P", d8="R", f7="R", a8="R")
    game = Game(board=board, positions=(board + "red",))
    choice = choose(game, PlayerConfig(depth=1, nodes=1000))
    assert game.apply(choice.move).outcome.winner == "red"
    assert choice.score == MATE - 1


@pytest.mark.parametrize("kwargs", [{"nodes": 0}, {"depth": 0}])
def test_invalid_configuration_is_rejected(kwargs) -> None:
    with pytest.raises(GameError):
        PlayerConfig(**kwargs)


def test_completed_search_matches_exhaustive_depth_two() -> None:
    from qi.players.common import ordered_moves

    board = board_at(e0="K", d9="k", a0="R", a5="r")
    game = Game(board=board, positions=(board + "red",))

    def exhaustive(position: Game, depth: int, ply: int) -> int:
        outcome = position.outcome
        if outcome:
            if outcome.winner is None:
                return 0
            return MATE - ply if outcome.winner == position.turn else -MATE + ply
        if depth == 0:
            return evaluate(position)
        return max(-exhaustive(position.apply(move), depth - 1, ply + 1) for move in ordered_moves(position))

    moves = ordered_moves(game)
    scores = [-exhaustive(game.apply(move), 1, 1) for move in moves]
    choice = choose(game, PlayerConfig(depth=2, nodes=10000))
    assert choice.completed_depth == 2
    assert choice.score == max(scores)
    assert choice.move == moves[scores.index(max(scores))]
