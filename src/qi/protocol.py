"""Validated replay interchange shared by CLI and HTTP."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from qi.game import START_FEN, Game, in_check, legal_moves, replay
from qi.players import Choice


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    ruleset: Literal["xiangqi-training-v1"] = "xiangqi-training-v1"
    initial_fen: Literal[START_FEN] = START_FEN
    moves: list[str] = Field(default_factory=list, max_length=300)

    def game(self) -> Game:
        return replay(tuple(self.moves))


class InspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot: Snapshot


class ApplyRequest(InspectRequest):
    move: str = Field(min_length=4, max_length=4)
    expected_state_hash: str = Field(min_length=64, max_length=64)


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


def inspect(game: Game) -> Position:
    outcome = game.outcome
    return Position(
        snapshot=Snapshot(moves=list(game.moves)),
        board=game.board,
        turn=game.turn,
        ply=len(game.moves),
        state_hash=game.state_hash,
        legal_moves=[] if outcome else list(legal_moves(game.board, game.turn)),
        in_check=in_check(game.board, game.turn),
        outcome=Result(winner=outcome.winner, reason=outcome.reason) if outcome else None,
    )


class OpponentRequest(InspectRequest):
    model_config = ConfigDict(extra="forbid")
    expected_state_hash: str = Field(min_length=64, max_length=64)
    player: Literal["random", "alphabeta"] = "alphabeta"
    seed: int = Field(default=0, ge=0, le=2_147_483_647, strict=True)
    depth: int = Field(default=2, ge=1, le=4, strict=True)
    nodes: int = Field(default=128, ge=1, le=512, strict=True)


class OpponentResult(BaseModel):
    position: Position
    choice: Choice
