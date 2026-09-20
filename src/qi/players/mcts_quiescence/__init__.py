"""Plain UCT with a bounded tactical leaf sharing its work allowance."""

from qi_game.reference import Game

from qi.players.common import MATE, NodeBudget
from qi.players.core import Player, PlayerConfig, PlayerInfo
from qi.players.mcts import search
from qi.players.quiescence import quiesce


def tactical_value(game: Game, budget: NodeBudget) -> float:
    score = quiesce(game, -2 * MATE, 2 * MATE, 0, budget, max_plies=2)
    if abs(score) >= MATE - 1000:
        return 1.0 if score > 0 else -1.0
    return score / (abs(score) + 900)


def select(game: Game, config: PlayerConfig):
    return search(game, config, budgeted_leaf=tactical_value)


PLAYER = Player(
    PlayerInfo(
        "mcts-quiescence",
        "mcts-quiescence-v1",
        "MCTS · quiescence leaves",
        "UCT with budgeted tactical leaf estimates.",
        True,
        default_nodes=512,
        default_rollout_plies=8,
    ),
    select,
)
