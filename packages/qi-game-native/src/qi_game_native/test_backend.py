"""Differential rules, ownership, and batch failure conformance."""

import json
from dataclasses import FrozenInstanceError
from importlib.resources import files
from random import Random

import pytest
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import Game, inspect
from qi_game.trajectory import PythonTrajectory

from qi_game_native.backend import NativeReferee, NativeTrajectory, step_many


def test_frozen_replays():
    fixture = json.loads((files("qi_game") / "fixtures/referee-v1.json").read_text())
    for case in fixture["replays"]:
        snapshot = Snapshot.model_validate(case["position"]["snapshot"])
        native, reference = NativeTrajectory(snapshot), PythonTrajectory(snapshot)
        assert native.inspect() == reference.inspect()
        assert native.inspect().to_position().model_dump() == case["position"]
        native.close()
        reference.close()


@pytest.mark.parametrize("width", [1, 8, 32, 128])
def test_batches_match_complete_reference_games(width):
    # Each game owns its RNG; grouping never changes trajectory identity.
    games = [NativeTrajectory(Snapshot()) for _ in range(width)]
    reference = [Game() for _ in games]
    rngs = [Random(700 + i) for i in range(width)]
    for _ in range(300):
        active, moves, indices = [], [], []
        for i, (native, expected, rng) in enumerate(zip(games, reference, rngs, strict=True)):
            position = native.inspect()
            assert position.to_position() == inspect(expected)
            if position.outcome:
                continue
            move = rng.choice(sorted(position.legal_moves))
            active.append(native)
            moves.append(move)
            indices.append(i)
            reference[i] = expected.apply(move)
        if not active:
            break
        results = [active[0].step(moves[0])] if width == 1 else step_many(active, moves)
        for i, position in zip(indices, results, strict=True):
            assert position.to_position() == inspect(reference[i])
    assert all(game.inspect().outcome is not None for game in games)
    for game in games:
        game.close()


def test_guards_errors_and_atomic_batch():
    games = [NativeTrajectory(Snapshot()), NativeTrajectory(Snapshot())]
    initial = [game.inspect() for game in games]
    for move, code in [
        ("bad", "invalid_move"),
        ("a9a8", "wrong_player"),
        ("a0a9", "illegal_move"),
        ("a0a1\0", "invalid_move"),
        ("🐈", "invalid_move"),
    ]:
        with pytest.raises(GameError) as error:
            step_many(games, ["b2e2", move])
        assert error.value.code == code
        assert [game.inspect() for game in games] == initial
        with pytest.raises(GameError) as error:
            games[1].step(move)
        assert error.value.code == code
        assert games[1].inspect() is initial[1]
    with pytest.raises(GameError) as error:
        step_many(games, ["bad", "bad"], [None, "stale"])
    assert error.value.code == "stale_state"
    with pytest.raises(ValueError):
        step_many([games[0], games[0]], ["b2e2", "b2e2"])
    with pytest.raises(ValueError):
        step_many(games, ["b2e2"])
    assert [game.inspect() for game in games] == initial
    # A successful follow-up checks actual native state, not just cached views.
    for move, position in zip(
        ["b2e2", "a3a4"], step_many(games, ["b2e2", "a3a4"], [p.state_hash for p in initial]), strict=True
    ):
        assert position.to_position() == inspect(Game().apply(move))
    for game in games:
        game.close()
        game.close()
        with pytest.raises(RuntimeError, match="closed"):
            game.step("b2e2")


def test_restoration_rejects_invalid_full_history_and_isolates_results():
    for factory in [NativeTrajectory, PythonTrajectory]:
        with pytest.raises(GameError) as error:
            factory(Snapshot(moves=["b2e2", "a0a1"]))
        assert error.value.code == "wrong_player"
    snapshot = Snapshot(moves=["b2e2"])
    referee = NativeReferee()
    result = referee.inspect(snapshot)
    result.snapshot.moves.clear()
    result.legal_moves.clear()
    assert referee.inspect(snapshot) == PythonTrajectory(snapshot).inspect().to_position()
    assert snapshot.moves == ["b2e2"]
    with pytest.raises(GameError) as error:
        referee.apply(snapshot, "bad", "stale")
    assert error.value.code == "stale_state"


def test_repetition_and_post_terminal_failure():
    moves = ["b0c2", "b9c7", "c2b0", "c7b9"] * 2
    game = NativeTrajectory(Snapshot(moves=moves))
    before = game.inspect()
    assert before.outcome.reason == "repetition" and not before.legal_moves
    with pytest.raises(GameError) as error:
        game.step("bad")
    assert error.value.code == "game_over"
    assert game.inspect() == before


def test_compact_scalar_views_and_metadata_commit(monkeypatch):
    from qi_game_native import backend

    game = NativeTrajectory(Snapshot(moves=["b2e2"]))
    before = game.inspect()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Scalar execution rebuilt a wire contract or used the batch path.")

    monkeypatch.setattr(backend, "Position", forbidden)
    monkeypatch.setattr(backend, "Snapshot", forbidden)
    monkeypatch.setattr(backend._native, "step_many", forbidden)
    assert game.inspect() is before
    with pytest.raises(GameError) as error:
        game.step("bad", "stale")
    assert error.value.code == "stale_state"
    with pytest.raises(TypeError):
        game.step(123)
    assert game.inspect() is before
    result = game.step("b9c7", before.state_hash)
    expected = Game().apply("b2e2").apply("b9c7")
    assert result.state_hash == expected.state_hash
    assert result.moves == expected.moves and before.moves == ("b2e2",)
    assert game.inspect() is result
    with pytest.raises(FrozenInstanceError):
        result.state_hash = "forged"
    with pytest.raises(TypeError):
        result.legal_moves[0] = "bad"


def test_batch_preparation_failure_never_advances_native_state(monkeypatch):
    games = [NativeTrajectory(Snapshot()), NativeTrajectory(Snapshot())]
    prepare = games[1]._prepare

    def exhausted(_move):
        raise MemoryError("metadata allocation fixture")

    monkeypatch.setattr(games[1], "_prepare", exhausted)
    with pytest.raises(MemoryError, match="metadata allocation"):
        step_many(games, ["b2e2", "a3a4"])
    monkeypatch.setattr(games[1], "_prepare", prepare)
    for move, position in zip(["b2e2", "a3a4"], step_many(games, ["b2e2", "a3a4"]), strict=True):
        assert position.to_position() == inspect(Game().apply(move))
