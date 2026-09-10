"""Server-configured resource bindings, independent of algorithm registration."""

import os
from dataclasses import dataclass, replace
from hashlib import sha256
from math import isclose
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qi.artifacts import digest
from qi.game import GameError
from qi.players.core import PlayerConfig, PlayerInfo, Setting


class Binding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    label: str = Field(min_length=1, max_length=100)
    implementation: str
    checkpoint: str | None = None
    engine: str | None = None
    network: str | None = None
    threads: int = Field(default=1, ge=1, le=16)
    hash_mb: int = Field(default=16, ge=1, le=1024)

    @model_validator(mode="after")
    def valid_resources(self):
        if self.implementation == "policy":
            if not self.checkpoint or self.engine or self.network:
                raise ValueError("A policy binding requires only a checkpoint.")
        elif self.implementation == "pikafish":
            if not self.engine or not self.network or self.checkpoint:
                raise ValueError("Pikafish requires engine and network resources.")
        elif self.checkpoint or self.engine or self.network:
            raise ValueError("This implementation does not accept model/engine resources.")
        return self


class BindingsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = Field(default=1, ge=1, le=1)
    players: list[Binding] = Field(max_length=64)


def configured_bindings() -> dict[str, Binding]:
    configured = os.environ.get("QI_PLAYERS_CONFIG")
    if not configured:
        return {}
    from qi.players.catalog import PLAYERS

    try:
        path = Path(configured).resolve()
        if path.stat().st_size > 64 * 1024:
            raise ValueError("Player configuration exceeds 64 KiB.")
        entries = BindingsFile.model_validate_json(path.read_text()).players
        result = {}
        for entry in entries:
            if entry.id in result or entry.id in PLAYERS or entry.id == "human":
                raise ValueError("Binding IDs must be unique and different from implementation IDs and human.")
            if entry.implementation not in PLAYERS:
                raise ValueError(f"Unknown implementation: {entry.implementation}")
            paths = {
                key: str((path.parent / value).resolve())
                for key in ("checkpoint", "engine", "network")
                if (value := getattr(entry, key)) is not None
            }
            result[entry.id] = entry.model_copy(update=paths)
        return result
    except (ValueError, OSError) as exc:
        raise GameError("invalid_bindings", f"Cannot read player configuration: {exc}") from exc


def binding_for(kind: str) -> Binding | None:
    return configured_bindings().get(kind)


def implementation_id(kind: str) -> str:
    binding = binding_for(kind)
    return binding.implementation if binding else kind


def file_identity(path: str, *, maximum: int = 512 * 1024 * 1024) -> str:
    resource = Path(path)
    try:
        if not resource.is_file() or resource.stat().st_size > maximum:
            raise ValueError("Resource is missing or exceeds its size limit.")
        fingerprint = sha256()
        with resource.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                fingerprint.update(chunk)
        return fingerprint.hexdigest()
    except (OSError, ValueError) as exc:
        raise GameError("unavailable_player", f"Cannot read configured resource: {resource.name}: {exc}") from exc


@dataclass(frozen=True)
class ResolvedBinding:
    binding: Binding
    sha256: str
    checkpoint_sha256: str | None
    engine_sha256: str | None
    network_sha256: str | None


def resolve(binding: Binding) -> ResolvedBinding:
    checkpoint = file_identity(binding.checkpoint, maximum=16 * 1024 * 1024) if binding.checkpoint else None
    engine = file_identity(binding.engine) if binding.engine else None
    network = file_identity(binding.network) if binding.network else None
    identity = digest(
        {
            "implementation": binding.implementation,
            "checkpoint": checkpoint,
            "engine": engine,
            "network": network,
            "threads": binding.threads,
            "hash_mb": binding.hash_mb,
        }
    )
    return ResolvedBinding(binding, identity, checkpoint, engine, network)


def pin(config: PlayerConfig) -> PlayerConfig:
    binding = binding_for(config.kind)
    if binding is None:
        if config.binding_sha256 is not None:
            raise GameError("binding_mismatch", "The saved player binding is no longer configured.")
        return config
    resolved = resolve(binding)
    if config.binding_sha256 is not None and config.binding_sha256 != resolved.sha256:
        raise GameError("binding_mismatch", "Configured resources differ from the pinned player binding.")
    if config.checkpoint_sha256 is not None and config.checkpoint_sha256 != resolved.checkpoint_sha256:
        raise GameError("checkpoint_mismatch", "Configured policy differs from the pinned checkpoint.")
    return replace(
        config,
        binding_sha256=resolved.sha256,
        checkpoint_sha256=resolved.checkpoint_sha256,
        work_semantics="engine_native" if binding.implementation == "pikafish" else "qi",
    )


def settings_for(info: PlayerInfo) -> dict[str, Setting]:
    kind = info.implementation_id or info.id
    if kind == "policy":
        return {}
    settings = {}
    if kind == "random" or info.default_rollout_plies is not None:
        settings["seed"] = Setting("Seed", 0, 0, 2_147_483_000)
    if info.uses_search:
        settings["nodes"] = Setting(
            "Node limit" if kind == "pikafish" else "Visit budget",
            info.default_nodes,
            1,
            1_000_000 if kind == "pikafish" else 100_000,
            unit="native nodes" if kind == "pikafish" else "qi visits",
        )
        if info.default_rollout_plies is not None:
            settings["rollout_plies"] = Setting("Rollout length", info.default_rollout_plies, 0, 64, unit="plies")
        else:
            settings["depth"] = Setting("Depth limit", info.default_depth, 1, 8, unit="plies")
    if kind == "pikafish":
        settings["timeout_seconds"] = Setting("Move timeout", 10, 0.1, 120, 0.1, "seconds")
    return settings


def configured_info(binding: Binding, info: PlayerInfo) -> PlayerInfo:
    info = replace(info, id=binding.id, label=binding.label, implementation_id=binding.implementation)
    try:
        resource = resolve(binding)
        return replace(
            info,
            binding_sha256=resource.sha256,
            checkpoint_sha256=resource.checkpoint_sha256,
            settings=settings_for(info),
        )
    except GameError as exc:
        return replace(info, available=False, unavailable_reason=str(exc), settings=settings_for(info))


def selection_config(
    player: str, settings: dict[str, float], expected_binding: str | None, expected_checkpoint: str | None = None
) -> PlayerConfig:
    from qi.players import list_players

    info = next((entry for entry in list_players() if entry.id == player), None)
    if info is None or not info.available:
        raise GameError("unavailable_player", info.unavailable_reason if info else "Player is not available.")
    if set(settings) - info.settings.keys():
        raise GameError("invalid_settings", "A submitted setting is not supported by this player.")
    values = {key: spec.default for key, spec in info.settings.items()}
    for key, value in settings.items():
        spec = info.settings[key]
        if (
            isinstance(value, bool)
            or not spec.minimum <= value <= spec.maximum
            or not isclose(
                (value - spec.minimum) / spec.step, round((value - spec.minimum) / spec.step), abs_tol=1e-8, rel_tol=0
            )
        ):
            raise GameError("invalid_settings", f"{spec.label} must be between {spec.minimum} and {spec.maximum}.")
        values[key] = value
    config = PlayerConfig(
        player,
        seed=int(values.get("seed", 0)),
        depth=int(values.get("depth", 2)),
        nodes=int(values.get("nodes", 128)),
        rollout_plies=int(values.get("rollout_plies", 8)),
        binding_sha256=expected_binding,
        checkpoint_sha256=expected_checkpoint,
        timeout_seconds=values.get("timeout_seconds", 10),
    )
    if expected_checkpoint != info.checkpoint_sha256:
        raise GameError("checkpoint_mismatch", "Select the current checkpoint identity explicitly.")
    if expected_binding != info.binding_sha256:
        raise GameError("binding_mismatch", "Select the current binding explicitly before playing.")
    return config
