"""Explicit in-repository registrations; adapters discover players through this catalog."""

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from qi.players.bindings import Binding


def build_catalog(players: tuple[Player, ...]) -> Mapping[str, Player]:
    result = {}
    for player in players:
        if not player.info.id or player.info.id == "human" or player.info.id in result:
            raise ValueError("Player IDs must be nonempty, unique, and different from the human UI mode.")
        result[player.info.id] = player
    return MappingProxyType(result)


PLAYERS = build_catalog((RANDOM, ALPHABETA, QUIESCENCE, MCTS, *ENHANCED, MCTS_QUIESCENCE, POLICY, PIKAFISH))


def get_player(kind: str, *, bindings: Mapping[str, "Binding"] | None = None) -> Player:
    from qi.players.bindings import configured_bindings

    binding = (configured_bindings() if bindings is None else bindings).get(kind)
    try:
        return PLAYERS[binding.implementation if binding else kind]
    except KeyError as exc:
        raise GameError("invalid_player", f"Unknown player {kind!r}; choose from {', '.join(PLAYERS)}.") from exc


def list_players() -> list[PlayerInfo]:
    from qi.players.bindings import configured_bindings, configured_info, settings_for
    from qi.players.policy import configured_info as policy_info

    result = []
    for player in PLAYERS.values():
        if player.available is not None and not player.available():
            continue
        info = player.info
        info = replace(info, implementation_id=info.id, settings=settings_for(info))
        if info.id == "policy":
            info = policy_info(info)
        result.append(info)
    for binding in configured_bindings().values():
        result.append(configured_info(binding, PLAYERS[binding.implementation].info))
    return result
