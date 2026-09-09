"""Frozen training data crosses the CLI and optional torch boundary faithfully."""

import json

import pytest
from typer.testing import CliRunner

from qi.cli import app
from qi.training_data.assembly import Bucket, MixtureRecipe, assemble


@pytest.fixture
def mixture_recipe(library):
    return MixtureRecipe(
        id="integration",
        supervision_fingerprint=library.examples[0].supervision_fingerprint,
        buckets=[
            Bucket(id=f"{mode}-{split}", modes=[mode], split=split, count=2)
            for mode in ("random", "teacher-guided")
            for split in ("train", "validation")
        ],
    )


def test_cli_assembly_writes_complete_and_incomplete_manifests(library, mixture_recipe, tmp_path):
    source, recipe, output = (tmp_path / name for name in ("library.json", "mixture.json", "dataset.json"))
    source.write_text(library.model_dump_json())
    settings = mixture_recipe
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


def test_manifest_training_checkpoint_and_slice_results(library, mixture_recipe, tmp_path):
    pytest.importorskip("torch")
    from qi.learning.train import train
    from qi.players.policy.runtime import load_checkpoint

    dataset = assemble(library, mixture_recipe)
    path = tmp_path / "policy.pt"
    result = train(dataset, path, steps=3, seconds=20)
    metadata = load_checkpoint(str(path.resolve())).metadata
    assert result["reload_predictions_equal"]
    assert metadata.dataset_manifest_fingerprint == dataset.manifest.fingerprint
    assert metadata.dataset_sha256 == dataset.digest
    assert metadata.validation_inputs == [label.input_sha256 for label in dataset.split_labels("validation")]
    assert result["slices"]["validation/bucket:teacher-guided-validation"]["positions"] == 2
    assert result["slices"]["train/bucket:random-train"]["legal_outputs"] == 2
    settings = mixture_recipe.model_copy(deep=True)
    settings.buckets[0].count = 100
    partial = assemble(library, settings)
    with pytest.raises(ValueError, match="Incomplete mixture"):
        train(partial, tmp_path / "refused.pt", steps=1)
    assert not (tmp_path / "refused.pt").exists()


def test_single_training_cli_accepts_frozen_data_and_saves_config_and_report(library, mixture_recipe, tmp_path):
    pytest.importorskip("torch")
    dataset = assemble(library, mixture_recipe)
    path, checkpoint = tmp_path / "dataset.json", tmp_path / "policy.pt"
    path.write_text(dataset.model_dump_json())
    result = CliRunner().invoke(
        app, ["learn", "train", "--data", str(path), "--checkpoint", str(checkpoint), "--steps", "2"]
    )
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "policy.pt.report.json").read_text())
    assert report["metadata"]["dataset_manifest_fingerprint"] == dataset.manifest.fingerprint
    assert report["reload_predictions_equal"]
    assert (tmp_path / "policy.pt.config.json").exists()


def test_training_deadline_saves_report_and_exits_nonzero(library, mixture_recipe, tmp_path, monkeypatch):
    pytest.importorskip("torch")
    path, checkpoint = tmp_path / "dataset.json", tmp_path / "partial.pt"
    path.write_text(assemble(library, mixture_recipe).model_dump_json())

    def deadline(dataset, checkpoint, **kwargs):
        checkpoint.write_bytes(b"test checkpoint")
        return {"status": "deadline", "completed_steps": 1, "requested_steps": kwargs["steps"]}

    monkeypatch.setattr("qi.learning.train.train", deadline)
    result = CliRunner().invoke(app, ["learn", "train", "--data", str(path), "--checkpoint", str(checkpoint)])
    assert result.exit_code != 0
    assert json.loads((tmp_path / "partial.pt.report.json").read_text())["status"] == "deadline"
    assert getattr(result.exception, "code", None) == "training_incomplete"


def test_existing_report_rejects_training_before_any_outputs(library, mixture_recipe, tmp_path):
    pytest.importorskip("torch")
    path = tmp_path / "dataset.json"
    path.write_text(assemble(library, mixture_recipe).model_dump_json())
    report = tmp_path / "policy.pt.report.json"
    report.write_text("preserved")
    result = CliRunner().invoke(
        app, ["learn", "train", "--data", str(path), "--checkpoint", str(tmp_path / "policy.pt")]
    )
    assert result.exit_code != 0
    assert report.read_text() == "preserved"
    assert not (tmp_path / "policy.pt").exists()
    assert not (tmp_path / "policy.pt.config.json").exists()


def test_obsolete_generation_recipe_fails_before_teacher_or_artifact_creation(data_setup, tmp_path):
    recipe, corpus, _, _, _ = data_setup
    recipe.version = "continuations-v1"
    path, reserved, output = tmp_path / "recipe.json", tmp_path / "corpus.json", tmp_path / "library.json"
    path.write_text(recipe.model_dump_json())
    reserved.write_text(corpus.model_dump_json())
    result = CliRunner().invoke(
        app,
        [
            "data",
            "generate",
            "--recipe",
            str(path),
            "--corpus",
            str(reserved),
            "--engine",
            "missing",
            "--network",
            "missing",
            "--output",
            str(output),
        ],
    )
    assert getattr(result.exception, "code", None) == "obsolete_recipe"
    assert not output.exists()
