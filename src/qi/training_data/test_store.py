"""Collection recovery, exact identities, SQL isolation and standalone snapshot contracts."""

import json
import sqlite3
from dataclasses import replace

import pytest
from qi_game.contracts import Snapshot
from qi_game.reference import restore

from qi.training_data.compatibility import export_legacy, import_json
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, SnapshotReader, export_snapshot, verify_snapshot
from qi.training_data.store import AnalysisSpec, Collection, GamePayload, RunPayload, board_identity


def run(store):
    return store.run(RunPayload(config={}, provenance={}, seed=7, planned_games=1))


def game(store, run_id, key="source", split="train"):
    return store.begin_game(
        run_id,
        key,
        GamePayload(
            source_id=key, family=key, split=split, mode="random", initial=Snapshot(), snapshot=Snapshot(), actor={}
        ),
    )


def recipe(store, corpus, count=1):
    spec = store.db.execute("SELECT identity FROM analysis_specs ORDER BY id LIMIT 1").fetchone()[0]
    return SelectionRecipe(
        analysis_spec=spec,
        reserved_corpus=corpus,
        buckets=[SnapshotBucket(id=split, split=split, count=count) for split in ("train", "validation")],
    )


def test_analysis_spec_preserves_persisted_identity_and_validates_nested_fields():
    # This digest predates the typed mapping; saved selections refer to it.
    payload = {
        "version": 1,
        "supervision": {
            "target": "legal-teacher-move-v1",
            "authority": "teacher-preference",
            "adapter": "uci-teacher-v2",
            "engine_sha256": "a" * 64,
            "network_sha256": "b" * 64,
            "settings": {"Threads": "1", "Hash": "16", "MultiPV": "2", "Ponder": "false"},
            "nodes": 100,
            "depth": None,
        },
        "timeout_seconds": 1.0,
        "output_contract": "teacher-analysis-v1-v2",
    }
    saved = json.dumps(payload, separators=(",", ":"))
    spec = AnalysisSpec.model_validate_json(saved)
    assert spec.model_dump_json() == saved
    assert spec.identity == "b9ea3d70c429bc0c249dbea1f0806f11f6a9ea0a80a64340e010f2f657ca5c67"
    for key, value in (
        ("nodes", "100"),
        ("depth", 65),
        ("settings", {"Threads": 1}),
        ("engine_sha256", "invalid"),
        ("unrecognized", True),
    ):
        invalid = {**payload, "supervision": {**payload["supervision"], key: value}}
        with pytest.raises(ValueError):
            AnalysisSpec.model_validate(invalid)
        with pytest.raises(ValueError):
            AnalysisSpec.model_validate_json(json.dumps(invalid))


def test_recovery_prefixes_and_first_committed_success(tmp_path, data_setup):
    _, _, teacher, labeler, _ = data_setup
    path = tmp_path / "store.sqlite"
    with Collection(path) as store:
        rid = run(store)
        gid = game(store, rid)
        initial = store.occurrence(gid, Snapshot())
        current = Snapshot(moves=["b0c2"])
        store.append(gid, current)
        with pytest.raises(ValueError, match="Prefix mutation"):
            store.append(gid, Snapshot(moves=["h0g2"]))
        assert store.snapshot(initial) == Snapshot()
        oid = store.occurrence(gid, current)
        answer = labeler(restore(current), teacher)
        spec = store.spec(AnalysisSpec.from_analysis(answer))
        older = store.begin_analysis(oid, spec)
        newer = store.begin_analysis(oid, spec)
        store.finish_analysis(newer, answer)
        store.finish_analysis(older, answer)
        assert store.first_success(oid, spec)[0] == newer
        unfinished = store.begin_analysis(oid, spec)
        with pytest.raises(ValueError, match="writer"):
            Collection(path)
    with Collection(path) as store:
        assert store.snapshot(oid) == current
        assert store.db.execute("SELECT status FROM analyses WHERE id=?", (unfinished,)).fetchone()[0] == "interrupted"
        assert store.db.execute("SELECT status FROM games WHERE id=?", (gid,)).fetchone()[0] == "interrupted"
        assert game(store, rid) != gid
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            store.db.execute("UPDATE position_occurrences SET state_hash='broken' WHERE id=?", (oid,))
        with pytest.raises(sqlite3.IntegrityError):
            store.db.execute(
                (
                    "INSERT INTO analyses(occurrence_id,spec_id,attempt,request,status"
                    ",created,payload) VALUES(999,999,'x','x','running',0,jsonb('{}'))"
                )
            )


def test_same_board_different_histories_and_second_spec(tmp_path, data_setup):
    _, _, teacher, labeler, _ = data_setup
    with Collection(tmp_path / "s.sqlite") as store:
        gid = game(store, run(store))
        first = store.occurrence(gid, Snapshot())
        repeated = Snapshot(moves=["b0c2", "b9c7", "c2b0", "c7b9"])
        for i in range(1, 5):
            store.append(gid, Snapshot(moves=repeated.moves[:i]))
        second = store.occurrence(gid, repeated)
        assert first != second and board_identity(Snapshot()) == board_identity(repeated)
        for oid in (first, second):
            for config in (teacher, replace(teacher, nodes=101)):
                answer = labeler(restore(store.snapshot(oid)), config)
                spec = store.spec(AnalysisSpec.from_analysis(answer))
                failed = store.begin_analysis(oid, spec)
                store.finish_analysis(failed, failure="fixture")
                store.finish_analysis(store.begin_analysis(oid, spec), answer)
        assert store.counts()["games"] == 1
        assert store.counts()["analyses"] == 8
        assert store.counts()["analysis_specs"] == 2


def test_import_snapshot_independent_replay_and_bounded_reader(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    source = tmp_path / "legacy.json"
    source.write_text(tiny_dataset.model_dump_json())
    path = tmp_path / "s.sqlite"
    with Collection(path) as store:
        import_json(store, source)
        before = store.counts()
        import_json(store, source)
        assert store.counts() == before
        selected = recipe(store, tiny_dataset.reserved_corpus)
        manifest = export_snapshot(store, selected, tmp_path / "snapshot", shard_rows=1)
        assert manifest["rows"] == 2
        store.db.execute("UPDATE position_occurrences SET phase='unknown'")
        store.db.commit()
        assert verify_snapshot(tmp_path / "snapshot")["rows"] == 2
        with pytest.raises(ValueError, match="quotas"):
            export_snapshot(store, recipe(store, tiny_dataset.reserved_corpus, 100), tmp_path / "short")
        assert not (tmp_path / "short").exists()
        assert json.loads((tmp_path / "short.pending/manifest.json").read_text())["actual"]
    reader = SnapshotReader(tmp_path / "snapshot")
    assert [len(b) for b in reader.batches(1)] == [1, 1]
    assert sum(len(b) for b in reader.label_batches(1)) == 2
    export_legacy(tmp_path / "snapshot", tmp_path / "roundtrip.json")
    from qi.training_data.v1 import Dataset

    reread = Dataset.model_validate_json((tmp_path / "roundtrip.json").read_text())
    original = {label.input_sha256: label.analysis for label in tiny_dataset.labels}
    assert all(original[label.input_sha256] == label.analysis for label in reread.labels)


def test_generation_resume_without_duplicate_games(tmp_path, data_setup):
    from qi.teacher import digest
    from qi.training_data.assembly import Bucket, MixtureRecipe
    from qi.training_data.collection_generation import generate_collection
    from qi.training_data.config import PreparationConfig, SupervisionSettings
    from qi.training_data.contracts import fingerprint
    from qi.training_data.generation import teacher_spec

    settings, corpus, teacher, labeler, calls = data_setup
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(corpus.model_dump_json())
    config = PreparationConfig(
        corpus=str(corpus_path),
        corpus_sha256=corpus.digest,
        generation=settings,
        supervision=SupervisionSettings(
            engine=str(teacher.engine),
            network=str(teacher.network),
            engine_sha256=digest(teacher.engine),
            network_sha256=digest(teacher.network),
            nodes=teacher.nodes,
            depth=teacher.depth,
            timeout_seconds=float(teacher.timeout_seconds),
        ),
        assembly=MixtureRecipe(
            id="fixture",
            supervision_fingerprint=fingerprint("supervision-v1", teacher_spec(teacher)),
            buckets=[Bucket(id=s, split=s, count=1) for s in ("train", "validation")],
        ),
    )

    # Existing fixture's timeout differs from its query config; correct it at this boundary.
    def answer(game, config):
        return labeler(game, config).model_copy(update={"timeout_seconds": float(config.timeout_seconds)})

    with Collection(tmp_path / "s.sqlite") as store:
        first = generate_collection(store, config, labeler=answer)
        calls.clear()
        second = generate_collection(store, config, labeler=answer)
        assert first == second and not calls
        assert first["games"] == 4
        assert first["position_occurrences"] == 32

    config.generation.sources = [settings.sources[2]]

    def failed_actor(game, config):
        raise RuntimeError("actor query failed")

    with Collection(tmp_path / "failed-actor.sqlite") as store:
        with pytest.raises(RuntimeError, match="actor query failed"):
            generate_collection(store, config, labeler=failed_actor)
        gid = store.db.execute("SELECT id FROM games").fetchone()[0]
        assert store.game(gid).actor_queries == 1
        assert store.db.execute("SELECT status FROM analyses").fetchone()[0] == "failed"


def test_snapshot_attempt_override_and_default_are_stable(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        import_json(store, source)
        selection = recipe(store, tiny_dataset.reserved_corpus)
        first = export_snapshot(store, selection, tmp_path / "first")
        row = next(SnapshotReader(tmp_path / "first").batches()).to_pylist()[0]
        analysis = store.db.execute(
            "SELECT occurrence_id,spec_id,json(payload) FROM analyses WHERE attempt=?", (row["analysis"],)
        ).fetchone()
        from qi_game.reference import legal_moves

        from qi.training_data.store import AnalysisPayload

        answer = AnalysisPayload.model_validate_json(analysis[2]).answer
        game = restore(answer.snapshot)
        answer.move = next(m for m in legal_moves(game.board, game.turn) if m != answer.move)
        new_id = store.begin_analysis(analysis[0], analysis[1])
        store.finish_analysis(new_id, answer)
        export_snapshot(store, selection, tmp_path / "default")
        default_rows = [r for b in SnapshotReader(tmp_path / "default").batches() for r in b.to_pylist()]
        assert next(r for r in default_rows if r["occurrence"] == row["occurrence"])["analysis"] == row["analysis"]
        new_attempt = store.db.execute("SELECT attempt FROM analyses WHERE id=?", (new_id,)).fetchone()[0]
        selection.overrides[row["occurrence"]] = new_attempt
        export_snapshot(store, selection, tmp_path / "override")
        overridden = [r for b in SnapshotReader(tmp_path / "override").batches() for r in b.to_pylist()]
        assert next(r for r in overridden if r["occurrence"] == row["occurrence"])["move"] == answer.move
        assert verify_snapshot(tmp_path / "first")["fingerprint"] == first["fingerprint"]
        stable = export_snapshot(store, selection, tmp_path / "same")
        assert stable["fingerprint"] == SnapshotReader(tmp_path / "override").manifest["fingerprint"]


def test_interrupted_prefixes_not_selected_and_observation_leakage(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        import_json(store, source)
        selection = recipe(store, tiny_dataset.reserved_corpus)
        label = tiny_dataset.split_labels("train")[0]
        rid = run(store)
        gid = game(store, rid, "other", "validation")
        for i in range(1, len(label.analysis.snapshot.moves) + 1):
            store.append(gid, Snapshot(moves=label.analysis.snapshot.moves[:i]))
        oid = store.occurrence(gid, label.analysis.snapshot)
        spec = store.spec(AnalysisSpec.from_analysis(label.analysis))
        store.finish_analysis(store.begin_analysis(oid, spec), label.analysis)
        # Unfinished evidence is retained but does not contaminate normal eligibility.
        export_snapshot(store, selection, tmp_path / "before")
        store.finish_game(gid, "ply-budget")
        with pytest.raises(ValueError, match="observation lineage"):
            export_snapshot(store, selection, tmp_path / "leak")


def test_identical_trajectory_rejected_even_with_disjoint_samples(tmp_path):
    with Collection(tmp_path / "s.sqlite") as store:
        rid = run(store)
        for split in ("train", "validation"):
            gid = game(store, rid, split, split)
            store.append(gid, Snapshot(moves=["b0c2"]))
            if split == "train":
                store.finish_game(gid, "ply-budget")
            else:
                with pytest.raises(ValueError, match="trajectory crosses splits"):
                    store.finish_game(gid, "ply-budget")


def test_corrupt_schema_jsonb_and_snapshot_rejected(tmp_path, tiny_dataset):
    path = tmp_path / "s.sqlite"
    with Collection(path) as store:
        rid = run(store)
        with pytest.raises(sqlite3.IntegrityError):
            store.db.execute("UPDATE generation_runs SET payload=x'1234' WHERE id=?", (rid,))
        store.db.execute("PRAGMA user_version=999")
        store.db.commit()
    with pytest.raises(ValueError, match="Unsupported collection schema"):
        Collection(path)


def test_incremental_append_preserves_metadata_accounting_and_caller_isolation(tmp_path, monkeypatch):
    with Collection(tmp_path / "incremental.sqlite") as store:
        gid = game(store, run(store))
        original = store.game(gid).model_dump()
        validated = []
        validate = store._validate_game

        def tracked(data, identity):
            validated.append(identity)
            return validate(data, identity)

        monkeypatch.setattr(store, "_validate_game", tracked)
        first = Snapshot(moves=["b0c2"])
        store.append(gid, first, actor_nodes=3, actor_ms=0.25, actor_queries=1)
        store.append(gid, first, actor_nodes=4, actor_ms=0.5, actor_queries=1)
        first.moves.clear()  # callers cannot mutate the validated cached prefix
        second = Snapshot(moves=["b0c2", "b9c7"])
        store.append(gid, second, actor_nodes=5, actor_ms=0.75, actor_queries=1)
        assert len(validated) == 1
        result = store.game(gid)
        assert result.model_dump() == original | {
            "snapshot": second.model_dump(),
            "actor_nodes": 12,
            "actor_ms": 1.5,
            "actor_queries": 3,
        }
        result.actor_nodes = 900
        result.snapshot.moves.clear()
        store.append(gid, second)
        assert store.game(gid).actor_nodes == 12
        # A valid SQL metadata update invalidates reuse and must survive the append.
        with store.db:
            store.db.execute(
                "UPDATE games SET payload=jsonb_set(payload,'$.themes',jsonb('[\"new\"]')) WHERE id=?", (gid,)
            )
        store.append(gid, second)
        assert store.game(gid).themes == ["new"]
        other = game(store, store.db.execute("SELECT run_id FROM games WHERE id=?", (gid,)).fetchone()[0], "other")
        store.append(other, Snapshot(moves=["a3a4"]))
        store.append(gid, second)
        assert store.game(other).snapshot.moves == ["a3a4"]
        with pytest.raises(ValueError, match="replay identity"):
            store.append(gid, second.model_copy(update={"ruleset": "wrong"}))


@pytest.mark.parametrize(
    "change",
    [
        "family='wrong'",
        "split='validation'",
        "trajectory='wrong'",
        "payload=jsonb_set(payload,'$.version',2)",
        "payload=jsonb_set(payload,'$.unexpected',1)",
        "payload=jsonb_set(payload,'$.actor_nodes','invalid')",
        "payload=jsonb_set(payload,'$.snapshot.moves',jsonb('[\"a3a4\"]'))",
    ],
)
def test_append_never_reuses_validation_after_persisted_corruption(tmp_path, change):
    with Collection(tmp_path / "corrupt.sqlite") as store:
        gid = game(store, run(store))
        store.append(gid, Snapshot(moves=["b0c2"]))
        with store.db:
            store.db.execute(f"UPDATE games SET {change} WHERE id=?", (gid,))
        before = tuple(
            store.db.execute("SELECT payload,family,split,trajectory FROM games WHERE id=?", (gid,)).fetchone()
        )
        with pytest.raises(ValueError):
            store.append(gid, Snapshot(moves=["b0c2", "b9c7"]))
        assert (
            tuple(store.db.execute("SELECT payload,family,split,trajectory FROM games WHERE id=?", (gid,)).fetchone())
            == before
        )


def test_append_commit_failure_keeps_cache_and_disk_at_committed_prefix(tmp_path):
    path = tmp_path / "commit.sqlite"
    with Collection(path) as store:
        gid = game(store, run(store))
        first = Snapshot(moves=["b0c2"])
        second = Snapshot(moves=["b0c2", "b9c7"])
        store.append(gid, first, actor_nodes=3)
        cached = store._append_cache
        store.db.execute(
            "CREATE TRIGGER bad_fk AFTER UPDATE ON games BEGIN UPDATE games SET run_id=999 WHERE id=NEW.id; END"
        )
        store.db.execute("PRAGMA defer_foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            store.append(gid, second, actor_nodes=5)
        assert store._append_cache is cached
        assert store.game(gid).snapshot == first and store.game(gid).actor_nodes == 3
        store.db.execute("DROP TRIGGER bad_fk")
        store.append(gid, second, actor_nodes=5)
        assert store.game(gid).actor_nodes == 8
        store.finish_game(gid, "ply-budget")
        with pytest.raises(ValueError, match="running game"):
            store.append(gid, second, actor_nodes=1)
    with Collection(path) as reopened:
        assert reopened.game(gid).snapshot == second and reopened.game(gid).actor_nodes == 8
        assert reopened.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not reopened.db.execute("PRAGMA foreign_key_check").fetchall()


def test_append_normalizes_valid_missing_defaults_and_rejects_bad_counters(tmp_path):
    with Collection(tmp_path / "defaults.sqlite") as store:
        gid = game(store, run(store))
        with store.db:
            store.db.execute(
                "UPDATE games SET payload=jsonb_remove(payload,'$.themes','$.snapshot.moves','$.snapshot.ruleset') "
                "WHERE id=?",
                (gid,),
            )
        first = Snapshot(moves=["b0c2"])
        store.append(gid, first, actor_nodes=2**80)
        actual = json.loads(store.db.execute("SELECT json(payload) FROM games WHERE id=?", (gid,)).fetchone()[0])
        assert actual == store.game(gid).model_dump()
        assert actual["snapshot"] == first.model_dump() and actual["actor_nodes"] == 2**80
        before = store.game(gid)
        for counters in [{"actor_nodes": 0.5}, {"actor_ms": float("inf")}, {"actor_ms": float("nan")}]:
            with pytest.raises(ValueError):
                store.append(gid, first, **counters)
            assert store.game(gid) == before


def test_append_rejects_a_row_changed_after_observation(tmp_path, monkeypatch):
    path = tmp_path / "changed.sqlite"
    with Collection(path) as store, sqlite3.connect(path) as external:
        gid = game(store, run(store))
        first = Snapshot(moves=["b0c2"])
        second = Snapshot(moves=["b0c2", "b9c7"])
        store.append(gid, first, actor_nodes=3)
        inspect = store.inspect

        def change_after_read(snapshot):
            value = inspect(snapshot)
            # Direct SQL can ignore the advisory writer lock; the write guard still protects it.
            with external:
                external.execute(
                    "UPDATE games SET payload=jsonb_set(payload,'$.themes',jsonb('[\"external\"]')) WHERE id=?", (gid,)
                )
            return value

        monkeypatch.setattr(store, "inspect", change_after_read)
        with pytest.raises(ValueError, match="unchanged running"):
            store.append(gid, second, actor_nodes=5)
        assert store.game(gid).snapshot == first and store.game(gid).themes == ["external"]
        monkeypatch.setattr(store, "inspect", inspect)
        store.append(gid, second, actor_nodes=5)
        assert store.game(gid).actor_nodes == 8 and store.game(gid).themes == ["external"]


def test_candidate_payload_retains_bounds_and_unknown_coverage(tiny_dataset):
    from qi.training_data.candidate_evidence import parse_candidates

    answer = tiny_dataset.labels[0].analysis.model_copy(deep=True)
    answer.search_info = [f"info depth 3 multipv 1 score cp 12 lowerbound wdl 400 400 200 pv {answer.move}"]
    parsed = parse_candidates(answer)
    assert parsed[0].score.bound == "lowerbound" and parsed[0].wdl == [400, 400, 200]
    answer.search_info = ["info depth 3 score cp 1 pv a0a9"]
    with pytest.raises(ValueError, match="Malformed candidate"):
        parse_candidates(answer)


def test_sql_bucket_priority_and_hash_tampering(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        import_json(store, source)
        selection = recipe(store, tiny_dataset.reserved_corpus)
        selection.buckets.insert(1, SnapshotBucket(id="later", split="train", count=1))
        with pytest.raises(ValueError, match="quotas"):
            export_snapshot(store, selection, tmp_path / "overlap")
        saved = json.loads((tmp_path / "overlap.pending/manifest.json").read_text())
        assert saved["actual"]["later"] == 0
        export_snapshot(store, recipe(store, tiny_dataset.reserved_corpus), tmp_path / "snapshot")
    manifest = json.loads((tmp_path / "snapshot/manifest.json").read_text())
    shard = tmp_path / "snapshot" / manifest["shards"][0]
    with shard.open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        SnapshotReader(tmp_path / "snapshot")


def test_label_failure_resume_keeps_completed_trajectory(tmp_path, data_setup):
    from qi.training_data.collection_generation import analyze_occurrence

    _, _, teacher, labeler, _ = data_setup
    path = tmp_path / "s.sqlite"
    with Collection(path) as store:
        rid = run(store)
        gid = game(store, rid)
        snap = Snapshot(moves=["b0c2"])
        store.append(gid, snap)
        oid = store.occurrence(gid, snap)
        store.finish_game(gid, "ply-budget")
        answer = labeler(restore(snap), teacher)
        spec = AnalysisSpec.from_analysis(answer)

        def failing(game, config):
            raise RuntimeError("teacher failed")

        with pytest.raises(RuntimeError, match="teacher failed"):
            analyze_occurrence(store, oid, teacher, spec, failing)
    with Collection(path) as store:
        assert game(store, rid) is None
        analyze_occurrence(store, oid, teacher, spec, labeler)
        assert [r[0] for r in store.db.execute("SELECT status FROM analyses ORDER BY id")] == ["failed", "success"]
        assert store.counts()["games"] == 1


def test_library_import_preserves_curated_phase_and_method(tmp_path, data_setup):
    from qi.training_data.generation import generate_library

    settings, corpus, teacher, labeler, _ = data_setup
    settings.sources = [settings.sources[2]]
    settings.sources[0].samples = 8
    settings.sources[0].start.curated_phase = "unknown"
    settings.sources[0].start.phase_authority = "fixture-authority"
    library = generate_library(settings, corpus, teacher, labeler=labeler)
    source = tmp_path / "library.json"
    source.write_text(library.model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        import_json(store, source)
        row = store.db.execute(
            "SELECT phase,json_extract(payload,'$.phase_method') FROM position_occurrences ORDER BY ply_count LIMIT 1"
        ).fetchone()
        assert tuple(row) == ("unknown", "curated:fixture-authority")
        assert store.counts()["analyses"] == len(library.examples)


def test_writer_alias_cannot_interrupt_live_game(tmp_path):
    path = tmp_path / "store.sqlite"
    with Collection(path) as store:
        gid = game(store, run(store))
        alias = tmp_path / "alias.sqlite"
        alias.symlink_to(path)
        with pytest.raises(ValueError, match="writer"):
            Collection(alias)
        store.append(gid, Snapshot(moves=["b0c2"]))
        assert store.db.execute("SELECT status FROM games WHERE id=?", (gid,)).fetchone()[0] == "running"


def test_snapshot_rejects_rehashed_ineligible_recipe(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    from qi.training_data.contracts import fingerprint

    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        import_json(store, source)
        export_snapshot(store, recipe(store, tiny_dataset.reserved_corpus), tmp_path / "snapshot")
    path = tmp_path / "snapshot/manifest.json"
    manifest = json.loads(path.read_text())
    for bucket in manifest["recipe"]["buckets"]:
        bucket["phases"] = []
    manifest.pop("fingerprint")
    manifest["fingerprint"] = fingerprint("parquet-manifest-v1", manifest)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="selection recipe"):
        verify_snapshot(tmp_path / "snapshot")


def test_legacy_preserves_generation_seed_and_rejects_new_origins(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    from qi.training_data.compatibility import legacy_source
    from qi.training_data.v1 import Dataset

    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_copy(update={"seed": 123}).model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        imported = import_json(store, source)
        selected = recipe(store, tiny_dataset.reserved_corpus)
        selected.seed = 987
        export_snapshot(store, selected, tmp_path / "snapshot")
        gid = game(store, run(store), "new-policy")
        with pytest.raises(ValueError, match="generator"):
            legacy_source(store, gid)
    receipt = export_legacy(tmp_path / "snapshot", tmp_path / "legacy.json")
    assert Dataset.model_validate_json((tmp_path / "legacy.json").read_text()).seed == 123
    assert receipt["parent_digests"] == [imported["parent_digest"]]
