"""Optional native backend in the production generation and recovery pipeline."""

import pytest
from fastapi.testclient import TestClient
from qi_game.trajectory import PythonTrajectory

pytest.importorskip("qi_game_native.backend")

from qi_game_native.backend import NativeReferee, NativeTrajectory

from qi.api import create_app
from qi.training_data.generation_policies import ActorPolicy
from qi.training_data.generation_runner import generate_policies
from qi.training_data.store import Collection
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
