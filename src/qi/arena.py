"""Reproducible baseline matches, always adjudicated by the game referee."""

from dataclasses import dataclass, replace
from importlib.metadata import version
from platform import platform, python_version

from qi.game import Game, GameError, Side
from qi.players import Choice, PlayerConfig, bind_config, choose
from qi.protocol import Snapshot


@dataclass(frozen=True)
class TurnRecord:
    ply: int
    side: Side
    choice: Choice


@dataclass(frozen=True)
class MatchRecord:
    schema_version: int
    qi_version: str
    python_version: str
    platform: str
    red: PlayerConfig
    black: PlayerConfig
    opening: Snapshot
    snapshot: Snapshot
    winner: Side | None
    reason: str
    turns: tuple[TurnRecord, ...]


def play_match(red: PlayerConfig, black: PlayerConfig, opening: Game | None = None) -> MatchRecord:
    game = opening if opening is not None else Game()
    initial = Snapshot(moves=list(game.moves))
    if initial.game() != game:
        raise GameError("invalid_opening", "Opening must replay from the standard initial position.")
    if game.outcome:
        raise GameError("game_over", "The opening is already terminal.")
    red, black = bind_config(red), bind_config(black)
    turns = []
    while (outcome := game.outcome) is None:
        config = red if game.turn == "red" else black
        # Seed each decision independently so resuming at a saved ply is reproducible.
        choice = choose(game, replace(config, seed=config.seed + len(game.moves)))
        turns.append(TurnRecord(len(game.moves) + 1, game.turn, choice))
        game = game.apply(choice.move, choice.state_hash)
    return MatchRecord(
        2 if red.binding_sha256 or black.binding_sha256 else 1,
        version("qi"),
        python_version(),
        platform(),
        red,
        black,
        initial,
        Snapshot(moves=list(game.moves)),
        outcome.winner,
        outcome.reason,
        tuple(turns),
    )
