"""Application requests and player session evidence; game interchange lives in qi_game."""

from math import isfinite
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, model_validator
from qi_game import contracts as game_contracts
from qi_game.reference import restore

from qi.players import Choice, PlayerConfig
from qi.players.validation import validate_decision


class InspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot: game_contracts.Snapshot


class ApplyRequest(InspectRequest):
    move: str = Field(min_length=4, max_length=4)
    expected_state_hash: str = Field(min_length=64, max_length=64)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


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


class PlayResult(BaseModel):
    position: game_contracts.Position
    choice: Choice
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
    snapshot: game_contracts.Snapshot
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
        game = restore(game_contracts.Snapshot(moves=self.snapshot.moves[: self.unknown_prefix]))
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
    position: game_contracts.Position
