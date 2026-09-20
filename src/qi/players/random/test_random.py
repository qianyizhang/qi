"""Seeded random selection is legal, repeatable, and read-only."""

from qi_game.reference import Game, legal_moves

from qi.players import PlayerConfig, choose


def test_seeded_random_is_repeatable_and_does_not_mutate() -> None:
    game = Game()
    config = PlayerConfig("random", seed=42)
    first, second = choose(game, config), choose(game, config)
    assert first.move == second.move
    assert first.move in legal_moves(game.board, game.turn)
    assert game == Game()
    assert first.nodes == 0 and first.score is None
    assert first.elapsed_ms >= 0
