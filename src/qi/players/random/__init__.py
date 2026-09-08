"""Uniform seeded selection over the original deterministic move ordering."""

import random

from qi.game import Game
from qi.players.common import ordered_moves
from qi.players.core import Decision, Player, PlayerConfig, PlayerInfo


def select(game: Game, config: PlayerConfig) -> Decision:
    return Decision(random.Random(config.seed).choice(ordered_moves(game)))


PLAYER = Player(
    PlayerInfo("random", "random-v1", "Random", "Uniform random legal moves with a fixed seed.", False), select
)
