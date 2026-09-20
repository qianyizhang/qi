"""Public player boundary: select by catalog ID, validate, and attach provenance."""

from time import perf_counter

from qi_game.core import GameError
from qi_game.reference import Game

from qi.players.bindings import ResolvedPlayer, resolve_player, resolve_selection
from qi.players.catalog import list_players
from qi.players.core import Choice, Decision, Player, PlayerConfig, PlayerInfo
from qi.players.validation import validate_decision

__all__ = [
    "Choice",
    "Decision",
    "Player",
    "PlayerConfig",
    "PlayerInfo",
    "ResolvedPlayer",
    "bind_config",
    "choose",
    "list_players",
    "resolve_selection",
]


def bind_config(config: PlayerConfig) -> PlayerConfig:
    """Pin participant identities; each later decision verifies its own resources."""
    return resolve_player(config).config


def choose(game: Game, config: PlayerConfig | ResolvedPlayer) -> Choice:
    if game.outcome:
        raise GameError("game_over", "Cannot select a move after the game ends.")
    resolved = config if isinstance(config, ResolvedPlayer) else resolve_player(config)
    player, config = resolved.player, resolved.config
    started = perf_counter()
    if resolved.resource is not None and player.select_bound is not None:
        decision = player.select_bound(game, config, resolved.resource)
    else:
        assert player.select is not None
        decision = player.select(game, config)
    try:
        validate_decision(decision, config, game)
    except ValueError as exc:
        raise GameError("invalid_player_result", str(exc)) from exc
    if decision.checkpoint_sha256 != config.checkpoint_sha256:
        raise GameError("invalid_player_result", "Player checkpoint differs from the pinned configuration.")
    return Choice(
        decision.move,
        game.state_hash,
        player.info.version,
        config.seed,
        decision.nodes,
        decision.completed_depth,
        decision.score,
        (perf_counter() - started) * 1000,
        decision.qnodes,
        decision.max_qply,
        decision.checkpoint_sha256,
        decision.model_calls,
        decision.mcts,
        decision.search_stats,
        decision.evaluation,
        decision.engine,
        config.binding_sha256,
    )
