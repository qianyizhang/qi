"""Xiangqi identity, outcomes, and rule errors; no implementation dependencies."""

from dataclasses import dataclass
from typing import Literal

Side = Literal["red", "black"]
RULESET = "xiangqi-training-v1"
START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"
START_BOARD = "RNBAKABNR..........C.....C.P.P.P.P.P..................p.p.p.p.p.c.....c..........rnbakabnr"


class GameError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class Outcome:
    winner: Side | None
    reason: Literal["checkmate", "stalemate", "repetition", "ply_limit"]
