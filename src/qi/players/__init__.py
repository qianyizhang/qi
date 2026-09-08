"""Public player boundary: select by catalog ID, validate, and attach provenance."""

from dataclasses import replace
from time import perf_counter

from qi.game import Game, GameError, legal_moves
from qi.players.catalog import get_player, list_players
from qi.players.core import Choice, Decision, Player, PlayerConfig, PlayerInfo

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
    if decision.move not in legal_moves(game.board, game.turn):
        raise GameError("invalid_player_result", "Player returned a move rejected by the referee.")
    if not (
        0 <= decision.qnodes <= decision.nodes <= config.nodes
        and 0 <= decision.completed_depth <= config.depth
        and 0 <= decision.max_qply <= decision.qnodes
        and decision.model_calls in (0, 1)
        and decision.checkpoint_sha256 == config.checkpoint_sha256
    ):
        raise GameError("invalid_player_result", "Player returned diagnostics outside its budget.")
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
    )
