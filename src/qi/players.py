"""Small deterministic baselines, independent of transport and training."""

import random
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from qi.game import Game, GameError, legal_moves, owner, parse_move

PlayerKind = Literal["random", "alphabeta"]
MATE = 100_000
VALUES = {"K": 0, "R": 900, "C": 450, "N": 400, "B": 200, "A": 200, "P": 100}


@dataclass(frozen=True)
class PlayerConfig:
    kind: PlayerKind = "alphabeta"
    seed: int = 0
    depth: int = 2
    nodes: int = 128

    def __post_init__(self) -> None:
        if self.kind not in ("random", "alphabeta"):
            raise GameError("invalid_player", "Choose random or alphabeta.")
        if not 1 <= self.depth <= 8 or self.nodes < 1:
            raise GameError("invalid_budget", "Depth must be 1-8 and nodes must be positive.")

    @property
    def version(self) -> str:
        return "random-v1" if self.kind == "random" else "alphabeta-material-v1"


@dataclass(frozen=True)
class Choice:
    move: str
    state_hash: str
    player_version: str
    seed: int
    nodes: int
    completed_depth: int
    score: int | None
    elapsed_ms: float


def evaluate(game: Game) -> int:
    """Material plus crossed-soldier bonus, from side-to-move perspective."""
    total = 0
    for i, piece in enumerate(game.board):
        if piece == ".":
            continue
        side = owner(piece)
        value = VALUES[piece.upper()]
        if piece.upper() == "P" and (i // 9 >= 5 if side == "red" else i // 9 <= 4):
            value += 100
        total += value if side == game.turn else -value
    return total


def ordered_moves(game: Game) -> list[str]:
    def key(move: str) -> tuple[int, str]:
        _, target = parse_move(move)
        return -VALUES.get(game.board[target].upper(), 0), move

    return sorted(legal_moves(game.board, game.turn), key=key)


class BudgetExhausted(Exception):
    pass


@dataclass
class Search:
    budget: int
    nodes: int = 0

    def visit(self, game: Game, depth: int, alpha: int, beta: int, ply: int) -> int:
        if self.nodes >= self.budget:
            raise BudgetExhausted
        self.nodes += 1
        outcome = game.outcome
        if outcome:
            if outcome.winner is None:
                return 0
            return MATE - ply if outcome.winner == game.turn else -MATE + ply
        if depth == 0:
            return evaluate(game)
        best = -MATE * 2
        for move in ordered_moves(game):
            score = -self.visit(game.apply(move), depth - 1, -beta, -alpha, ply + 1)
            best = max(best, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best


def choose(game: Game, config: PlayerConfig) -> Choice:
    started = perf_counter()
    if game.outcome:
        raise GameError("game_over", "Cannot select a move after the game ends.")
    moves = ordered_moves(game)
    if config.kind == "random":
        move = random.Random(config.seed).choice(moves)
        return Choice(move, game.state_hash, config.version, config.seed, 0, 0, None, (perf_counter() - started) * 1000)
    search = Search(config.nodes)
    best_move, best_score, completed_depth = moves[0], None, 0
    for depth in range(1, config.depth + 1):
        iteration_move, iteration_score = moves[0], -MATE * 2
        try:
            # Count the root once per iteration, within the same total budget.
            if search.nodes >= search.budget:
                raise BudgetExhausted
            search.nodes += 1
            for move in moves:
                score = -search.visit(game.apply(move), depth - 1, -MATE * 2, -iteration_score, 1)
                if score > iteration_score:
                    iteration_move, iteration_score = move, score
        except BudgetExhausted:
            break
        best_move, best_score, completed_depth = iteration_move, iteration_score, depth
    return Choice(
        best_move,
        game.state_hash,
        config.version,
        config.seed,
        search.nodes,
        completed_depth,
        best_score,
        (perf_counter() - started) * 1000,
    )
