"""Explicit optional study checks; installed production dependencies stay unchanged."""

import json
import sys

import pytest
import study
from fastapi.testclient import TestClient

from qi.api import create_app


@pytest.fixture
def candidate(arm, monkeypatch):
    monkeypatch.syspath_prepend(str(study.ARTIFACTS / "deps"))
    if arm == "import":
        pytest.importorskip("pyffish")
    elif sys.platform != "darwin" or not (study.ARTIFACTS / "minimal.dylib").exists():
        pytest.skip("Build the macOS native study first")
    return arm


@pytest.mark.parametrize("arm", ["import", "minimal-scalar"])
def test_real_http_consumer_accepts_candidate_and_preserves_errors(candidate):
    with TestClient(create_app(referee=study.RefereeAdapter(candidate))) as client:
        initial = client.post("/api/new").json()
        request = {"snapshot": initial["snapshot"], "move": "a3a4", "expected_state_hash": initial["state_hash"]}
        response = client.post("/api/apply", json=request)
        assert response.status_code == 200
        assert response.json()["snapshot"]["moves"] == ["a3a4"]
        request["expected_state_hash"] = "0" * 64
        assert client.post("/api/apply", json=request).json()["error"]["code"] == "stale_state"
        assert client.post("/api/inspect", json={"snapshot": initial["snapshot"]}).json() == initial
        broken = {"snapshot": {**initial["snapshot"], "moves": ["a3a4", "a3a4"]}}
        assert client.post("/api/inspect", json=broken).json()["error"]["code"] == "illegal_move"


@pytest.mark.parametrize("arm", ["import", "minimal-scalar"])
def test_scalar_state_rejection_is_atomic_after_moves(candidate):
    state = study.FACTORIES[candidate]()
    try:
        for move in ["a3a4", "a6a5", "a4a5"]:
            state.apply(move)
        before = state.position().model_dump()
        with pytest.raises(study.GameError):
            state.apply("a5a6")
        assert state.position().model_dump() == before
    finally:
        state.close()


def test_evidence_writer_rejects_overwrite(tmp_path):
    target = tmp_path / "result.json"
    study.write_new(target, {"original": True})
    with pytest.raises(FileExistsError):
        study.write_new(target, {"original": False})
    assert json.loads(target.read_text()) == {"original": True}
