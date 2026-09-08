"""Explicit in-repository registrations; adapters discover players through this catalog."""

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

from qi.game import GameError
from qi.players.alphabeta import PLAYER as ALPHABETA
from qi.players.core import Player, PlayerInfo
from qi.players.mcts import PLAYER as MCTS
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


PLAYERS = build_catalog((RANDOM, ALPHABETA, QUIESCENCE, MCTS, POLICY))


def get_player(kind: str) -> Player:
    try:
        return PLAYERS[kind]
    except KeyError as exc:
        raise GameError("invalid_player", f"Unknown player {kind!r}; choose from {', '.join(PLAYERS)}.") from exc


def list_players() -> list[PlayerInfo]:
    result = []
    for player in PLAYERS.values():
        if player.available is not None and not player.available():
            continue
        info = player.info
        if player.checkpoint is not None:
            info = replace(info, checkpoint_sha256=player.checkpoint())
        result.append(info)
    return result
