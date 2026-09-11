"""Benchmark invariants: replay, recovery, reuse, identity and test-pool lifecycle."""

import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.artifacts import write_json
from qi.benchmark.api import directories
from qi.benchmark.models import BenchmarkSeries, BenchmarkSpec, Book, BookStart, Entrant
from qi.benchmark.runner import run_benchmark
from qi.benchmark.store import load_manifest, read_attempts, writer_lock
from qi.benchmark.summary import summarize_benchmark
from qi.players import Decision, Player, PlayerConfig, PlayerInfo
from qi.protocol import Snapshot

LOOP = ["b0c2", "b9c7", "c2b0", "c7b9"]


@pytest.fixture
def plan(monkeypatch, tmp_path):
    from qi.players import catalog

    def select(game, config):
        return Decision(LOOP[len(game.moves) % 4])

    players = dict(catalog.PLAYERS)
    for id in ("loop-a", "loop-b", "loop-c"):
        players[id] = Player(PlayerInfo(id, id + "-v1", id, "Hermetic repeated horse moves", False), select)
    monkeypatch.setattr(catalog, "PLAYERS", players)
    monkeypatch.setenv("QI_BENCHMARK_STATE", str(tmp_path / "pool-state"))
    book = Book(
        id="fixture",
        use="smoke",
        provenance="Hermetic fixture",
        selection="One source family",
        starts=[
            BookStart(
                id="loop",
                family="one",
                source_game="one",
                source_url="test:one",
                description="Cycle",
                snapshot=Snapshot(moves=LOOP),
            ),
        ],
    )
    refs = [Entrant(id=id, label=id, config=PlayerConfig(id)) for id in ("loop-a", "loop-b")]
    return BenchmarkSpec(
        series=BenchmarkSeries(id="fixture", label="Fixture benchmark", book=book, references=refs, anchor="loop-a"),
        starts=["loop"],
    )


def test_run_replays_both_colors_separates_diagnostic_and_resummarizes_offline(plan, tmp_path, monkeypatch):
    output = tmp_path / "run"
    run_benchmark(plan, output)
    summary = summarize_benchmark(output, persist=True)
    assert summary.status == "complete"
    assert summary.planned_games == summary.completed_games == 4
    assert len(summary.matchups) == 2
    assert all(m.completed_pairs == 1 and m.draws == 2 for m in summary.matchups)
    assert [r.games for r in summary.fit.ratings] == [2, 2]
    assert sum(c.decisions for c in summary.costs.values()) == 8
    manifest = load_manifest(output)
    attempts = read_attempts(output, manifest)
    for slot in manifest.spec.slots():
        game = attempts[slot.id][0].match
        assert game.snapshot.game().outcome.reason == game.reason
        assert (game.red, game.black) == (
            (slot.config_a, slot.config_b) if slot.a_side == "red" else (slot.config_b, slot.config_a)
        )
    monkeypatch.setattr("qi.benchmark.runner.play_match", lambda *_: pytest.fail("Offline scoring executed a player"))
    assert summarize_benchmark(output) == summary
    run_benchmark(manifest.spec, output, resume=True)
    assert summarize_benchmark(output) == summary


def test_failure_preserves_half_pair_and_resume_never_replays_completed_game(plan, tmp_path, monkeypatch):
    from qi.benchmark import runner

    original = runner.play_match
    calls = []

    def fail_second(*args):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError("engine stopped")
        return original(*args)

    monkeypatch.setattr(runner, "play_match", fail_second)
    directory = tmp_path / "failed"
    run_benchmark(plan, directory)
    result = summarize_benchmark(directory)
    assert result.status == "failed" and result.completed_games == 1
    assert result.matchups[0].completed_pairs == 0 and result.matchups[0].score_rate is None
    assert all(r.elo is None for r in result.fit.ratings)
    monkeypatch.setattr(runner, "play_match", original)
    manifest = load_manifest(directory)
    original_game = read_attempts(directory, manifest)[manifest.spec.slots()[0].id][0].sha256
    run_benchmark(manifest.spec, directory, resume=True)
    summary = summarize_benchmark(directory)
    assert summary.status == "complete" and summary.failed_attempts == 1
    history = read_attempts(directory, manifest)
    assert history[manifest.spec.slots()[0].id][0].sha256 == original_game
    assert [a.status for a in history[manifest.spec.slots()[1].id]] == ["failed", "complete"]


def test_abrupt_running_attempt_is_retained_as_interrupted(plan, tmp_path):
    directory = tmp_path / "run"
    manifest = run_benchmark(plan, directory)
    slot = manifest.spec.slots()[0]
    path = directory / "attempts" / slot.id / "000001.json"
    data = json.loads(path.read_text())
    data.update(status="running", finished_at=None, elapsed_seconds=None, match=None)
    write_json(path, data)
    run_benchmark(manifest.spec, directory, resume=True)
    assert [a.status for a in read_attempts(directory, manifest)[slot.id]] == ["interrupted", "complete"]


@pytest.mark.parametrize("field", ["winner", "seed", "version", "latency", "budget", "opening"])
def test_saved_match_corruption_is_rejected(plan, tmp_path, field):
    directory = tmp_path / "run"
    manifest = run_benchmark(plan, directory)
    path = directory / "attempts" / manifest.spec.slots()[0].id / "000001.json"
    data = json.loads(path.read_text())
    choice = data["match"]["turns"][0]["choice"]
    if field == "winner":
        data["match"]["winner"] = "red"
    elif field == "seed":
        choice["seed"] += 1
    elif field == "version":
        choice["player_version"] = "wrong"
    elif field == "latency":
        choice["elapsed_ms"] = -1
    elif field == "budget":
        choice["nodes"] = 1000000
    else:
        data["match"]["opening"]["moves"] = []
    write_json(path, data)
    with pytest.raises(ValueError):
        summarize_benchmark(directory)


def test_rating_snapshot_is_checked_against_recomputed_evidence(plan, tmp_path):
    directory = tmp_path / "run"
    run_benchmark(plan, directory)
    summary = summarize_benchmark(directory, persist=True)
    path = directory / "reports" / f"{summary.evidence_sha256}.json"
    data = json.loads(path.read_text())
    data["fit"]["ratings"][0]["elo"] += 500
    write_json(path, data)
    with pytest.raises(ValueError, match="rescored"):
        summarize_benchmark(directory)


def test_gauntlet_reuses_reference_games_once_and_rejects_changed_conditions(plan, tmp_path):
    baseline = tmp_path / "baseline"
    frozen = run_benchmark(plan, baseline).spec
    gauntlet = BenchmarkSpec(
        series=frozen.series,
        starts=frozen.starts,
        mode="gauntlet",
        candidates=[Entrant(id="loop-c", label="Candidate", config=PlayerConfig("loop-c"))],
    )
    output = tmp_path / "candidate"
    run_benchmark(gauntlet, output, reuse=[baseline, baseline])
    summary = summarize_benchmark(output)
    assert summary.reused_games == 4 and summary.completed_games == 12
    assert len(summary.fit.ratings) == 3
    changed = frozen.model_copy(deep=True)
    changed.series.references[0].config = replace(changed.series.references[0].config, nodes=999)
    with pytest.raises(ValueError, match="identical"):
        run_benchmark(changed, tmp_path / "changed", reuse=[baseline])
    assert not (tmp_path / "changed").exists()


def test_locked_pool_hides_results_retires_and_cannot_be_renamed_for_reuse(plan, tmp_path):
    plan.series.book.use = "locked-test"
    directory = tmp_path / "locked"
    frozen = run_benchmark(plan, directory).spec
    hidden = summarize_benchmark(directory)
    assert hidden.results_hidden and hidden.fit is None and not hidden.matchups
    with pytest.raises(ValueError, match="reserved"):
        run_benchmark(frozen, tmp_path / "duplicate")
    revealed = summarize_benchmark(directory, reveal=True, persist=True)
    assert revealed.pool_status == "retired" and not revealed.results_hidden
    assert summarize_benchmark(directory) == revealed
    copied = plan.model_copy(deep=True)
    copied.series.book.id = "renamed-test"
    with pytest.raises(ValueError, match="retired"):
        run_benchmark(copied, tmp_path / "renamed")


def test_writer_lock_is_shared_through_symlinks(plan, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with writer_lock(real / ".run.lock"), pytest.raises(ValueError, match="writer"):
        run_benchmark(plan, alias / "run")


def test_fresh_locked_gauntlet_runs_its_reference_matrix_without_reuse(plan, tmp_path):
    plan.series.book.use = "locked-test"
    plan.mode = "gauntlet"
    plan.candidates = [Entrant(id="loop-c", label="Candidate", config=PlayerConfig("loop-c"))]
    output = tmp_path / "confirmation"
    run_benchmark(plan, output)
    hidden = summarize_benchmark(output)
    assert hidden.results_hidden and hidden.completed_games == 12
    assert summarize_benchmark(output, reveal=True).status == "complete"


def test_development_exposure_cannot_be_rebranded_as_fresh_confirmation(plan, tmp_path):
    plan.series.book.use = "development"
    run_benchmark(plan, tmp_path / "development")
    plan.series.book.use = "locked-test"
    with pytest.raises(ValueError, match="development"):
        run_benchmark(plan, tmp_path / "confirmation")


def test_selected_start_order_is_honored_without_changing_slot_identity(plan):
    second = plan.series.book.starts[0].model_copy(update={"id": "second", "snapshot": Snapshot(moves=LOOP[:2])})
    plan.series.book.starts.append(second)
    plan.starts = ["loop", "second"]
    original = plan.slots()
    plan.starts = ["second", "loop"]
    reordered = plan.slots()
    assert [s.start.id for s in reordered[:4]] == ["second", "second", "loop", "loop"]
    assert {s.id for s in original} == {s.id for s in reordered}


def test_api_discovery_typed_results_missing_and_escaped_paths(plan, tmp_path, monkeypatch):
    root = tmp_path / "benchmarks"
    directory = root / "run"
    run_benchmark(plan, directory)
    summarize_benchmark(directory, persist=True)
    monkeypatch.setenv("QI_BENCHMARK_ROOTS", str(root))
    outside = tmp_path / "outside"
    run_benchmark(plan, outside)
    (root / "escape").symlink_to(outside, target_is_directory=True)
    with TestClient(create_app()) as client:
        listing = client.get("/api/benchmarks").json()
        assert len(listing["entries"]) == 1
        id = listing["entries"][0]["id"]
        assert id in directories()
        result = client.get(f"/api/benchmarks/{id}")
        assert result.status_code == 200
        assert result.json()["summary"]["completed_games"] == 4
        assert client.get("/api/benchmarks/missing").status_code == 404
        assert client.get(f"/api/benchmarks/{id}/snapshots/bad").status_code == 404
