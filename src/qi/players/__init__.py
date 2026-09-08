"""Public player boundary: select by catalog ID, validate, and attach provenance."""

from dataclasses import replace
from math import isfinite
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
    if (stats := decision.mcts) is not None:
        roots = stats.root_moves
        valid = (
            stats.tree_visits + stats.rollout_steps + stats.leaf_nodes == decision.nodes
            and stats.leaf_nodes >= 0
            and 0 <= stats.leaf_aborts <= stats.unfinished_simulations
            and stats.simulations == stats.terminal_simulations + stats.rollout_cutoffs + stats.budget_cutoffs
            and stats.simulations == sum(move.visits for move in roots)
            and stats.tree_visits >= 2 * stats.simulations + stats.unfinished_simulations
            and stats.unfinished_simulations in (0, 1)
            and 0 <= stats.max_tree_depth <= stats.tree_visits
            and all(
                count >= 0
                for count in (
                    stats.rollout_steps,
                    stats.terminal_simulations,
                    stats.rollout_cutoffs,
                    stats.budget_cutoffs,
                    stats.simulations,
                )
            )
            and len(roots) == len({move.move for move in roots})
            and {move.move for move in roots} == set(legal_moves(game.board, game.turn))
            and all(
                move.visits >= 0
                and (
                    move.mean_value is None
                    if move.visits == 0
                    else move.mean_value is not None and isfinite(move.mean_value) and -1 <= move.mean_value <= 1
                )
                for move in roots
            )
        )
        if not valid:
            raise GameError("invalid_player_result", "Player returned inconsistent MCTS diagnostics.")
    if (stats := decision.search_stats) is not None and not (
        0 <= stats.see_nodes <= decision.nodes - decision.qnodes
        and 0 <= stats.max_extensions <= 4
        and 0 <= stats.extensions <= decision.nodes
        and 0 <= stats.tt_cutoffs <= stats.tt_hits <= decision.nodes
        and 0 <= stats.cutoffs <= decision.nodes
    ):
        raise GameError("invalid_player_result", "Player returned inconsistent search diagnostics.")
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
