"""Policy generation against the real collection and immutable snapshot boundary."""

import json

import pytest

from qi.evaluation import Corpus, Opening
from qi.game import GameError, legal_moves
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherIdentity, digest
from qi.training_data.generation_io import CollectionIO, analysis_spec
from qi.training_data.generation_policies import ActorPolicy, SamplingPolicy
from qi.training_data.generation_runner import (
    GenerationSource,
    GenerationTeacher,
    PolicyGenerationConfig,
    generate_policies,
)
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, SnapshotReader, export_snapshot, verify_snapshot
from qi.training_data.store import AnalysisSpec, Collection, OccurrencePayload


@pytest.fixture
def setup(tmp_path):
    engine, network = tmp_path / "engine", tmp_path / "network"
    engine.write_text("fake engine")
    network.write_text("fake network")
    teacher = GenerationTeacher(
        engine=str(engine),
        network=str(network),
        engine_sha256=digest(engine),
        network_sha256=digest(network),
        nodes=100,
        timeout_seconds=1.0,
    )
    config = PolicyGenerationConfig(
        name="policy-test",
        seconds=120.0,
        corpus=Corpus(
            id="reserved",
            provenance="test",
            openings=[Opening(id="initial", description="Initial board", snapshot=Snapshot())],
        ),
        teachers={"actor": teacher, "strong": teacher.model_copy(update={"nodes": 1000})},
        actor_teacher="actor",
        supervision=["actor", "strong"],
        actor_audit_every=2,
        sources=[
            GenerationSource(
                id="main",
                games=1,
                split="train",
                additional_plies=12,
                sampling=SamplingPolicy(phase_counts={"opening": 2}, min_spacing=3, min_ply=3),
            )
        ],
    )
    calls = []

    def provider(game, settings):
        calls.append((game.moves, settings.nodes, settings.multipv))
        legal = sorted(legal_moves(game.board, game.turn))
        identity = TeacherIdentity.read(settings)
        spec = analysis_spec(settings, identity).supervision
        return TeacherAnalysis(
            schema_version=int(spec["adapter"][-1]),
            adapter_version=spec["adapter"],
            snapshot=Snapshot(moves=list(game.moves)),
            state_hash=game.state_hash,
            move=legal[0],
            engine_name="test",
            engine_sha256=identity.engine_sha256,
            network_sha256=identity.network_sha256,
            settings=spec["settings"],
            requested_nodes=settings.nodes,
            requested_depth=settings.depth,
            timeout_seconds=settings.timeout_seconds,
            reported_nodes=settings.nodes,
            reported_depth=3,
            elapsed_ms=1.0,
            score=None,
            search_info=[
                f"info depth 3 multipv {i + 1} score cp {100 - 10 * i} nodes {settings.nodes} pv {move}"
                for i, move in enumerate(legal[: settings.multipv])
            ],
        )

    return config, provider, calls


def completed(store):
    return [store.game(r[0]) for r in store.db.execute("SELECT id FROM games WHERE status='complete' ORDER BY id")]


def test_generation_retention_and_resume(tmp_path, setup):
    config, provider, calls = setup
    with Collection(tmp_path / "s.sqlite") as store:
        result = generate_policies(store, config, provider=provider)
        assert result["status"] == "complete" and result["games"] == 1
        game = completed(store)[0]
        assert game.actor_queries == 12 and game.actor_nodes == 1200
        selection = game.actor["generation_result"]["sampling"]["selected"]
        selected = []
        for row in store.db.execute("SELECT ply_count,json(payload) FROM position_occurrences"):
            metadata = OccurrencePayload.model_validate_json(row[1]).metadata
            if metadata.get("selected"):
                selected.append(row[0])
                assert metadata["actor_decision"]["move"] == game.snapshot.moves[row[0]]
        assert sorted(selected) == selection
        assert store.counts()["analysis_specs"] == 3  # Actor MultiPV plus two independent single-PV labels.
        before = store.counts()
        calls.clear()
        second = generate_policies(store, config, provider=provider)
        assert second["reused_games"] == 1 and not calls and store.counts() == before
        assert second["selected_by_phase"] == result["selected_by_phase"]
    with Collection(tmp_path / "s.sqlite") as store:
        assert generate_policies(store, config, provider=provider)["reused_games"] == 1


def test_actor_does_not_depend_on_sampling_or_game_count(tmp_path, setup):
    config, provider, _ = setup
    with Collection(tmp_path / "a.sqlite") as store:
        generate_policies(store, config, provider=provider)
        original = completed(store)[0].snapshot
    config.sources[0].games = 2
    config.sources[0].sampling = SamplingPolicy(phase_counts={"opening": 4}, min_spacing=1)
    with Collection(tmp_path / "b.sqlite") as store:
        generate_policies(store, config, provider=provider)
        assert completed(store)[0].snapshot == original


def test_one_intervention_then_teacher_recovery(tmp_path, setup):
    config, provider, _ = setup
    config.sources[0].actor = ActorPolicy(mode="intervention", intervention_min_ply=3, intervention_max_ply=3)
    with Collection(tmp_path / "s.sqlite") as store:
        generate_policies(store, config, provider=provider)
        result = completed(store)[0].actor["generation_result"]
        assert result["intervention_applied"]
        assert sum(d["intervention"] for d in result["decisions"]) == 1
        for d in result["decisions"]:
            before = Snapshot(moves=completed(store)[0].snapshot.moves[: d["ply"]]).game()
            best = sorted(legal_moves(before.board, before.turn))[0]
            assert (d["move"] != best) == (d["ply"] == 3)


@pytest.mark.parametrize("error,retries", [("teacher_timeout", 1), ("teacher_exit", 1), ("teacher_mismatch", 0)])
def test_failure_policy_and_reopen(tmp_path, setup, error, retries):
    config, provider, calls = setup
    attempts = []

    def broken(game, settings):
        attempts.append(1)
        raise GameError(error, "injected")

    path = tmp_path / "s.sqlite"
    with Collection(path) as store:
        with pytest.raises(GameError, match="injected"):
            generate_policies(store, config, provider=broken)
        assert len(attempts) == 1 + retries
        assert store.game(1).actor_queries == 1 + retries
        assert store.db.execute("SELECT count(*) FROM analyses WHERE status='failed'").fetchone()[0] == 1 + retries
    with Collection(path) as store:
        generate_policies(store, config, provider=provider)
        assert len(completed(store)) == 1
        assert store.db.execute("SELECT count(*) FROM games").fetchone()[0] == 2
        calls.clear()
        generate_policies(store, config, provider=provider)
        assert not calls


def test_transient_retry_succeeds_and_invalid_answer_fails_fast(tmp_path, setup):
    config, provider, calls = setup
    attempt = 0

    def transient(game, settings):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise GameError("teacher_timeout", "one failure")
        return provider(game, settings)

    with Collection(tmp_path / "retry.sqlite") as store:
        result = generate_policies(store, config, provider=transient)
        assert result["execution_counters"]["retries"] == 1
        assert completed(store)[0].actor_queries == 13
    calls.clear()

    def wrong(game, settings):
        answer = provider(game, settings)
        return answer.model_copy(update={"state_hash": "invalid"})

    with Collection(tmp_path / "wrong.sqlite") as store:
        with pytest.raises(ValueError):
            generate_policies(store, config, provider=wrong)
        assert len(calls) == 1
        assert store.db.execute("SELECT status FROM analyses").fetchone()[0] == "failed"


def test_deadline_does_not_weaken_query_budget(tmp_path, setup):
    config, provider, calls = setup
    config.seconds = 0.5  # Smaller than the frozen 1-second query timeout.
    with Collection(tmp_path / "s.sqlite") as store:
        with pytest.raises(GameError, match="pinned query timeout"):
            generate_policies(store, config, provider=provider, clock=lambda: 0.0)
        assert not calls
        assert store.db.execute("SELECT stop_reason FROM games").fetchone()[0] == "deadline"


def test_shortfalls_are_not_redistributed(tmp_path, setup):
    config, provider, _ = setup
    config.sources[0].sampling.phase_counts = {"opening": 1, "endgame": 5}
    with Collection(tmp_path / "s.sqlite") as store:
        result = generate_policies(store, config, provider=provider)
        assert result["status"] == "shortfall"
        assert result["selected_by_phase"] == {"opening": 1, "endgame": 0}
        assert result["shortfall_by_phase"] == {"opening": 0, "endgame": 5}
        assert result["generation_status"] == "complete"


def test_generated_child_preserves_parent_and_split(tmp_path, setup):
    config, provider, _ = setup
    with Collection(tmp_path / "s.sqlite") as store:
        generate_policies(store, config, provider=provider)
        start, parent = CollectionIO(store).generated_start(1, 4)
        child = config.model_copy(deep=True)
        child.name = "child"
        child.sources[0].id = "child"
        child.sources[0].start = start
        child.sources[0].parent_trajectory = parent
        generate_policies(store, child, provider=provider)
        assert completed(store)[1].parent_digest == parent
        assert completed(store)[1].family == completed(store)[0].family
        assert completed(store)[1].snapshot.moves[:4] == completed(store)[0].snapshot.moves[:4]
        child.sources[0].split = "validation"
        with pytest.raises(ValueError, match="family and split"):
            generate_policies(store, child, provider=provider)


def test_selected_sql_export_and_frozen_reader(tmp_path, setup):
    pytest.importorskip("pyarrow")
    config, provider, _ = setup
    config.sources[0].actor = ActorPolicy(mode="random")
    config.sources[0].sampling = SamplingPolicy(
        phase_counts={"opening": 2, "middlegame": 2, "endgame": 2, "unknown": 2}, min_spacing=1, min_ply=3
    )
    config.sources += [config.sources[0].model_copy(update={"id": "validation", "split": "validation"})]
    with Collection(tmp_path / "s.sqlite") as store:
        generate_policies(store, config, provider=provider)
        # Add a compatible audit-only analysis: a matching spec alone must not make it eligible.
        snapshot = Snapshot(moves=store.game(1).snapshot.moves[:2])
        audit = CollectionIO(store).occurrence(1, snapshot, {"actor_audit": True})
        answer = provider(snapshot.game(), config.teachers["strong"].config())
        CollectionIO(store).retain(audit, answer)
        recipe = SelectionRecipe(
            analysis_spec=AnalysisSpec.from_analysis(answer).identity,
            reserved_corpus=config.corpus,
            selected_only=True,
            buckets=[SnapshotBucket(id=s, split=s, count=2) for s in ("train", "validation")],
        )
        path = tmp_path / "snapshot"
        manifest = export_snapshot(store, recipe, path, shard_rows=1)
        assert manifest["rows"] == 4
        rows = [row for b in SnapshotReader(path).batches(1) for row in b.to_pylist()]
        assert len(rows) == 4
        selected = {
            r[0]
            for r in store.db.execute(
                "SELECT identity FROM position_occurrences WHERE json_extract(payload,'$.metadata.selected')=1"
            )
        }
        assert {r["occurrence"] for r in rows} <= selected
        before = (path / "manifest.json").read_bytes()
        # Another successful analysis cannot mutate an existing snapshot's rows or evidence.
        spec = store.spec(AnalysisSpec.from_analysis(answer))
        store.finish_analysis(store.begin_analysis(audit, spec), answer)
        assert verify_snapshot(path)["rows"] == 4 and (path / "manifest.json").read_bytes() == before
        assert sum(len(b) for b in SnapshotReader(path).label_batches(1)) == 4
        assert json.loads(before)["recipe"]["selected_only"]


def test_interruption_keeps_completed_games_and_failure_evidence(tmp_path, setup):
    config, provider, _ = setup
    config.sources[0].games = 2
    completed_first = False

    def events(event):
        nonlocal completed_first
        if event["kind"] == "completed-game":
            completed_first = True

    def interrupted(game, settings):
        if completed_first:
            raise KeyboardInterrupt()
        return provider(game, settings)

    path = tmp_path / "interrupted.sqlite"
    with Collection(path) as store:
        with pytest.raises(KeyboardInterrupt):
            generate_policies(store, config, provider=interrupted, event=events)
        assert len(completed(store)) == 1
        first_snapshot = completed(store)[0].snapshot
        assert store.db.execute("SELECT status FROM games ORDER BY id DESC LIMIT 1").fetchone()[0] == "interrupted"
    with Collection(path) as store:
        result = generate_policies(store, config, provider=provider)
        assert result["games"] == 2 and result["reused_games"] == 1
        assert completed(store)[0].snapshot == first_snapshot
        assert store.db.execute("SELECT count(*) FROM games").fetchone()[0] == 3


def test_asset_locations_do_not_change_seeded_moves(tmp_path, setup):
    config, provider, _ = setup
    with Collection(tmp_path / "a.sqlite") as store:
        generate_policies(store, config, provider=provider)
        original = completed(store)[0].snapshot
    from pathlib import Path

    for field in ("engine", "network"):
        old = Path(getattr(config.teachers["actor"], field))
        new = tmp_path / ("relocated-" + field)
        new.write_bytes(old.read_bytes())
        for teacher in config.teachers.values():
            setattr(teacher, field, str(new))
    with Collection(tmp_path / "b.sqlite") as store:
        generate_policies(store, config, provider=provider)
        assert completed(store)[0].snapshot == original
