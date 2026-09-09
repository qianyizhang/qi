"""Configured training shares the existing optimizer and survives copy/edit/rerun."""

import importlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytest.importorskip("torch")

from qi.cli import app
from qi.game import GameError
from qi.learning.config import Recipe, load_recipe
from qi.learning.runs import run_recipe
from qi.learning.train import train
from qi.players.policy.runtime import load_checkpoint


def test_saved_config_can_be_copied_tweaked_and_replayed(tiny_dataset, tmp_path):
    recipe = Recipe.model_validate(
        {
            "data": {"dataset": "unused.json", "train_size": 3},
            "training": {"updates": 2},
        }
    )
    first = tmp_path / "first"
    result = run_recipe(recipe, tiny_dataset, first, source_config=tmp_path / "recipe.json")
    saved = first / result["trials"][0]["config"]
    config = load_recipe(saved)
    assert config.data.dataset == str(first / "dataset.json")
    assert config.training.updates == 2
    direct = train(tiny_dataset, tmp_path / "direct.pt", steps=2, train_inputs=config.training_inputs(tiny_dataset))
    expected = load_checkpoint(direct["checkpoint"])
    actual = load_checkpoint(result["trials"][0]["report"]["checkpoint"])
    for key, value in expected.model.state_dict().items():
        assert value.equal(actual.model.state_dict()[key])
    copied = json.loads(saved.read_text())
    copied["optimizer"]["learning_rate"] = 0.003
    copy_path = tmp_path / "tweaked.json"
    copy_path.write_text(json.dumps(copied))
    execution = CliRunner().invoke(
        app, ["learn", "run", "--config", str(copy_path), "--output", str(tmp_path / "second")]
    )
    assert execution.exit_code == 0, execution.output
    second = json.loads(execution.stdout)
    report = second["trials"][0]["report"]
    assert report["metadata"]["learning_rate"] == 0.003
    assert report["metadata"]["train_inputs"] == direct["metadata"]["train_inputs"]
    assert json.loads((tmp_path / "second/config.json").read_text())["derived_from"] == str(saved)
    assert json.loads((tmp_path / "second/config.json").read_text())["origin_config"] == str(
        tmp_path / "second/config.json"
    )
    with pytest.raises(GameError, match="fresh experiment"):
        run_recipe(recipe, tiny_dataset, first, source_config=copy_path)


@pytest.mark.parametrize("stop", ["deadline", "failure", "interrupt"])
def test_configured_runs_preserve_partial_evidence(tiny_dataset, tmp_path, monkeypatch, stop):
    runs = importlib.import_module("qi.learning.runs")
    trainer = importlib.import_module("qi.learning.train")
    recipe = Recipe.model_validate({"data": {"dataset": "unused.json"}, "seeds": [7, 17]})
    clock = [0.0]
    monkeypatch.setattr(runs, "perf_counter", lambda: clock[0])
    calls = []

    def interrupted_train(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            if stop == "interrupt":
                raise KeyboardInterrupt()
            raise GameError("test_failure", "test failure")
        if stop == "deadline":
            clock[0] = 601.0
        return {"status": "complete"}

    monkeypatch.setattr(trainer, "train", interrupted_train)
    output = tmp_path / "partial"
    if stop == "deadline":
        run_recipe(recipe, tiny_dataset, output, source_config=tmp_path / "recipe.json")
    else:
        with pytest.raises(KeyboardInterrupt if stop == "interrupt" else GameError):
            run_recipe(recipe, tiny_dataset, output, source_config=tmp_path / "recipe.json")
    summary = json.loads((output / "summary.json").read_text())
    assert summary["status"] == {"deadline": "deadline", "failure": "failed", "interrupt": "interrupted"}[stop]
    assert summary["cases"] == [{"case": "policy", "complete_seeds": 1, "expected_seeds": 2}]
    assert (output / "policy-seed-7.config.json").is_file()


def test_configured_run_accepts_complete_frozen_data_and_rejects_shortfalls(tiny_dataset, tmp_path):
    from qi.game import legal_moves
    from qi.protocol import Snapshot
    from qi.teacher import TeacherConfig
    from qi.training_data.assembly import Bucket, MixtureRecipe, assemble
    from qi.training_data.contracts import GenerationRecipe, SourcePlan, StartingPosition
    from qi.training_data.generation import generate_library, teacher_spec
    from qi.training_data.loading import load_dataset

    teacher = TeacherConfig(tmp_path / "fake-engine", tmp_path / "fake-network")
    spec = teacher_spec(teacher)

    def labeler(game, config):
        return tiny_dataset.labels[0].analysis.model_copy(
            update={
                "snapshot": Snapshot(moves=list(game.moves)),
                "state_hash": game.state_hash,
                "move": sorted(legal_moves(game.board, game.turn))[0],
                "engine_sha256": spec["engine_sha256"],
                "network_sha256": spec["network_sha256"],
                "settings": spec["settings"],
            }
        )

    library = generate_library(
        GenerationRecipe(
            id="config-fixture",
            sources=[
                SourcePlan(
                    id=split,
                    mode="random",
                    split=split,
                    start=StartingPosition(id="initial", version="1"),
                    additional_plies=8,
                    samples=3,
                )
                for split in ("train", "validation")
            ],
        ),
        tiny_dataset.reserved_corpus,
        teacher,
        labeler=labeler,
    )
    mixture = MixtureRecipe(
        id="config-fixture",
        supervision_fingerprint=library.examples[0].supervision_fingerprint,
        buckets=[Bucket(id=split, split=split, count=2) for split in ("train", "validation")],
    )
    dataset = assemble(library, mixture)
    path = tmp_path / "frozen.json"
    path.write_text(dataset.model_dump_json())
    recipe = Recipe.model_validate({"data": {"dataset": str(path)}, "training": {"updates": 2}})
    result = run_recipe(recipe, load_dataset(path), tmp_path / "frozen-run", source_config=tmp_path / "recipe.json")
    assert result["status"] == "complete"
    assert result["trials"][0]["report"]["slices"]
    saved = load_recipe(tmp_path / "frozen-run/config.json")
    assert load_dataset(Path(saved.data.dataset)).manifest == dataset.manifest
    mixture.buckets[0].count = 100
    path.write_text(assemble(library, mixture).model_dump_json())
    with pytest.raises(ValueError, match="Incomplete mixture"):
        load_dataset(path)


def test_legacy_preflight_allows_retry_and_preserves_negative_seed(tiny_dataset, tmp_path, monkeypatch):
    trainer = importlib.import_module("qi.learning.train")
    data = tmp_path / "data.json"
    data.write_text(tiny_dataset.model_dump_json())
    checkpoint = tmp_path / "policy.pt"
    config = tmp_path / "policy.pt.config.json"
    args = ["learn", "train", "--data", str(data), "--checkpoint", str(checkpoint), "--steps", "1", "--seed", "-1"]

    def unavailable(*args):
        raise GameError("mps_unavailable", "fixture device unavailable")

    with monkeypatch.context() as context:
        context.setattr(trainer, "validate_device", unavailable)
        assert CliRunner().invoke(app, args).exit_code != 0
    assert not checkpoint.exists() and not config.exists()
    retry = CliRunner().invoke(app, args)
    assert retry.exit_code == 0, retry.output
    assert load_recipe(config).training.seed == json.loads(retry.stdout)["metadata"]["seed"] == -1
    other = tmp_path / "policy.pth"
    args[args.index(str(checkpoint))] = str(other)
    assert CliRunner().invoke(app, args).exit_code == 0
    assert (tmp_path / "policy.pth.config.json").exists()


def test_legacy_negative_subset_seed_uses_the_shared_executor(tiny_dataset, tmp_path):
    from qi.learning.experiment import LearningPlan, ordered_inputs, run_experiment

    result = run_experiment(
        tiny_dataset,
        tiny_dataset.reserved_corpus,
        LearningPlan(sizes=[3], seeds=[7], subset_seed=-1, steps=1),
        tmp_path / "negative-subset",
    )
    assert result["trials"][0]["report"]["metadata"]["train_inputs"] == ordered_inputs(tiny_dataset, -1)[:3]
