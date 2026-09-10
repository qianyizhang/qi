"""Public player boundary: select by catalog ID, validate, and attach provenance."""

from dataclasses import replace
from time import perf_counter

from qi.game import Game, GameError
from qi.players.catalog import get_player, list_players
from qi.players.core import Choice, Decision, Player, PlayerConfig, PlayerInfo
from qi.players.validation import validate_decision

__all__ = ["Choice", "Decision", "Player", "PlayerConfig", "PlayerInfo", "bind_config", "choose", "list_players"]


def bind_config(config: PlayerConfig) -> PlayerConfig:
    """Pin the configured checkpoint before an arena batch starts."""
    player = get_player(config.kind)
    if player.checkpoint is not None:
        digest = player.checkpoint()
        if config.checkpoint_sha256 is not None and config.checkpoint_sha256 != digest:
            raise GameError("checkpoint_mismatch", "Configured policy differs from the pinned player checkpoint.")
        return replace(config, checkpoint_sha256=digest)
    if config.checkpoint_sha256 is not None:
        raise GameError("invalid_player", "This player does not use a checkpoint.")
    return config


def choose(game: Game, config: PlayerConfig) -> Choice:
    player = get_player(config.kind)
    if game.outcome:
        raise GameError("game_over", "Cannot select a move after the game ends.")
    config = bind_config(config)
    started = perf_counter()
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
    )
