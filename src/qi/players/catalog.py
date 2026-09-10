"""Explicit in-repository registrations; adapters discover players through this catalog."""

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

from qi.game import GameError
from qi.players.alphabeta import PLAYER as ALPHABETA
from qi.players.core import Player, PlayerInfo
from qi.players.enhanced import PLAYERS as ENHANCED
from qi.players.mcts import PLAYER as MCTS
from qi.players.mcts_quiescence import PLAYER as MCTS_QUIESCENCE
from qi.players.pikafish import PLAYER as PIKAFISH
from qi.players.policy import PLAYER as POLICY
from qi.players.quiescence import PLAYER as QUIESCENCE
from qi.players.random import PLAYER as RANDOM


def build_catalog(players: tuple[Player, ...]) -> Mapping[str, Player]:
    result = {}
    for player in players:
        if not player.info.id or player.info.id == "human" or player.info.id in result:
            raise ValueError("Player IDs must be nonempty, unique, and different from the human UI mode.")
        result[player.info.id] = player
    return MappingProxyType(result)


PLAYERS = build_catalog((RANDOM, ALPHABETA, QUIESCENCE, MCTS, *ENHANCED, MCTS_QUIESCENCE, POLICY, PIKAFISH))


def get_player(kind: str) -> Player:
    from qi.players.bindings import implementation_id

    try:
        return PLAYERS[implementation_id(kind)]
    except KeyError as exc:
        raise GameError("invalid_player", f"Unknown player {kind!r}; choose from {', '.join(PLAYERS)}.") from exc


def list_players() -> list[PlayerInfo]:
    from qi.players.bindings import configured_bindings, configured_info, file_identity, settings_for
    from qi.players.policy import configured_path

    result = []
    for player in PLAYERS.values():
        if player.available is not None and not player.available():
            continue
        info = player.info
        info = replace(info, implementation_id=info.id, settings=settings_for(info))
        if info.id == "policy":
            try:
                info = replace(info, checkpoint_sha256=file_identity(configured_path(), maximum=16 * 1024 * 1024))
            except GameError as exc:
                info = replace(info, available=False, unavailable_reason=str(exc))
        result.append(info)
    for binding in configured_bindings().values():
        result.append(configured_info(binding, PLAYERS[binding.implementation].info))
    return result
