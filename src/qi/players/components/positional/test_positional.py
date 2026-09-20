"""Handcrafted terms expose their contributions and preserve color symmetry."""

from dataclasses import replace

from qi_game.reference import Game

from qi.players.components.positional import breakdown, evaluate, placement


def test_symmetric_start_is_equal_and_breakdown_sums():
    terms = breakdown(Game())
    assert terms.total == evaluate(Game()) == 0
    assert terms.material == terms.placement == terms.mobility == terms.king_safety == 0


def test_knight_prefers_central_placement_and_terms_are_color_relative():
    assert placement("N", 2 * 9 + 4) > placement("N", 2 * 9)
    game = Game().apply("b0c2")
    assert breakdown(game).placement < 0
    flipped = replace(game, board=game.board[::-1].swapcase(), turn="red")
    assert breakdown(flipped) == breakdown(game)
    opposite = replace(game, turn="red")
    assert evaluate(opposite) == -evaluate(game)
