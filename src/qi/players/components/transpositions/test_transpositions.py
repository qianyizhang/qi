"""Bounds, mate distances, and repetition context cannot be silently conflated."""

from dataclasses import replace

from qi.game import Game, replay
from qi.players.common import MATE
from qi.players.components.transpositions import Entry, TranspositionTable, mate_from_table, mate_to_table, position_key


def test_board_alone_is_not_a_cache_identity():
    game = replay(("b0c2", "b9c7", "c2b0", "c7b9"))
    different_history = replace(game, positions=(game.board + game.turn,))
    assert game.board == different_history.board and len(game.moves) == len(different_history.moves)
    assert position_key(game) != position_key(different_history)
    assert position_key(game) != position_key(replace(game, moves=(*game.moves, "b2e2")))
    assert position_key(game) == position_key(replace(game, positions=tuple(reversed(game.positions))))


def test_bounds_only_cut_off_compatible_windows_and_exact_horizons():
    lower = Entry(2, 1, 50, "lower", "b2e2")
    assert lower.cutoff(2, 1, -100, 40, 0) == 50
    assert lower.cutoff(2, 1, -100, 60, 0) is None
    assert lower.cutoff(1, 1, -100, 40, 0) is None
    assert lower.cutoff(2, 0, -100, 40, 0) is None
    assert Entry(2, 1, -50, "upper", None).cutoff(2, 1, -40, 100, 0) == -50


def test_mate_distance_is_relative_to_the_probed_path():
    assert mate_from_table(mate_to_table(MATE - 9, 4), 2) == MATE - 7
    assert mate_from_table(mate_to_table(-MATE + 9, 4), 2) == -MATE + 7
    assert mate_from_table(mate_to_table(900, 4), 2) == 900


def test_capacity_and_context_misses():
    table = TranspositionTable(1)
    entry = Entry(1, 0, 0, "exact", "b2e2")
    table.store(Game(), entry)
    assert table.probe(Game()) == entry
    child = Game().apply("b2e2")
    table.store(child, entry)
    assert table.probe(Game()) is None and table.probe(child) == entry
    assert len(table.entries) == 1
