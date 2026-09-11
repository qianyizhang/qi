"""Explicit external-engine participant; importing its descriptor launches nothing."""

from qi.game import Game, GameError
from qi.players.core import Decision, EngineScore, EngineWork, Player, PlayerConfig, PlayerInfo


def select(game: Game, config: PlayerConfig) -> Decision:
    from qi.players.bindings import binding_for, resolve
    from qi.teacher import TeacherConfig, TeacherIdentity, TeacherSession

    binding = binding_for(config.kind)
    if binding is None or binding.implementation != "pikafish":
        raise GameError("missing_binding", "Select a configured Pikafish player binding.")
    resource = resolve(binding)
    if resource.sha256 != config.binding_sha256:
        raise GameError("binding_mismatch", "Engine resources changed after selection.")
    from pathlib import Path

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
    select,
    available=lambda: False,
)
