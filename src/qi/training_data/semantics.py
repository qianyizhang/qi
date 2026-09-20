"""Versioned immediate position/label features; no inferred tactical proofs."""

from typing import Literal

from qi_game.reference import in_check, moved, other, parse_move

SemanticTag = Literal["in-check", "teacher-capture", "teacher-gives-check"]
SEMANTIC_VERSION = "immediate-position-label-v1"


def semantic_tags(board: str, turn: str, move: str) -> list[str]:
    source, target = parse_move(move)
    values = {
        "in-check": in_check(board, turn),
        "teacher-capture": board[target] != ".",
        "teacher-gives-check": in_check(moved(board, source, target), other(turn)),
    }
    return [name for name, present in values.items() if present]


def material_counts(board: str) -> dict[str, int]:
    return {piece: board.count(piece) for piece in "KABNRCPkabnrcp"}
