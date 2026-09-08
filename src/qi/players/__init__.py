"""Public player boundary: select by catalog ID, validate, and attach provenance."""

from time import perf_counter

from qi.game import Game, GameError, legal_moves
from qi.players.catalog import get_player, list_players
from qi.players.core import Choice, Decision, Player, PlayerConfig, PlayerInfo

__all__ = ["Choice", "Decision", "Player", "PlayerConfig", "PlayerInfo", "choose", "list_players"]


def choose(game: Game, config: PlayerConfig) -> Choice:
    player = get_player(config.kind)
    if game.outcome:
        raise GameError("game_over", "Cannot select a move after the game ends.")
    started = perf_counter()
    decision = player.select(game, config)
    if decision.move not in legal_moves(game.board, game.turn):
        raise GameError("invalid_player_result", "Player returned a move rejected by the referee.")
    if not (
        0 <= decision.qnodes <= decision.nodes <= config.nodes
        and 0 <= decision.completed_depth <= config.depth
        and 0 <= decision.max_qply <= decision.qnodes
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
    )
