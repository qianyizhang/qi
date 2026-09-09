"""Frozen training data crosses the CLI and optional torch boundary faithfully."""

import json

import pytest
from typer.testing import CliRunner

from qi.cli import app
from qi.training_data.assembly import assemble
from qi.training_data.test_pipeline import data_setup, library, mixture  # noqa: F401


def test_cli_assembly_writes_complete_and_incomplete_manifests(library, tmp_path):  # noqa: F811
    source, recipe, output = (tmp_path / name for name in ("library.json", "mixture.json", "dataset.json"))
    source.write_text(library.model_dump_json())
    settings = mixture(library)
    recipe.write_text(settings.model_dump_json())
    runner = CliRunner()
    args = ["data", "assemble", "--library", str(source), "--recipe", str(recipe), "--output", str(output)]
    assert runner.invoke(app, args).exit_code == 0
    assert json.loads(output.read_text())["manifest"]["status"] == "complete"
    assert runner.invoke(app, args).exit_code != 0
    settings.buckets[0].count = 100
    recipe.write_text(settings.model_dump_json())
    partial = tmp_path / "partial.json"
    assert runner.invoke(app, [*args[:-1], str(partial)]).exit_code != 0
    assert json.loads(partial.read_text())["manifest"]["status"] == "incomplete"


def test_manifest_training_checkpoint_and_slice_results(library, tmp_path):  # noqa: F811
    pytest.importorskip("torch")
    from qi.learning.train import train
    from qi.players.policy.runtime import load_checkpoint

    dataset = assemble(library, mixture(library))
    path = tmp_path / "policy.pt"
    result = train(dataset, path, steps=3, seconds=20)
    metadata = load_checkpoint(str(path.resolve())).metadata
    assert result["reload_predictions_equal"]
    assert metadata.dataset_manifest_fingerprint == dataset.manifest.fingerprint
    assert metadata.dataset_sha256 == dataset.digest
    assert metadata.validation_inputs == [label.input_sha256 for label in dataset.split_labels("validation")]
    assert result["slices"]["validation/bucket:teacher-guided-validation"]["positions"] == 2
    assert result["slices"]["train/bucket:random-train"]["legal_outputs"] == 2
    settings = mixture(library, 100)
    partial = assemble(library, settings)
    with pytest.raises(ValueError, match="Incomplete mixture"):
        train(partial, tmp_path / "refused.pt", steps=1)
    assert not (tmp_path / "refused.pt").exists()
