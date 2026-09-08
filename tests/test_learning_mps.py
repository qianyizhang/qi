"""Explicit optional Metal lane; default tests never require a GPU."""

import os

import pytest

torch = pytest.importorskip("torch")
pytestmark = pytest.mark.skipif(
    os.environ.get("QI_TEST_MPS") != "1", reason="Run make test-learning-mps with Metal access."
)


def test_mps_fit_serializes_cpu_weights_and_preserves_reload(tiny_dataset, tmp_path):
    from qi.learning.train import train
    from qi.players.policy.runtime import load_checkpoint

    assert torch.backends.mps.is_available(), "The explicitly requested MPS lane needs GPU access."
    path = tmp_path / "metal.pt"
    report = train(tiny_dataset, path, device="mps", steps=100, diagnostic_examples=4)
    cpu = train(tiny_dataset, tmp_path / "cpu.pt", steps=100, diagnostic_examples=4)
    assert report["status"] == "complete" and report["training_device"] == "mps"
    assert report["train"]["agreement"] == 1
    assert report["reload_predictions_equal"]
    assert report["initial_loss"] == pytest.approx(cpu["initial_loss"], abs=1e-5)
    assert report["final_loss"] < report["initial_loss"] / 10
    loaded = load_checkpoint(str(path))
    assert loaded.metadata.training_device == "mps"
    assert all(weight.device.type == "cpu" for weight in loaded.model.parameters())
