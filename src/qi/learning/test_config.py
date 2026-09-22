"""Recipes remain copyable and cannot hide ignored settings."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from qi.cli import app
from qi.learning.config import Recipe, load_recipe
from qi.learning.runs import preview_recipe, summarize_cases


def test_cases_expand_independently_and_keep_the_same_holdout(tiny_dataset):
    recipe = Recipe.model_validate(
        {
            "data": {"dataset": "dataset.json"},
            "cases": [
                {"name": "small", "overrides": {"data": {"train_size": 3}}},
                {"name": "larger", "overrides": {"data": {"train_size": 6}, "optimizer": {"learning_rate": 0.003}}},
            ],
            "seeds": [7, 17],
        }
    )
    manifest = preview_recipe(recipe, tiny_dataset)
    trials = manifest["trials"]
    assert len(trials) == 4
    assert [trial["config"]["training"]["seed"] for trial in trials] == [7, 17, 7, 17]
    assert trials[0]["train_inputs"] == trials[1]["train_inputs"] == trials[2]["train_inputs"][:3]
    assert trials[0]["config"]["optimizer"]["learning_rate"] == 0.01
    assert trials[2]["config"]["optimizer"]["learning_rate"] == 0.003
    assert not set(trials[2]["train_inputs"]) & set(manifest["validation_inputs"])


@pytest.mark.parametrize(
    "seed,indices",
    [(7, [7, 2, 4, 6, 1, 3, 8, 0, 5]), (8, [7, 5, 2, 6, 4, 1, 8, 3, 0]), (-1, [4, 6, 0, 3, 7, 1, 5, 8, 2])],
)
def test_curve_input_order_matches_pre_migration_selection(tiny_dataset, seed, indices):
    # These index orders were captured from the retired curve adapter before migration.
    source_order = [label.input_sha256 for label in tiny_dataset.split_labels("train")]
    recipe = Recipe.model_validate(
        {
            "data": {"dataset": "dataset.json", "subset_seed": seed},
            "cases": [{"name": f"size-{size}", "overrides": {"data": {"train_size": size}}} for size in (3, 6, 9)],
            "seeds": [7, 17, 27],
        }
    )
    manifest = preview_recipe(recipe, tiny_dataset)
    assert manifest["planned_trials"] == 9
    expected = [source_order[index] for index in indices]
    sources = {label.input_sha256: label.source_id for label in tiny_dataset.labels}
    assert len({sources[key] for key in expected[:3]}) == 3
    for trial in manifest["trials"]:
        assert trial["train_inputs"] == expected[: trial["config"]["data"]["train_size"]]
        assert not set(trial["train_inputs"]) & set(manifest["validation_inputs"])
    assert manifest["reserved_corpus_sha256"] == tiny_dataset.reserved_corpus.digest
    assert "plan" not in manifest and "ordered_train_inputs" not in manifest


def test_source_order_and_insufficient_data_preserve_recipe_contract(tiny_dataset):
    from qi_game.core import GameError

    recipe = Recipe.model_validate({"data": {"dataset": "dataset.json", "selection": "source-order", "train_size": 3}})
    assert recipe.training_inputs(tiny_dataset) == [
        label.input_sha256 for label in tiny_dataset.split_labels("train")[:3]
    ]
    recipe.data.train_size = 100
    with pytest.raises(GameError, match="dataset has"):
        preview_recipe(recipe, tiny_dataset)


@pytest.mark.parametrize(
    "patch",
    [
        {"optimizer": {"learn_rate": 0.02}},
        {"model": {"architecture": "imaginary-model"}},
        {"training": {"precision": "float16"}},
        {"execution": {"fit_seconds": float("nan")}},
        {"seeds": [1, 1]},
        {"cases": [{"name": "../escape"}]},
        {"cases": [{"name": "a", "overrides": {"training": {"seed": 17}}}]},
        {"cases": [{"name": "a", "overrides": {"data": {"dataset": "other.json"}}}]},
        {"cases": [{"name": "a", "overrides": {"optimizer": {"typo": 1}}}]},
        {"schema_version": 2},
    ],
)
def test_invalid_or_unsupported_settings_fail(patch):
    with pytest.raises(ValidationError):
        Recipe.model_validate({"data": {"dataset": "dataset.json"}, **patch})


def test_preview_reads_paths_relative_to_config_and_rejects_cli_overrides(tiny_dataset, tmp_path):
    (tmp_path / "dataset.json").write_text(tiny_dataset.model_dump_json())
    config = tmp_path / "recipe.json"
    config.write_text(json.dumps({"data": {"dataset": "dataset.json"}}))
    before = set(tmp_path.iterdir())
    assert load_recipe(config).data.dataset == str(tmp_path / "dataset.json")
    result = CliRunner().invoke(app, ["learn", "run", "--config", str(config), "--preview"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["planned_trials"] == 1
    without_trainer = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['torch'] = None; from qi.cli import main; main()",
            "learn",
            "run",
            "--config",
            str(config),
            "--preview",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(without_trainer.stdout) == json.loads(result.stdout)
    rejected = CliRunner().invoke(app, ["learn", "run", "--config", str(config), "--seed", "17", "--preview"])
    assert rejected.exit_code != 0
    assert set(tmp_path.iterdir()) == before


def test_partial_case_has_no_aggregate():
    planned = [{"case": "a"}, {"case": "a"}, {"case": "b"}]
    trials = [{"case": "a", "report": {"status": "deadline"}}]
    assert summarize_cases(trials, planned) == [
        {"case": "a", "complete_seeds": 0, "expected_seeds": 2},
        {"case": "b", "complete_seeds": 0, "expected_seeds": 1},
    ]


def test_case_names_cannot_collide_on_case_insensitive_filesystems():
    with pytest.raises(ValidationError, match="case-insensitive"):
        Recipe.model_validate({"data": {"dataset": "data.json"}, "cases": [{"name": "Control"}, {"name": "control"}]})


def test_seed_aliases_are_not_independent_initializations():
    with pytest.raises(ValidationError, match="distinct PyTorch"):
        Recipe.model_validate({"data": {"dataset": "data.json"}, "seeds": [-1, 2**64 - 1]})
    recipe = Recipe.model_validate({"data": {"dataset": "data.json", "subset_seed": -1}, "training": {"seed": -1}})
    assert recipe.expand()[0][1].training.seed == -1


def test_historical_ancestry_resolves_from_config_location(tmp_path):
    folder = tmp_path / "recipes"
    folder.mkdir()
    original = tmp_path / "manifest.json"
    original.write_text("{}")
    path = folder / "historical.json"
    path.write_text(json.dumps({"data": {"dataset": "../dataset.json"}, "derived_from": "../manifest.json"}))
    recipe = load_recipe(path)
    assert recipe.derived_from == str(original)
    assert Path(recipe.derived_from).is_file()
