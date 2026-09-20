"""Optional native backend in the production generation and recovery pipeline."""

import sqlite3
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from qi_game.contracts import Snapshot
from qi_game.core import START_BOARD, GameError
from qi_game.execution import ReplaySession
from qi_game.trajectory import PythonTrajectory

pytest.importorskip("qi_game_native.backend")

from qi_game_native.backend import NativeReferee, NativeTrajectory

from qi.api import create_app
from qi.teacher import TeacherSession
from qi.training_data.generation_policies import ActorPolicy
from qi.training_data.generation_runner import generate_policies
from qi.training_data.store import Collection, GamePayload, RunPayload
from qi.training_data.test_generation_runner import completed
from qi.training_data.test_generation_runner import setup as generation_setup


@pytest.fixture
def setup(tmp_path):
    return generation_setup.__wrapped__(tmp_path)


def content(store):
    games = [game.model_dump(exclude={"actor_ms"}) for game in completed(store)]
    occurrences = store.db.execute(
        "SELECT ply_count,board,turn,state_hash,input_hash,phase,json(payload) FROM position_occurrences ORDER BY id"
    ).fetchall()
    return games, [tuple(row) for row in occurrences]


def test_native_http_boundary():
    with TestClient(create_app(referee=NativeReferee())) as client:
        initial = client.post("/api/new").json()
        request = {"snapshot": initial["snapshot"], "move": "a3a4", "expected_state_hash": initial["state_hash"]}
        response = client.post("/api/apply", json=request)
        assert response.status_code == 200 and response.json()["snapshot"]["moves"] == ["a3a4"]
        request["expected_state_hash"] = "0" * 64
        assert client.post("/api/apply", json=request).json()["error"]["code"] == "stale_state"
        assert client.post("/api/inspect", json={"snapshot": initial["snapshot"]}).json() == initial


@pytest.mark.parametrize("mode", ["random", "plausible", "intervention"])
def test_native_preserves_actor_sampling_supervision_and_resume(tmp_path, setup, mode):
    config, provider, calls = setup
    config.sources[0].actor = ActorPolicy(mode=mode, intervention_min_ply=3, intervention_max_ply=3)
    config.sources[0].games = 3
    runs = []
    for factory in (None, PythonTrajectory, NativeTrajectory):
        name = factory.__name__ if factory else "default"
        with Collection(tmp_path / f"{name}.sqlite") as store:
            result = generate_policies(store, config, provider=provider, trajectory_factory=factory)
            assert result["games"] == 3
            runs.append(content(store))
            counts = store.counts()
            calls.clear()
            repeat = generate_policies(store, config, provider=provider, trajectory_factory=factory)
            assert repeat["reused_games"] == 3 and not calls and store.counts() == counts
    assert runs[0] == runs[1] == runs[2]


def test_native_closes_after_provider_failure(tmp_path, setup):
    config, _, _ = setup
    opened = []

    class Tracked(NativeTrajectory):
        def __init__(self, snapshot):
            super().__init__(snapshot)
            opened.append(self)

    def broken(*_):
        raise RuntimeError("teacher failed")

    with Collection(tmp_path / "failed.sqlite") as store:
        with pytest.raises(RuntimeError, match="teacher failed"):
            generate_policies(store, config, provider=broken, trajectory_factory=Tracked)
        assert store.db.execute("SELECT status FROM games").fetchone()[0] == "failed"
    assert len(opened) == 1
    with pytest.raises(RuntimeError, match="closed"):
        opened[0].inspect()


@pytest.mark.parametrize("mode", ["random", "plausible", "intervention"])
def test_native_consumers_do_not_reenter_python_rules(tmp_path, setup, monkeypatch, mode):
    import importlib

    import qi_game.reference as reference

    config, provider, _ = setup
    config.sources[0].actor = ActorPolicy(mode=mode, intervention_min_ply=3, intervention_max_ply=3)
    real_legal = reference.legal_moves
    calls = []

    def guarded_legal(board, turn):
        # Initial config/corpus preflight is independent of runtime selection.
        assert board == START_BOARD, "Native generation reentered Python move generation."
        return real_legal(board, turn)

    class Tracked(NativeTrajectory):
        def step(self, move, expected_hash=None):
            calls.append(move)
            return super().step(move, expected_hash)

    monkeypatch.setattr(reference, "legal_moves", guarded_legal)
    for name in (
        "qi.teacher",
        "qi.training_data.contracts",
        "qi.training_data.candidate_evidence",
        "qi.training_data.generation_policies",
        "qi.training_data.generation_runner",
    ):
        monkeypatch.setattr(importlib.import_module(name), "legal_moves", guarded_legal)
    with Collection(tmp_path / "native-only.sqlite") as store:
        result = generate_policies(store, config, provider=provider, trajectory_factory=Tracked)
        assert result["games"] == 1
        moves = completed(store)[0].snapshot.moves
        assert calls == moves  # collection, sampler and evidence reuse each validation
        assert store._execution is None


def test_cached_legality_does_not_bypass_persisted_prefix_or_failed_transaction(tmp_path):
    with Collection(tmp_path / "atomic.sqlite") as store, ReplaySession(NativeTrajectory) as execution:
        with store.executing(execution):
            run = store.run(RunPayload(config={}, provenance={}, seed=1, planned_games=1))
            game = store.begin_game(
                run,
                "one",
                GamePayload(
                    source_id="one",
                    family="one",
                    split="train",
                    mode="random",
                    actor={},
                    initial=Snapshot(),
                    snapshot=Snapshot(),
                ),
            )
            next_snapshot = Snapshot(moves=["b2e2"])
            cached = execution.inspect(next_snapshot)
            store.db.execute(
                "CREATE TRIGGER fail_append BEFORE UPDATE ON games BEGIN SELECT RAISE(ABORT, 'disk fixture'); END"
            )
            with pytest.raises(sqlite3.IntegrityError, match="disk fixture"):
                store.append(game, next_snapshot, actor_nodes=10)
            assert store.game(game).snapshot.moves == [] and store.game(game).actor_nodes == 0
            store.db.execute("DROP TRIGGER fail_append")
            store.append(game, next_snapshot, actor_nodes=10)
            assert store.game(game).actor_nodes == 10
            assert execution.inspect(next_snapshot) is cached
            with pytest.raises(ValueError, match="Prefix mutation"):
                store.append(game, Snapshot(moves=["a3a4"]))
            with pytest.raises(ValueError, match="persisted prefix"):
                store.occurrence(game, Snapshot(moves=["b2e2", "b9c7"]))
            with pytest.raises(GameError):
                store.append(game, Snapshot(moves=["b2e2", "a0a1"]))
            assert store.game(game).snapshot == next_snapshot
            occurrence = store.occurrence(game, next_snapshot)
        assert store._execution is None
    with Collection(tmp_path / "atomic.sqlite") as reopened:
        assert reopened.game(game).snapshot == next_snapshot
        assert reopened.snapshot(occurrence) == next_snapshot


def test_teacher_checks_all_view_fields_before_query(setup):
    config, _, _ = setup
    settings = config.teachers["actor"].config()
    with ReplaySession(NativeTrajectory) as execution:
        view = execution.inspect(Snapshot(moves=["b2e2"]))
        for forged in [replace(view, board=START_BOARD), replace(view, legal_moves=("bad",))]:
            with TeacherSession(settings, execution=execution) as session:
                with pytest.raises(GameError) as error:
                    session.analyze(forged, settings)
                assert error.value.code == "invalid_state" and session.engine is None
