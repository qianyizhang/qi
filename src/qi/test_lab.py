"""Local lab contracts: isolated readers, session evidence and owned trace jobs."""

import json
import subprocess
import sys
from dataclasses import asdict
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import restore

from qi.api import create_app
from qi.experiments.inspect import inspect_decision
from qi.experiments.presentation import read_bundle
from qi.experiments.report import render_export
from qi.experiments.runner import run
from qi.experiments.test_experiments import plan
from qi.lab import TraceJobs, TraceRequest, discover
from qi.players import PlayerConfig, bind_config, choose, list_players, resolve_selection
from qi.protocol import ConfigurationChange, Controller, Controllers, GameSession, SessionMove


@pytest.fixture
def lab_run(tmp_path, monkeypatch):
    monkeypatch.setenv("QI_EXPERIMENT_ROOTS", str(tmp_path / "experiments"))
    monkeypatch.setenv("QI_LAB_STATE", str(tmp_path / "jobs"))
    directory = tmp_path / "experiments" / "run"
    run(plan(), directory)
    return directory


def trace_request(directory):
    bundle = read_bundle(directory)
    return TraceRequest(
        run_id=next(iter(discover())),
        unit_id=bundle.units[0].job.id,
        unit_sha256=bundle.units[0].sha256,
        turn_index=0,
        request_id=uuid4().hex,
    )


def await_job(jobs, timeout=10):
    end = monotonic() + timeout
    while monotonic() < end:
        job = jobs.list()[0]
        if job.status != "running" and jobs.process is None:
            return job
        sleep(0.02)
    pytest.fail("Trace job did not finish within the test deadline.")


def test_presentation_is_pure_and_narrative_identity_is_separate(lab_run, monkeypatch):
    before = read_bundle(lab_run)
    (lab_run / "narrative.md").write_text("# Observation\n\n[Unit](units/unit-00000.json)\n\n<script>alert(1)</script>")
    monkeypatch.setattr("qi.players.choose", lambda *_: pytest.fail("Player executed by reader"))
    monkeypatch.setitem(
        sys.modules,
        "qi.players.policy.runtime",
        SimpleNamespace(load_checkpoint=lambda *_: pytest.fail("Model loaded by reader")),
    )
    after = read_bundle(lab_run)
    assert before.data.summary == after.data.summary
    assert before.data.evidence_sha256 == after.data.evidence_sha256
    assert before.data.presentation_sha256 != after.data.presentation_sha256
    assert not after.data.warnings
    md = render_export(after, "md")
    assert "| Player | Budget | Samples / planned" in md and "[Unit](units/unit-00000.json)" in md
    html = render_export(after, "html")
    assert "<script>alert(1)</script>" not in html
    parsed = json.loads(html.split('<script type="application/json" id="data">')[1].split("</script>")[0])
    assert parsed["data"]["summary"] == after.data.summary.model_dump()


def test_discovery_isolates_invalid_unsupported_and_source_copies(lab_run):
    root = lab_run.parent
    for name, manifest in (("bad", "{"), ("future", '{"kind":"learning-v2"}'), ("source/copy", '{"kind":"source"}')):
        folder = root / name
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text(manifest)
    entries = [entry for entry, _ in discover().values()]
    assert len(entries) == 3
    assert {entry.status for entry in entries} == {"complete", "invalid", "unsupported"}


def test_bad_trace_does_not_hide_valid_base_evidence(lab_run):
    (lab_run / "traces").mkdir()
    (lab_run / "traces/broken.json").write_text("{}")
    data = read_bundle(lab_run).data
    assert data.completed == data.planned and len(data.warnings) == 1 and not data.traces


@pytest.mark.parametrize("manifest", [[], "not an object", None, 12])
def test_non_object_manifest_does_not_break_other_runs(lab_run, manifest):
    bad = lab_run.parent / "bad"
    bad.mkdir()
    (bad / "manifest.json").write_text(json.dumps(manifest))
    with TestClient(create_app()) as client:
        response = client.get("/api/experiments")
    assert response.status_code == 200
    assert {row["status"] for row in response.json()} == {"invalid", "complete"}


@pytest.mark.parametrize("status", [{"status": []}, {"status": "surprise"}, [], None])
def test_malformed_status_is_an_isolated_invalid_run(lab_run, status):
    (lab_run / "status.json").write_text(json.dumps(status))
    with TestClient(create_app()) as client:
        response = client.get("/api/experiments")
    assert response.status_code == 200
    assert response.json()[0]["status"] == "invalid"


def test_new_trace_changes_presentation_identity_only(lab_run):
    before = read_bundle(lab_run).data
    inspect_decision(lab_run, "unit-00000", 0, lab_run / "traces/added.json")
    after = read_bundle(lab_run).data
    assert before.evidence_sha256 == after.evidence_sha256
    assert before.presentation_sha256 != after.presentation_sha256
    assert len(after.traces) == 1


def test_job_storage_failure_does_not_launch_or_retain_ownership(lab_run, monkeypatch):
    jobs = TraceJobs()
    jobs.list()
    save = jobs._save

    def fail_save():
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(jobs, "_save", fail_save)
        with pytest.raises(GameError, match="disk full"):
            jobs.start(trace_request(lab_run))
    assert jobs.process is None and jobs.lease is None
    assert jobs.list()[0].status == "failed"
    save()
    jobs.start(trace_request(lab_run))
    assert await_job(jobs).status == "succeeded"
    jobs.close()


def test_symlink_escape_is_rejected(lab_run, tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    (lab_run / "units/escape.json").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        read_bundle(lab_run)


def test_native_api_routes_and_lazy_trace_pages(lab_run):
    inspect_decision(lab_run, "unit-00000", 0, lab_run / "traces/alpha.json")
    run_id = next(iter(discover()))
    with TestClient(create_app()) as client:
        for page in ("/", "/play", "/experiments", f"/experiments/{run_id}", "/reference"):
            assert client.get(page).status_code == 200
        assert client.get("/api/unknown").status_code == 404
        assert client.get("/assets/absent.js").status_code == 404
        data = client.get(f"/api/experiments/{run_id}").json()
        assert ("turns" not in data["units"][0] and "events" not in data["traces"][0]) or isinstance(
            data["traces"][0]["events"], int
        )
        page = client.get(f"/api/experiments/{run_id}/traces/alpha?limit=1&show_work=true").json()
        assert len(page["events"]) <= 1 and page["total"] >= len(page["events"])
        assert client.get("/api/experiments/not-a-run").status_code == 409
        assert client.get(f"/api/experiments/{run_id}/export?format=md").status_code == 200


def test_trace_success_duplicate_and_restart_state(lab_run, tmp_path):
    jobs = TraceJobs(tmp_path / "jobs")
    request = trace_request(lab_run).model_copy(update={"limit": 3})
    started = jobs.start(request)
    assert jobs.start(request).id == started.id
    with pytest.raises(GameError, match="already running"):
        jobs.start(request.model_copy(update={"request_id": uuid4().hex}))
    final = await_job(jobs)
    assert final.status == "succeeded", final.message
    assert final.events == 3 and final.recording_complete is False
    assert (lab_run / f"traces/{final.trace_id}.json").exists()
    assert len(read_bundle(lab_run).traces) == 1
    assert TraceJobs(tmp_path / "jobs").list()[0].status == "succeeded"
    jobs.close()


def test_cached_owners_refresh_and_append_without_losing_completed_jobs(lab_run, tmp_path):
    state = tmp_path / "shared-jobs"
    first, second = TraceJobs(state), TraceJobs(state)
    try:
        assert first.list() == second.list() == []
        first.start(trace_request(lab_run))
        first_result = await_job(first)
        assert first_result.status == "succeeded", first_result.message
        assert second.list() == [first_result]

        second.start(trace_request(lab_run).model_copy(update={"limit": 3}))
        second_result = await_job(second)
        assert second_result.status == "succeeded", second_result.message
        assert first.list() == second.list() == [second_result, first_result]
        assert TraceJobs(state).list() == [second_result, first_result]
        assert len(list((lab_run / "traces").glob("ui-*.json"))) == 2
    finally:
        first.close()
        second.close()


def test_request_id_replay_and_conflict_are_reconciled_across_cached_owners(lab_run, tmp_path):
    state = tmp_path / "shared-jobs"
    first, second = TraceJobs(state), TraceJobs(state)
    request = trace_request(lab_run)
    try:
        assert second.list() == []
        first.start(request)
        completed = await_job(first)
        assert completed.status == "succeeded", completed.message
        assert second.start(request) == completed
        assert len(list((lab_run / "traces").glob("ui-*.json"))) == 1
        with pytest.raises(GameError, match="Request ID already belongs"):
            second.start(request.model_copy(update={"limit": 3}))
        assert second.list() == [completed]

        # Neither the replay nor the conflict may retain the shared lease.
        first.start(request.model_copy(update={"request_id": uuid4().hex}))
        newer = await_job(first)
        assert newer.status == "succeeded", newer.message
        assert second.list() == [newer, completed]
    finally:
        first.close()
        second.close()


def test_cached_observer_cannot_reconcile_or_replace_another_active_owner(lab_run, tmp_path, monkeypatch):
    state = tmp_path / "shared-jobs"
    first, second = TraceJobs(state), TraceJobs(state)
    popen = subprocess.Popen
    monkeypatch.setattr(
        "qi.lab.subprocess.Popen",
        lambda args, **kwargs: popen(
            [sys.executable, "-c", "import time; time.sleep(30)"] if "qi.trace_worker" in args else args, **kwargs
        ),
    )
    request = trace_request(lab_run)
    try:
        assert first.list() == second.list() == []
        started = first.start(request)
        with pytest.raises(GameError, match="Another server owns"):
            second.list()
        with pytest.raises(GameError, match="Another server owns"):
            second.start(request)
        assert first.list()[0].status == "running"
        first.cancel(started.id)
        final = await_job(first)
        assert final.status == "cancelled"
        assert second.list() == [final]
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("failure", ["stale-evidence", "incompatible", "launch", "thread"])
def test_failed_start_releases_the_lease_for_another_cached_owner(lab_run, tmp_path, monkeypatch, failure):
    state = tmp_path / "shared-jobs"
    first, second = TraceJobs(state), TraceJobs(state)
    request = trace_request(lab_run)

    def fail_launch(*_args, **_kwargs):
        raise OSError("launch unavailable")

    def fail_thread(*_args, **_kwargs):
        raise RuntimeError("thread unavailable")

    try:
        assert first.list() == second.list() == []
        with monkeypatch.context() as patch:
            attempted = request
            if failure == "stale-evidence":
                attempted = request.model_copy(update={"unit_sha256": "0" * 64})
            elif failure == "incompatible":
                patch.setattr("qi.lab.trace_compatibility", lambda _: "Runtime changed")
            elif failure == "launch":
                patch.setattr("qi.lab.subprocess.Popen", fail_launch)
            else:
                patch.setattr("qi.lab.threading.Thread.start", fail_thread)
            with pytest.raises(GameError):
                first.start(attempted)

        second.start(request.model_copy(update={"request_id": uuid4().hex}))
        completed = await_job(second)
        assert completed.status == "succeeded", completed.message
        observed = first.list()
        assert observed == second.list()
        assert observed[0] == completed
        if failure in {"launch", "thread"}:
            assert len(observed) == 2 and observed[1].status == "failed"
        else:
            assert observed == [completed]
    finally:
        first.close()
        second.close()


def test_failed_launch_keeps_ownership_until_failure_is_persisted(lab_run, tmp_path, monkeypatch):
    from qi.lab import write_json

    state = tmp_path / "shared-jobs"
    first, second = TraceJobs(state), TraceJobs(state)
    blocked = []

    def observe_failure_write(path, rows):
        if path.name == "jobs.json" and any(row["status"] == "failed" for row in rows):
            try:
                second.list()
            except GameError as error:
                assert error.code == "trace_busy"
                blocked.append(True)
            else:
                blocked.append(False)
        write_json(path, rows)

    def fail_launch(*_args, **_kwargs):
        raise OSError("launch unavailable")

    try:
        assert second.list() == []
        monkeypatch.setattr("qi.lab.write_json", observe_failure_write)
        monkeypatch.setattr("qi.lab.subprocess.Popen", fail_launch)
        with pytest.raises(GameError, match="launch unavailable"):
            first.start(trace_request(lab_run))
        assert blocked == [True]
        assert second.list()[0].status == "failed"
    finally:
        first.close()
        second.close()


def test_trace_mismatch_never_launches(lab_run, monkeypatch, tmp_path):
    request = trace_request(lab_run)
    monkeypatch.setattr("qi.lab.trace_compatibility", lambda _: "Code or runtime changed")
    monkeypatch.setattr("qi.lab.subprocess.Popen", lambda *_a, **_k: pytest.fail("Launched incompatible trace"))
    with pytest.raises(GameError, match="changed"):
        TraceJobs(tmp_path / "jobs").start(request)


@pytest.mark.parametrize("outcome", ["cancelled", "timed-out", "interrupted"])
def test_owned_job_termination_never_publishes(lab_run, monkeypatch, tmp_path, outcome):
    popen = subprocess.Popen
    monkeypatch.setattr(
        "qi.lab.subprocess.Popen",
        lambda args, **kwargs: popen(
            [sys.executable, "-c", "import time; time.sleep(30)"] if "qi.trace_worker" in args else args, **kwargs
        ),
    )
    jobs = TraceJobs(tmp_path / "jobs", deadline=0.1 if outcome == "timed-out" else 5)
    started = jobs.start(trace_request(lab_run))
    if outcome == "cancelled":
        jobs.cancel(started.id)
    elif outcome == "interrupted":
        jobs.close()
    final = await_job(jobs)
    assert final.status == outcome
    assert not list((lab_run / "traces").glob("ui-*.json"))
    assert jobs.cancel(final.id).status == outcome
    jobs.close()


def test_startup_marks_unfinished_state_interrupted(tmp_path):
    state = tmp_path / "jobs"
    state.mkdir()
    request = TraceRequest(run_id="0" * 24, unit_id="unit-00000", unit_sha256="0" * 64, turn_index=0, request_id="test")
    (state / "jobs.json").write_text(
        json.dumps(
            [
                {
                    "id": "test",
                    "request": request.model_dump(),
                    "status": "running",
                    "started": 1,
                    "message": "running",
                    "deadline_seconds": 5,
                }
            ]
        )
    )
    assert TraceJobs(state).list()[0].status == "interrupted"


def test_session_round_trip_mixed_controllers_and_unknown_prefix():
    snapshot = Snapshot(moves=["b2e2"])
    game = restore(snapshot)
    old = Controllers(red=Controller(), black=Controller(player="random", settings={"seed": 7}))
    config = PlayerConfig("random", seed=8)
    choice = choose(game, config)
    game = game.apply(choice.move)
    new = Controllers(red=Controller(player="greedy"), black=Controller())
    session = GameSession(
        snapshot=Snapshot(moves=list(game.moves)),
        controllers=new,
        unknown_prefix=1,
        changes=[ConfigurationChange(ply=1, controllers=old), ConfigurationChange(ply=2, controllers=new)],
        history=[SessionMove(ply=2, side="black", controller=old.black, config=config, choice=choice)],
    )
    assert GameSession.model_validate_json(session.model_dump_json()) == session
    raw = session.model_dump()
    raw["history"][0]["controller"]["player"] = "greedy"
    with pytest.raises(ValueError, match="attribution"):
        GameSession.model_validate(raw)


def test_capability_settings_and_pinned_catalog_without_model_load(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"metadata reads hash bytes, without executing torch")
    config = tmp_path / "players.json"
    config.write_text(
        json.dumps(
            {
                "players": [
                    {"id": "trained-a", "label": "Trained A", "implementation": "policy", "checkpoint": "model.pt"}
                ]
            }
        )
    )
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(config))
    entry = next(entry for entry in list_players() if entry.id == "trained-a")
    assert entry.available and entry.settings == {} and entry.implementation_id == "policy"
    pinned = bind_config(PlayerConfig("trained-a"))
    checkpoint.write_bytes(b"changed resource")
    with pytest.raises(GameError, match="differ"):
        bind_config(pinned)
    with pytest.raises(GameError, match="not supported"):
        resolve_selection("trained-a", {"nodes": 8}, entry.binding_sha256)
    with TestClient(create_app()) as client:
        bad = client.post(
            "/api/play/choose",
            json={
                "snapshot": Snapshot().model_dump(),
                "expected_state_hash": restore(Snapshot()).state_hash,
                "controller": {"player": "greedy", "settings": {"depth": 99}},
            },
        )
        assert bad.status_code == 409
    assert asdict(pinned)["checkpoint_sha256"] == entry.checkpoint_sha256
