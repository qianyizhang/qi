"""Optional bounded snapshot-to-tensor parity; optimizer semantics stay unchanged."""

import pytest

pytest.importorskip("torch")
pytest.importorskip("pyarrow")

from qi.learning.train import tensors
from qi.training_data.compatibility import import_json
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, SnapshotReader, export_snapshot
from qi.training_data.store import Collection


def test_snapshot_batches_prepare_identical_tensors(tmp_path, tiny_dataset):
    import torch

    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_dump_json())
    with Collection(tmp_path / "s.sqlite") as store:
        import_json(store, source)
        spec = store.db.execute("SELECT identity FROM analysis_specs LIMIT 1").fetchone()[0]
        recipe = SelectionRecipe(
            analysis_spec=spec,
            reserved_corpus=tiny_dataset.reserved_corpus,
            buckets=[SnapshotBucket(id=s, split=s, count=2) for s in ("train", "validation")],
        )
        export_snapshot(store, recipe, tmp_path / "snapshot", shard_rows=2)
    originals = {label.input_sha256: label for label in tiny_dataset.labels}
    for labels in SnapshotReader(tmp_path / "snapshot").label_batches(1):
        expected = tensors([originals[label.input_sha256] for label in labels])
        actual = tensors(labels)
        assert all(torch.equal(a, b) for a, b in zip(expected, actual, strict=True))
