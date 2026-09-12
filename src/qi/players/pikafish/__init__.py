"""Explicit external-engine participant; importing its descriptor launches nothing."""

from pathlib import Path
from typing import TYPE_CHECKING

from qi.game import Game
from qi.players.core import Decision, EngineScore, EngineWork, Player, PlayerConfig, PlayerInfo

if TYPE_CHECKING:
    from qi.players.bindings import ResolvedBinding


def select(game: Game, config: PlayerConfig, resource: "ResolvedBinding") -> Decision:
    from qi.teacher import TeacherConfig, TeacherIdentity, TeacherSession

    binding = resource.binding
    engine, network = Path(binding.engine), Path(binding.network)
    settings = TeacherConfig(
        engine, network, config.nodes, config.depth, config.timeout_seconds, threads=binding.threads
    )
    identity = TeacherIdentity(engine, network, resource.engine_sha256, resource.network_sha256)
    with TeacherSession(settings, identity=identity) as session:
        session.settings.update(Hash=str(binding.hash_mb))
        analysis = session.analyze(game, settings)
    native = EngineWork(
        analysis.engine_name,
        analysis.engine_sha256,
        analysis.network_sha256,
        config.nodes,
        config.depth,
        config.timeout_seconds,
        analysis.reported_nodes,
        analysis.reported_depth,
        EngineScore(analysis.score.kind, analysis.score.value, analysis.score.bound) if analysis.score else None,
        binding.threads,
        binding.hash_mb,
    )
    return Decision(analysis.move, engine=native)


PLAYER = Player(
    PlayerInfo(
        "pikafish",
        "pikafish-uci-v1",
        "Pikafish",
        "Configured local UCI engine; qi adjudicates every move.",
        True,
        default_nodes=10000,
        default_depth=6,
    ),
    None,
    available=lambda: False,
    select_bound=select,
)
