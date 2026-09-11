"""Full-pass gradient/update parity and durable snapshot-to-checkpoint behavior."""

from copy import deepcopy
from time import perf_counter

import pytest

pytest.importorskip("torch")
pytest.importorskip("pyarrow")

import torch

from qi.learning.snapshot import (
    SnapshotConfig,
    SnapshotTensors,
    accumulated_step,
    prepare_snapshot,
    train_snapshot,
)
from qi.players.policy.runtime import load_checkpoint, make_model
from qi.training_data.compatibility import import_json
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, export_snapshot
from qi.training_data.store import Collection


def test_full_batch_gradient_and_adam_update_with_short_final_chunk():
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        torch.manual_seed(917)
        full = make_model()
        chunked = deepcopy(full)
        x = torch.randn(7, 1261)
        mask = torch.zeros(7, 8100, dtype=torch.bool)
        mask[:, :11] = True
        y = torch.arange(7)
        a = torch.optim.Adam(full.parameters(), lr=0.01)
        b = torch.optim.Adam(chunked.parameters(), lr=0.01)
        for _ in range(3):
            a.zero_grad()
            loss = torch.nn.functional.cross_entropy(full(x).masked_fill(~mask, -torch.inf), y)
            loss.backward()
            actual = accumulated_step(
                chunked, b, [(None, (x[i : i + 3], mask[i : i + 3], y[i : i + 3])) for i in range(0, 7, 3)], 7
            )
            assert actual == pytest.approx(float(loss.detach()), abs=2e-6)
            for left, right in zip(full.parameters(), chunked.parameters(), strict=True):
                torch.testing.assert_close(left.grad, right.grad, rtol=2e-4, atol=2e-6)
            a.step()
            for left, right in zip(full.parameters(), chunked.parameters(), strict=True):
                torch.testing.assert_close(left, right, rtol=2e-4, atol=2e-5)
        before = deepcopy(chunked.state_dict())

        def expired_pass():
            yield None, (x[:3], mask[:3], y[:3])

        assert accumulated_step(chunked, b, expired_pass(), 7, deadline=perf_counter() - 1) is None
        assert all(torch.equal(v, chunked.state_dict()[k]) for k, v in before.items())
    finally:
        torch.set_num_threads(old_threads)


def test_snapshot_fit_reload_and_cache_tampering(tmp_path, tiny_dataset):
    source = tmp_path / "source.json"
    source.write_text(tiny_dataset.model_dump_json())
    with Collection(tmp_path / "collection.sqlite") as store:
        import_json(store, source)
        recipe = SelectionRecipe(
            analysis_spec=store.db.execute("SELECT identity FROM analysis_specs LIMIT 1").fetchone()[0],
            reserved_corpus=tiny_dataset.reserved_corpus,
            buckets=[SnapshotBucket(id=s, split=s, count=2) for s in ["train", "validation"]],
        )
        export_snapshot(store, recipe, tmp_path / "snapshot")
    prepare_snapshot(tmp_path / "snapshot", tmp_path / "tensors", chunk_size=1)
    settings = SnapshotConfig.model_validate(
        {"data": {"snapshot": str(tmp_path / "snapshot")}, "training": {"updates": 3, "chunk_size": 1}}
    )
    report = train_snapshot(SnapshotTensors(tmp_path / "tensors"), settings, tmp_path / "fit")
    assert report["status"] == "complete"
    assert report["completed_updates"] == 3 and report["reload_predictions_equal"]
    assert report["stats"]["validation"]["positions"] == 2
    loaded = load_checkpoint(str(tmp_path / "fit/policy.pt"))
    assert loaded.metadata.training_protocol == "snapshot-full-batch-v1"
    assert loaded.metadata.dataset_manifest_fingerprint == report["snapshot_fingerprint"]
    with (tmp_path / "tensors/features.npy").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        SnapshotTensors(tmp_path / "tensors")
