"""Checkpoint-backed policy registration; importing the catalog never imports torch."""

import os
from pathlib import Path
from typing import TYPE_CHECKING

from qi.game import Game, GameError
from qi.players.core import Decision, Player, PlayerConfig, PlayerInfo

if TYPE_CHECKING:
    from qi.players.bindings import ResolvedBinding

_pinned_checkpoints: dict[str, str] = {}


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
    loaded = load_model(path)
    _pinned_checkpoints[path] = loaded.sha256
    return loaded


def configured_info(info: PlayerInfo) -> PlayerInfo:
    """Advertise the loaded identity without importing the optional model runtime."""
    from dataclasses import replace

    from qi.players.bindings import file_identity

    path = configured_path()
    if path is None:
        return replace(
            info, available=False, unavailable_reason="Set QI_POLICY_CHECKPOINT to a trained local checkpoint."
        )
    pinned = _pinned_checkpoints.get(path)
    try:
        current = file_identity(path, maximum=16 * 1024 * 1024)
        if pinned is not None and current != pinned:
            return replace(
                info,
                checkpoint_sha256=pinned,
                available=False,
                unavailable_reason="Checkpoint changed after loading. Restart the server to use its new contents.",
            )
        return replace(info, checkpoint_sha256=pinned or current)
    except GameError as exc:
        reason = str(exc)
        if pinned is not None:
            reason += " The process still has the pinned checkpoint; restore its file or restart the server."
        return replace(info, checkpoint_sha256=pinned, available=False, unavailable_reason=reason)


def select(game: Game, config: PlayerConfig) -> Decision:
    loaded = configured_model()
    if config.checkpoint_sha256 is not None and config.checkpoint_sha256 != loaded.sha256:
        raise GameError("checkpoint_mismatch", "Configured policy differs from the pinned player checkpoint.")
    return Decision(loaded.predict(game), checkpoint_sha256=loaded.sha256, model_calls=1)


def select_bound(game: Game, config: PlayerConfig, resource: "ResolvedBinding") -> Decision:
    loaded = load_model(resource.binding.checkpoint, config.checkpoint_sha256)
    return Decision(loaded.predict(game), checkpoint_sha256=loaded.sha256, model_calls=1)


PLAYER = Player(
    PlayerInfo("policy", "policy-mlp-v1", "Learned policy", "Local teacher-imitation checkpoint; one CPU pass.", False),
    select,
    checkpoint=lambda: configured_model().sha256,
    available=lambda: configured_path() is not None,
    select_bound=select_bound,
)
