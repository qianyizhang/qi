"""One bundled CPU reference run and a small check against its Mac baseline."""

import json
import math
from hashlib import sha256
from pathlib import Path

from qi_game.core import GameError

from qi.artifacts import digest, provenance, write_json
from qi.learning.config import Recipe, load_recipe
from qi.learning.runs import preview_recipe, run_recipe
from qi.training_data.loading import load_dataset

BUNDLE = Path(__file__).with_name("reference_data")


def recipe_identity(recipe: Recipe) -> str:
    values = recipe.model_dump(exclude={"origin_config", "derived_from"})
    values["data"].pop("dataset")
    return digest(values)


def verify_reference(output: Path) -> dict:
    """Check retained inputs, settings, checkpoint and metrics; retain failures too."""
    from qi.learning.train import measure
    from qi.players.policy.runtime import load_checkpoint

    expected = json.loads((BUNDLE / "expected.json").read_text())
    checks, metrics = {}, {}
    result = {"reference": expected["reference"], "checks": checks, "metrics": metrics, "runtime": provenance()}
    try:
        recipe = load_recipe(output / "config.json")
        dataset = load_dataset(output / "dataset.json")
        manifest = json.loads((output / "manifest.json").read_text())
        summary = json.loads((output / "summary.json").read_text())
        checks["dataset_identity"] = dataset.digest == expected["dataset_sha256"] == manifest["dataset_sha256"]
        checks["recipe_identity"] = recipe_identity(recipe) == expected["recipe_sha256"]
        checks["complete"] = summary["status"] == "complete" and len(summary["trials"]) == 1
        trial = summary["trials"][0]
        report = trial["report"]
        name = f"{trial['case']}-seed-{trial['seed']}"
        checks["saved_report"] = json.loads((output / f"{name}.json").read_text()) == report
        concrete = load_recipe(output / trial["config"])
        checks["trial_recipe"] = recipe_identity(concrete) == recipe_identity(recipe)
        checkpoint = output / f"{name}.pt"
        # The inference loader is process-pinned; verification must inspect current bytes.
        checks["checkpoint_bytes"] = sha256(checkpoint.read_bytes()).hexdigest() == report["checkpoint_sha256"]
        policy = load_checkpoint(str(checkpoint.resolve()), report["checkpoint_sha256"])
        metadata = policy.metadata.model_dump()
        checks["checkpoint_metadata"] = metadata == report["metadata"]
        checks["checkpoint_dataset"] = metadata["dataset_sha256"] == dataset.digest
        checks["checkpoint_settings"] = (
            metadata["seed"] == recipe.training.seed
            and metadata["learning_rate"] == recipe.optimizer.learning_rate
            and metadata["reserved_corpus_sha256"] == dataset.reserved_corpus.digest
        )
        checks["splits"] = (
            metadata["train_inputs"] == recipe.training_inputs(dataset)
            and metadata["validation_inputs"]
            == manifest["validation_inputs"]
            == [label.input_sha256 for label in dataset.split_labels("validation")]
            and manifest["trials"][0]["train_inputs"] == metadata["train_inputs"]
        )
        checks["updates"] = report["completed_steps"] == metadata["steps"] == recipe.training.updates
        checks["cpu"] = metadata["training_device"] == "cpu" and metadata["training_threads"] == 1
        checks["reload"] = report["reload_predictions_equal"] is True
        checks["overfit"] = report["train"]["agreement"] == 1 and report["final_loss"] < report["initial_loss"] / 10
        measured = {split: measure(policy, dataset.split_labels(split))[0] for split in ("train", "validation")}
        for split, stats in measured.items():
            checks[f"{split}_legal"] = stats["legal_outputs"] == stats["positions"] == report[split]["positions"]
        for key, target in expected["metrics"].items():
            parts = key.split(".")
            actual = report[parts[0]] if len(parts) == 1 else measured[parts[0]][parts[1]]
            metrics[key] = {"actual": actual, **target}
            checks[key] = math.isclose(
                actual, target["expected"], rel_tol=target["relative_tolerance"], abs_tol=target["absolute_tolerance"]
            )
            if len(parts) == 2:
                checks[f"{key}_report"] = math.isclose(actual, report[parts[0]][parts[1]], rel_tol=1e-5, abs_tol=1e-6)
    except (OSError, ValueError, KeyError, IndexError, TypeError, GameError) as exc:
        checks["read_artifacts"] = False
        result["error"] = str(exc)
    result["status"] = "passed" if all(checks.values()) else "failed"
    write_json(output / "verification.json", result, indent=2)
    return result


def run_reference(output: Path | None = None, *, preview_only: bool = False) -> dict:
    recipe = load_recipe(BUNDLE / "recipe.json")
    dataset = load_dataset(BUNDLE / "dataset.json")
    expected = json.loads((BUNDLE / "expected.json").read_text())
    if dataset.digest != expected["dataset_sha256"] or recipe_identity(recipe) != expected["recipe_sha256"]:
        raise GameError("reference_mismatch", "Bundled reference inputs differ from their expected identities.")
    if preview_only:
        return {**preview_recipe(recipe, dataset), "expected": expected}
    if output is None:
        raise GameError("missing_output", "Provide --output for execution, or use --preview.")
    if output.exists():
        raise GameError("experiment_exists", "Choose a fresh experiment directory; existing runs are preserved.")
    try:
        run_recipe(recipe, dataset, output, source_config=BUNDLE / "recipe.json")
    except Exception as exc:
        if output.is_dir():
            write_json(output / "verification.json", {"status": "failed", "error": str(exc)}, indent=2)
        raise
    return verify_reference(output)
