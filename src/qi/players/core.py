"""The small contract shared by every in-process player."""

from collections.abc import Callable
from dataclasses import dataclass

from qi.game import Game, GameError


@dataclass(frozen=True)
class PlayerConfig:
    kind: str = "alphabeta"
    seed: int = 0
    depth: int = 2
    nodes: int = 128
    checkpoint_sha256: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.depth <= 8 or self.nodes < 1:
            raise GameError("invalid_budget", "Depth must be 1-8 and nodes must be positive.")


@dataclass(frozen=True)
class Decision:
    move: str
    nodes: int = 0
    completed_depth: int = 0
    score: int | None = None
    qnodes: int = 0
    max_qply: int = 0
    checkpoint_sha256: str | None = None
    model_calls: int = 0


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
    qnodes: int = 0
    max_qply: int = 0
    checkpoint_sha256: str | None = None
    model_calls: int = 0


@dataclass(frozen=True)
class PlayerInfo:
    id: str
    version: str
    label: str
    description: str
    uses_search: bool
    default_nodes: int = 128
    default_depth: int = 2
    checkpoint_sha256: str | None = None


@dataclass(frozen=True)
class Player:
    info: PlayerInfo
    select: Callable[[Game, PlayerConfig], Decision]
    checkpoint: Callable[[], str] | None = None
    available: Callable[[], bool] | None = None
