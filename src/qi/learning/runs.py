"""Execute named cases through the existing trainer, preserving copyable configs."""

from pathlib import Path
from statistics import mean, pstdev
from time import perf_counter

from qi_game.core import GameError

from qi.artifacts import write_json
from qi.learning.config import Recipe
from qi.learning.provenance import source_identity
from qi.training_data.assembly import TrainingDataset
from qi.training_data.loading import PreparedDataset


def preview_recipe(recipe: Recipe, dataset: PreparedDataset) -> dict:
    recipe = Recipe.model_validate(recipe.model_dump())
    dataset = type(dataset).model_validate(dataset.model_dump())
    if isinstance(dataset, TrainingDataset):
        dataset.require_complete()
    trials = []
    for case, config in recipe.expand():
        inputs = config.training_inputs(dataset)
        trials.append({"case": case, "config": config.model_dump(), "train_inputs": inputs})
    return {
        "dataset_sha256": dataset.digest,
        "reserved_corpus_sha256": dataset.reserved_corpus.digest,
        "validation_inputs": [label.input_sha256 for label in dataset.split_labels("validation")],
        "planned_trials": len(trials),
        "trials": trials,
    }


def summarize_cases(trials: list[dict], planned: list[dict]) -> list[dict]:
    rows = []
    for case in dict.fromkeys(trial["case"] for trial in planned):
        expected = sum(trial["case"] == case for trial in planned)
        complete = [trial for trial in trials if trial["case"] == case and trial["report"]["status"] == "complete"]
        row = {"case": case, "complete_seeds": len(complete), "expected_seeds": expected}
        if len(complete) == expected:
            for split in ("train", "validation"):
                for metric in ("agreement", "cross_entropy"):
                    values = [trial["report"][split][metric] for trial in complete]
                    row[f"{split}_{metric}_mean"] = mean(values)
                    row[f"{split}_{metric}_std"] = pstdev(values)
            row["random_legal_agreement"] = complete[0]["report"]["validation"]["random_legal_agreement"]
        rows.append(row)
    return rows


def run_recipe(recipe: Recipe, dataset: PreparedDataset, output: Path, *, source_config: Path) -> dict:
    manifest = preview_recipe(recipe, dataset)
    from qi.learning.train import train, validate_device

    for _, config in recipe.expand():
        validate_device(config.execution.device, config.execution.threads)
    if output.exists():
        raise GameError("experiment_exists", "Choose a fresh experiment directory; existing runs are preserved.")
    recipe = recipe.model_copy(deep=True)
    recipe.derived_from = recipe.origin_config or recipe.derived_from or str(source_config.resolve())
    recipe.origin_config = str((output / "config.json").resolve())
    recipe.data.dataset = str((output / "dataset.json").resolve())
    manifest.update(source_identity(), source_config=str(source_config.resolve()))
    output.mkdir(parents=True)
    (output / "dataset.json").write_text(dataset.model_dump_json() + "\n")
    write_json(output / "config.json", recipe.model_dump(), indent=2)
    write_json(output / "manifest.json", manifest, indent=2)
    result = {"status": "running", "planned_trials": manifest["planned_trials"], "trials": []}
    started = perf_counter()

    def save() -> None:
        result["elapsed_seconds"] = perf_counter() - started
        result["cases"] = summarize_cases(result["trials"], manifest["trials"])
        write_json(output / "summary.json", result, indent=2)

    save()
    try:
        for (case, config), planned in zip(recipe.expand(), manifest["trials"], strict=True):
            remaining = recipe.execution.total_seconds - (perf_counter() - started)
            if remaining <= 0:
                result["status"] = "deadline"
                save()
                return result
            config.execution.fit_seconds = min(config.execution.fit_seconds, remaining)
            config.data.train_size = len(planned["train_inputs"])
            name = f"{case}-seed-{config.training.seed}"
            config.derived_from = recipe.origin_config
            config.origin_config = str((output / f"{name}.config.json").resolve())
            result["active_trial"] = name
            write_json(output / f"{name}.config.json", config.model_dump(), indent=2)
            save()
            report = train(
                dataset,
                output / f"{name}.pt",
                seed=config.training.seed,
                steps=config.training.updates,
                seconds=config.execution.fit_seconds,
                learning_rate=config.optimizer.learning_rate,
                device=config.execution.device,
                threads=config.execution.threads,
                train_inputs=planned["train_inputs"],
            )
            write_json(output / f"{name}.json", report, indent=2)
            result["trials"].append(
                {"case": case, "seed": config.training.seed, "config": f"{name}.config.json", "report": report}
            )
            result.pop("active_trial")
            save()
        result["status"] = (
            "complete" if all(trial["report"]["status"] == "complete" for trial in result["trials"]) else "incomplete"
        )
    except (Exception, KeyboardInterrupt) as exc:
        result["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        save()
        raise
    save()
    return result
