"""Validated replay data; importing schemas does not load a referee or any player."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from qi_game.core import START_FEN


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    ruleset: Literal["xiangqi-training-v1"] = "xiangqi-training-v1"
    initial_fen: Literal[START_FEN] = START_FEN
    moves: list[str] = Field(default_factory=list, max_length=300)


class Result(BaseModel):
    winner: Literal["red", "black"] | None
    reason: str


class Position(BaseModel):
    snapshot: Snapshot
    board: str
    turn: Literal["red", "black"]
    ply: int
    state_hash: str
    legal_moves: list[str]
    in_check: bool
    outcome: Result | None
