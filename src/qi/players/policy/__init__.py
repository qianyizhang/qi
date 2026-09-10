"""Checkpoint-backed policy registration; importing the catalog never imports torch."""

import os
from pathlib import Path

from qi.game import Game, GameError
from qi.players.core import Decision, Player, PlayerConfig, PlayerInfo


def configured_path() -> str | None:
    value = os.environ.get("QI_POLICY_CHECKPOINT")
    return str(Path(value).resolve()) if value else None


def load_model(path: str, expected_sha256: str | None = None):
    try:
        from qi.players.policy.runtime import load_checkpoint
    except ImportError as exc:
        raise GameError("learning_not_installed", "Install the learning extra: uv sync --extra learning.") from exc
    return load_checkpoint(path, expected_sha256)


def configured_model():
    path = configured_path()
    if path is None:
        raise GameError("missing_checkpoint", "Set QI_POLICY_CHECKPOINT to a trained local checkpoint.")
    return load_model(path)


def select(game: Game, config: PlayerConfig) -> Decision:
    from qi.players.bindings import binding_for

    binding = binding_for(config.kind)
    if binding is None:
        loaded = configured_model()
    else:
        loaded = load_model(binding.checkpoint, config.checkpoint_sha256)
    if config.checkpoint_sha256 is not None and config.checkpoint_sha256 != loaded.sha256:
        raise GameError("checkpoint_mismatch", "Configured policy differs from the pinned player checkpoint.")
    return Decision(loaded.predict(game), checkpoint_sha256=loaded.sha256, model_calls=1)


PLAYER = Player(
    PlayerInfo("policy", "policy-mlp-v1", "Learned policy", "Local teacher-imitation checkpoint; one CPU pass.", False),
    select,
    checkpoint=lambda: configured_model().sha256,
    available=lambda: configured_path() is not None,
)
