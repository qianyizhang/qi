"""Versioned board observations and coordinate action IDs; no model dependency."""

from hashlib import sha256

from qi_game.execution import GameView
from qi_game.reference import Game, parse_move

ENCODING = "absolute-board-turn-v1"
ARCHITECTURE = "mlp-1261-64-8100-v1"
PIECES = "KABNRCPkabnrcp"
INPUTS = 1261
ACTIONS = 8100


def input_key(game: Game | GameView) -> str:
    return sha256(f"{ENCODING}:{game.board}:{game.turn}".encode()).hexdigest()


def encode(game: Game) -> list[float]:
    features = [0.0] * INPUTS
    for square, piece in enumerate(game.board):
        if piece != ".":
            features[PIECES.index(piece) * 90 + square] = 1.0
    features[-1] = float(game.turn == "black")
    return features


def action_id(move: str) -> int:
    source, target = parse_move(move)
    return source * 90 + target
