"""Checkpoint-backed policy registration; importing the catalog never imports torch."""

import os
from pathlib import Path

from qi.game import Game, GameError
from qi.players.core import Decision, Player, PlayerConfig, PlayerInfo


def configured_path() -> str | None:
    value = os.environ.get("QI_POLICY_CHECKPOINT")
    return str(Path(value).resolve()) if value else None


def configured_model():
    path = configured_path()
    if path is None:
        raise GameError("missing_checkpoint", "Set QI_POLICY_CHECKPOINT to a trained local checkpoint.")
    try:
        from qi.players.policy.runtime import load_checkpoint
    except ImportError as exc:
        raise GameError("learning_not_installed", "Install the learning extra: uv sync --extra learning.") from exc
    return load_checkpoint(path)


def select(game: Game, config: PlayerConfig) -> Decision:
    loaded = configured_model()
    if config.checkpoint_sha256 is not None and config.checkpoint_sha256 != loaded.sha256:
        raise GameError("checkpoint_mismatch", "Configured policy differs from the pinned player checkpoint.")
    return Decision(loaded.predict(game), checkpoint_sha256=loaded.sha256, model_calls=1)


PLAYER = Player(
    PlayerInfo("policy", "policy-mlp-v1", "Learned policy", "Local teacher-imitation checkpoint; one CPU pass.", False),
    select,
    checkpoint=lambda: configured_model().sha256,
    available=lambda: configured_path() is not None,
)
