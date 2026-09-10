"""Validated replay interchange shared by CLI and HTTP."""

from math import isfinite
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, field_validator, model_validator

from qi.game import START_FEN, Game, in_check, legal_moves, replay
from qi.players import Choice, PlayerConfig
from qi.players.catalog import get_player
from qi.players.validation import validate_decision


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
    player: str = "alphabeta"
    seed: int = Field(default=0, ge=0, le=2_147_483_647, strict=True)
    depth: int = Field(default=2, ge=1, le=4, strict=True)
    nodes: int = Field(default=128, ge=1, le=512, strict=True)
    rollout_plies: int = Field(default=8, ge=0, le=64, strict=True)

    @field_validator("player")
    @classmethod
    def registered_player(cls, value: str) -> str:
        get_player(value)
        return value


class OpponentResult(BaseModel):
    position: Position
    choice: Choice


class Controller(BaseModel):
    """A UI selection stores identity, never a resource path."""

    model_config = ConfigDict(extra="forbid")
    player: str = Field(default="human", min_length=1, max_length=64)
    settings: dict[str, StrictFloat] = Field(default_factory=dict, max_length=8)
    binding_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    checkpoint_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def controller_shape(self) -> Self:
        if any(not isfinite(value) for value in self.settings.values()):
            raise ValueError("Settings must be finite numbers.")
        if self.player == "human" and (self.settings or self.binding_sha256 or self.checkpoint_sha256):
            raise ValueError("Human controllers have no computer settings or resources.")
        return self


class Controllers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    red: Controller = Field(default_factory=Controller)
    black: Controller = Field(default_factory=Controller)


class PlayRequest(InspectRequest):
    expected_state_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    controller: Controller


class PlayResult(OpponentResult):
    config: PlayerConfig


class ConfigurationChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ply: int = Field(ge=0, le=300)
    controllers: Controllers


class SessionMove(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ply: int = Field(ge=1, le=300)
    side: Literal["red", "black"]
    controller: Controller
    config: PlayerConfig | None = None
    choice: Choice | None = None


class GameSession(BaseModel):
    """Exploratory session evidence; validation does not resolve live resources."""

    model_config = ConfigDict(extra="forbid")
    format: Literal["qi-game-session"] = "qi-game-session"
    schema_version: Literal[1] = 1
    snapshot: Snapshot
    controllers: Controllers
    unknown_prefix: int = Field(default=0, ge=0, le=300)
    changes: list[ConfigurationChange] = Field(min_length=1, max_length=2000)
    history: list[SessionMove] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def validate_history(self) -> Self:
        size = len(self.snapshot.moves)
        if self.unknown_prefix > size or self.changes[0].ply != self.unknown_prefix:
            raise ValueError("Configuration history must start at the known prefix boundary.")
        if (
            any(a.ply > b.ply for a, b in zip(self.changes, self.changes[1:], strict=False))
            or self.changes[-1].ply > size
        ):
            raise ValueError("Configuration changes must follow ply order.")
        if self.controllers != self.changes[-1].controllers:
            raise ValueError("Current controllers differ from the last configuration change.")
        if [entry.ply for entry in self.history] != list(range(self.unknown_prefix + 1, size + 1)):
            raise ValueError("Known move attribution must be contiguous.")
        game = Snapshot(moves=self.snapshot.moves[: self.unknown_prefix]).game()
        for entry in self.history:
            active = next(change for change in reversed(self.changes) if change.ply < entry.ply)
            controller = getattr(active.controllers, game.turn)
            if entry.side != game.turn or entry.controller != controller:
                raise ValueError("Move attribution differs from the configured controller.")
            if controller.player == "human":
                if entry.config is not None or entry.choice is not None:
                    raise ValueError("Human moves cannot contain computed player evidence.")
            else:
                choice, config = entry.choice, entry.config
                if choice is None or config is None:
                    raise ValueError("Computer moves require actual configuration and diagnostics.")
                if (
                    config.kind != controller.player
                    or config.binding_sha256 != controller.binding_sha256
                    or config.checkpoint_sha256 != controller.checkpoint_sha256
                    or choice.binding_sha256 != config.binding_sha256
                    or choice.checkpoint_sha256 != config.checkpoint_sha256
                    or choice.seed != config.seed
                    or config.seed != controller.settings.get("seed", 0) + len(game.moves)
                    or choice.state_hash != game.state_hash
                    or choice.move != self.snapshot.moves[entry.ply - 1]
                    or not isfinite(choice.elapsed_ms)
                    or choice.elapsed_ms < 0
                ):
                    raise ValueError("Computer move identity differs from recorded configuration or replay.")
                for key, value in controller.settings.items():
                    if key != "seed" and getattr(config, key, None) != value:
                        raise ValueError("Actual player settings differ from the selected settings.")
                validate_decision(choice, config, game)
            game = game.apply(self.snapshot.moves[entry.ply - 1])
        return self


class SessionResult(BaseModel):
    session: GameSession
    position: Position
