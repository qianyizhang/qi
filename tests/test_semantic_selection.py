"""Versioned input decisions must survive independent frozen-snapshot verification."""

import json

import pytest

from qi.training_data.compatibility import import_json
from qi.training_data.contracts import fingerprint
from qi.training_data.semantics import semantic_tags
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, export_snapshot, verify_snapshot
from qi.training_data.store import Collection


def test_v2_explicit_selection_exclusions_and_tampered_predicate(tmp_path, tiny_dataset):
    pytest.importorskip("pyarrow")
    source = tmp_path / "data.json"
    source.write_text(tiny_dataset.model_dump_json())
    training = tiny_dataset.split_labels("train")
    validation = tiny_dataset.split_labels("validation")
    excluded = training[0].input_sha256
    wanted = training[1]
    with Collection(tmp_path / "collection.sqlite") as store:
        import_json(store, source)
        spec = store.db.execute("SELECT identity FROM analysis_specs LIMIT 1").fetchone()[0]
        buckets = [
            SnapshotBucket(id="train", split="train", count=1, inputs=[wanted.input_sha256]),
            SnapshotBucket(id="validation", split="validation", count=1, inputs=[validation[0].input_sha256]),
        ]
        with pytest.raises(ValueError, match="require sql-selection-v2"):
            SelectionRecipe(analysis_spec=spec, reserved_corpus=tiny_dataset.reserved_corpus, buckets=buckets)
        recipe = SelectionRecipe(
            version="sql-selection-v2",
            analysis_spec=spec,
            reserved_corpus=tiny_dataset.reserved_corpus,
            buckets=buckets,
            excluded_inputs={excluded: "held-out overlap"},
        )
        export_snapshot(store, recipe, tmp_path / "snapshot")
    assert verify_snapshot(tmp_path / "snapshot")["rows"] == 2
    path = tmp_path / "snapshot/manifest.json"
    manifest = json.loads(path.read_text())
    game = wanted.analysis.snapshot.game()
    absent = next(
        t
        for t in ["in-check", "teacher-capture", "teacher-gives-check"]
        if t not in semantic_tags(game.board, game.turn, wanted.analysis.move)
    )
    manifest["recipe"]["buckets"][0]["semantic_tags"] = [absent]
    manifest.pop("fingerprint")
    manifest["fingerprint"] = fingerprint("parquet-manifest-v1", manifest)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match=r"violates selection recipe|count mismatch"):
        verify_snapshot(tmp_path / "snapshot")
