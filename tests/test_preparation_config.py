"""Preparation configs pin generation inputs and preserve incomplete evidence."""

import json

import pytest
from typer.testing import CliRunner

from qi.cli import app
from qi.game import GameError
from qi.training_data.assembly import Bucket, MixtureRecipe
from qi.training_data.config import PreparationConfig, SupervisionSettings, load_preparation, prepare_dataset
from qi.training_data.contracts import fingerprint
from qi.training_data.generation import teacher_spec
from qi.training_data.loading import load_dataset


@pytest.fixture
def preparation(data_setup, tmp_path):
    recipe, corpus, teacher, labeler, calls = data_setup
    path = tmp_path / "corpus.json"
    path.write_text(corpus.model_dump_json())
    spec = teacher_spec(teacher)
    config = PreparationConfig(
        corpus="corpus.json",
        corpus_sha256=corpus.digest,
        generation=recipe,
        supervision=SupervisionSettings(
            engine="fake-engine",
            network="fake-network",
            engine_sha256=spec["engine_sha256"],
            network_sha256=spec["network_sha256"],
            nodes=teacher.nodes,
            depth=teacher.depth,
        ),
        assembly=MixtureRecipe(
            id="configured-mixture",
            supervision_fingerprint=fingerprint("supervision-v1", spec),
            buckets=[
                Bucket(id=f"{mode}-{split}", modes=[mode], split=split, count=2)
                for mode in ("random", "teacher-guided")
                for split in ("train", "validation")
            ],
        ),
    )
    config_path = tmp_path / "preparation.json"
    config_path.write_text(config.model_dump_json())
    return load_preparation(config_path), labeler, calls


def test_saved_config_runs_both_modes_and_can_be_copied(preparation, tmp_path):
    config, labeler, _ = preparation
    output = tmp_path / "prepared"
    result = prepare_dataset(config, output, labeler=labeler)
    assert result["status"] == "complete"
    dataset = load_dataset(output / "dataset.json")
    assert len(dataset.labels) == 8
    assert {source.actor_spec["mode"] for source in dataset.library.sources} == {"random", "teacher-guided"}
    copied = load_preparation(output / "config.json")
    assert copied == config
    second = prepare_dataset(copied, tmp_path / "copy", labeler=labeler)
    assert second["dataset_manifest_fingerprint"] == result["dataset_manifest_fingerprint"]
    before = (output / "dataset.json").read_bytes()
    with pytest.raises(GameError, match="fresh"):
        prepare_dataset(config, output, labeler=labeler)
    assert (output / "dataset.json").read_bytes() == before


@pytest.mark.parametrize(
    "field,code",
    [
        ("engine_sha256", "teacher_mismatch"),
        ("corpus_sha256", "corpus_mismatch"),
        ("supervision_fingerprint", "supervision_mismatch"),
    ],
)
def test_wrong_pins_fail_before_generation(preparation, tmp_path, field, code):
    config, labeler, calls = preparation
    target = (
        config
        if field == "corpus_sha256"
        else (config.assembly if field == "supervision_fingerprint" else config.supervision)
    )
    setattr(target, field, "0" * 64)
    output = tmp_path / "refused"
    with pytest.raises(GameError) as error:
        prepare_dataset(config, output, labeler=labeler)
    assert error.value.code == code
    assert not output.exists() and not calls


def test_actor_teacher_budget_is_independent_of_supervision(preparation, tmp_path):
    config, labeler, calls = preparation
    config.actor_teacher = config.supervision.model_copy(update={"nodes": 101})
    result = prepare_dataset(config, tmp_path / "separate", labeler=labeler)
    assert result["status"] == "complete"
    dataset = load_dataset(tmp_path / "separate" / "dataset.json")
    assert {nodes for _, nodes in calls} == {100, 101}
    assert {example.analysis.requested_nodes for example in dataset.library.examples} == {100}


def test_partial_generation_and_quota_shortfall_are_retained(preparation, tmp_path):
    config, labeler, _ = preparation

    def failing(game, teacher):
        raise GameError("teacher_timeout", "bounded failure")

    output = tmp_path / "partial"
    result = prepare_dataset(config, output, labeler=failing)
    assert result["status"] == result["generation_status"] == "incomplete"
    assert (output / "library.json").exists() and not (output / "dataset.json").exists()
    assert "bounded failure" in json.loads((output / "summary.json").read_text())["failure"]
    config.assembly.buckets[0].count = 100
    quota_output = tmp_path / "shortfall"
    result = prepare_dataset(config, quota_output, labeler=labeler)
    assert result["status"] == "incomplete" and result["generation_status"] == "complete"
    with pytest.raises(ValueError, match="Incomplete mixture"):
        load_dataset(quota_output / "dataset.json")


def test_prepare_cli_uses_saved_config_and_reports_incompleteness(preparation, tmp_path, monkeypatch):
    config, labeler, _ = preparation
    path = tmp_path / "submitted.json"
    path.write_text(config.model_dump_json())
    monkeypatch.setattr(
        "qi.training_data.cli.prepare_dataset", lambda config, output: prepare_dataset(config, output, labeler=labeler)
    )
    result = CliRunner().invoke(app, ["data", "prepare", "--config", str(path), "--output", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "complete"
    config.assembly.buckets[0].count = 100
    path.write_text(config.model_dump_json())
    result = CliRunner().invoke(app, ["data", "prepare", "--config", str(path), "--output", str(tmp_path / "short")])
    assert getattr(result.exception, "code", None) == "preparation_incomplete"
