"""Original material alpha-beta player, with a replaceable leaf evaluation function."""

from collections.abc import Callable
from dataclasses import dataclass

from qi.game import Game
from qi.players.common import MATE, BudgetExhausted, NodeBudget, evaluate, ordered_moves, terminal_score
from qi.players.core import Decision, Player, PlayerConfig, PlayerInfo

LeafEvaluator = Callable[[Game, int, int, int, NodeBudget], int]


def static_leaf(game: Game, alpha: int, beta: int, ply: int, budget: NodeBudget) -> int:
    return evaluate(game)


@dataclass
class Search:
    budget: NodeBudget
    leaf: LeafEvaluator = static_leaf

    def visit(self, game: Game, depth: int, alpha: int, beta: int, ply: int) -> int:
        self.budget.visit()
        if (score := terminal_score(game, ply)) is not None:
            return score
        if depth == 0:
            return self.leaf(game, alpha, beta, ply, self.budget)
        best = -MATE * 2
        for move in ordered_moves(game):
            score = -self.visit(game.apply(move), depth - 1, -beta, -alpha, ply + 1)
            best = max(best, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best


def search(game: Game, config: PlayerConfig, leaf: LeafEvaluator = static_leaf) -> Decision:
    moves = ordered_moves(game)
    budget = NodeBudget(config.nodes)
    worker = Search(budget, leaf)
    best_move, best_score, completed_depth = moves[0], None, 0
    for depth in range(1, config.depth + 1):
        iteration_move, iteration_score = moves[0], -MATE * 2
        try:
            budget.visit()
            for move in moves:
                score = -worker.visit(game.apply(move), depth - 1, -MATE * 2, -iteration_score, 1)
                if score > iteration_score:
                    iteration_move, iteration_score = move, score
        except BudgetExhausted:
            break
        best_move, best_score, completed_depth = iteration_move, iteration_score, depth
    return Decision(best_move, budget.nodes, completed_depth, best_score, budget.qnodes, budget.max_qply)


def select(game: Game, config: PlayerConfig) -> Decision:
    return search(game, config)


PLAYER = Player(
    PlayerInfo("alphabeta", "alphabeta-material-v1", "Alpha-beta", "Material search with a fixed-depth horizon.", True),
    select,
)
