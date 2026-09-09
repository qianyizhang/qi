"""Prepare, profile, then run the locked AB-LEARN-006 comparison using existing labels."""

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev, stdev
from time import perf_counter

from investigate_source_coverage import investigate

from qi.learning.config import DataSettings, ExecutionSettings, Recipe, TrainingSettings, load_recipe
from qi.learning.runs import run_recipe
from qi.training_data.loading import load_dataset
from qi.training_data.selection import select_training
from qi.training_data.v1 import Dataset


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def prepare(data: Path, audit_path: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Choose a fresh study directory.")
    parent = Dataset.model_validate_json(data.read_text())
    audit = json.loads(audit_path.read_text())
    expected = investigate(parent)
    if any(audit.get(key) != value for key, value in json.loads(json.dumps(expected)).items()):
        raise ValueError("Saved selection differs from the frozen data-only audit.")
    trials = []
    for block in audit["replicates"]:
        for case, selection in block["cases"].items():
            name = f"block-{block['block']}-{case}"
            dataset = select_training(parent, selection["input_ids"], selection_id=name)
            path = output / "datasets" / f"{name}.json"
            write(path, dataset.model_dump())
            for seed in (7, 17, 27):
                trial = f"{name}-seed-{seed}"
                config = Recipe(
                    name=name,
                    data=DataSettings(dataset=str(path.resolve()), train_size=768, selection="source-order"),
                    training=TrainingSettings(seed=seed),
                    execution=ExecutionSettings(device="cpu", threads=1, fit_seconds=600.0, total_seconds=600.0),
                )
                write(output / "configs" / f"{trial}.json", config.model_dump())
                trials.append({"name": trial, "block": block["block"], "case": case, "seed": seed})
    write(
        output / "study.json",
        {
            "work_id": "AB-LEARN-006",
            "parent_dataset_sha256": parent.digest,
            "selection_audit": str(audit_path.resolve()),
            "trials": trials,
            "expectation": "Broader source coverage may improve held-out agreement at fixed label count.",
            "primary_metric": "validation agreement; paired broader minus concentrated within each block and seed",
            "secondary_metric": "validation cross-entropy; lower is better",
            "holdout_status": "previously inspected; exploratory",
            "profile_policy": "First fit counts in the 18; only runtime allowances may change after profiling.",
        },
    )
    print("Prepared six frozen datasets and all 18 full configs.", flush=True)


def execute(output: Path, *, profile: bool) -> None:
    study = json.loads((output / "study.json").read_text())
    trials = study["trials"][:1] if profile else study["trials"][1:]
    if not profile:
        timing = json.loads((output / "profile.json").read_text())
        first = json.loads((output / "runs" / study["trials"][0]["name"] / "summary.json").read_text())
        if first["status"] != "complete":
            raise ValueError("The profile fit must complete before the fixed matrix continues.")
        allowance = min(600.0, max(60.0, timing["wall_seconds"] * 3))
        write(output / "execution-plan.json", {"remaining_fits": 17, "seconds_per_fit": allowance})
    for trial in trials:
        config_path = output / "configs" / f"{trial['name']}.json"
        recipe = load_recipe(config_path)
        if not profile:
            recipe.execution.fit_seconds = allowance
            recipe.execution.total_seconds = allowance
            # Prepared scientific settings are unchanged; saved runtime config is explicit.
            config_path = output / "execution-configs" / config_path.name
            write(config_path, recipe.model_dump())
        started = perf_counter()
        result = run_recipe(
            recipe, load_dataset(Path(recipe.data.dataset)), output / "runs" / trial["name"], source_config=config_path
        )
        wall = perf_counter() - started
        if profile:
            write(
                output / "profile.json",
                {
                    "trial": trial["name"],
                    "wall_seconds": wall,
                    "optimization_seconds": result["trials"][0]["report"]["optimization_seconds"],
                },
            )
        print(json.dumps({"trial": trial["name"], "status": result["status"], "wall_seconds": wall}), flush=True)
        if result["status"] != "complete":
            raise ValueError("Incomplete fit retained; do not silently rerun or aggregate it.")


def summarize(output: Path, report_path: Path) -> None:
    study = json.loads((output / "study.json").read_text())
    expected = {
        (block, case, seed) for block in range(3) for case in ("concentrated", "broader") for seed in (7, 17, 27)
    }
    if len(study["trials"]) != 18 or {(t["block"], t["case"], t["seed"]) for t in study["trials"]} != expected:
        raise ValueError("The study must contain the exact 18 declared fits.")
    rows, heldout, training_inputs = [], None, {}
    for trial in study["trials"]:
        folder = output / "runs" / trial["name"]
        result = json.loads((folder / "summary.json").read_text())
        if result["status"] != "complete" or len(result["trials"]) != 1:
            raise ValueError("All 18 declared fits must be complete before aggregation.")
        report = result["trials"][0]["report"]
        prepared = load_recipe(output / "configs" / f"{trial['name']}.json")
        actual = load_recipe(folder / "config.json")
        for section in ("model", "objective", "optimizer", "training", "evaluation"):
            if getattr(actual, section) != getattr(prepared, section):
                raise ValueError(f"Scientific config changed: {trial['name']} / {section}.")
        if actual.data.model_dump(exclude={"dataset"}) != prepared.data.model_dump(exclude={"dataset"}):
            raise ValueError("Data selection settings changed.")
        metadata = report["metadata"]
        if report["completed_steps"] != 200 or metadata["seed"] != trial["seed"]:
            raise ValueError("Trial differs from the fixed step/seed plan.")
        if report["training_device"] != "cpu" or report["training_threads"] != 1 or metadata["learning_rate"] != 0.01:
            raise ValueError("Trial differs from the fixed device/optimizer plan.")
        if heldout is None:
            heldout = metadata["validation_inputs"]
        if metadata["validation_inputs"] != heldout or len(heldout) != 4219:
            raise ValueError("Held-out inputs must match exactly in every fit.")
        keys = metadata["train_inputs"]
        group = (trial["block"], trial["case"])
        if keys != training_inputs.setdefault(group, keys) or len(set(keys)) != 768 or set(keys) & set(heldout):
            raise ValueError("Training selection changed or overlaps held-out inputs.")
        if not report["reload_predictions_equal"]:
            raise ValueError("Checkpoint reload differs.")
        rows.append(
            {
                **trial,
                "status": report["status"],
                "completed_steps": report["completed_steps"],
                "train_agreement": report["train"]["agreement"],
                "validation_agreement": report["validation"]["agreement"],
                "validation_cross_entropy": report["validation"]["cross_entropy"],
                "optimization_seconds": report["optimization_seconds"],
                "dataset_sha256": metadata["dataset_sha256"],
                "checkpoint_sha256": report["checkpoint_sha256"],
                "source_sha256": json.loads((folder / "manifest.json").read_text())["source_sha256"],
            }
        )
    blocks = []
    for block in range(3):
        pairs = []
        for seed in (7, 17, 27):
            cases = {row["case"]: row for row in rows if row["block"] == block and row["seed"] == seed}
            pairs.append(
                {
                    "seed": seed,
                    **{
                        metric: cases["broader"][metric] - cases["concentrated"][metric]
                        for metric in ("validation_agreement", "validation_cross_entropy")
                    },
                }
            )
        blocks.append(
            {
                "block": block,
                "paired_deltas": pairs,
                **{
                    metric: {
                        "mean_delta": mean(pair[metric] for pair in pairs),
                        "initialization_std": pstdev(pair[metric] for pair in pairs),
                    }
                    for metric in ("validation_agreement", "validation_cross_entropy")
                },
            }
        )
    write(
        report_path,
        {
            "work_id": study["work_id"],
            "status": "complete",
            "training_runs": len(rows),
            "parent_dataset_sha256": study["parent_dataset_sha256"],
            "artifact_directory": str(output),
            "holdout_positions": len(heldout),
            "holdout_status": study["holdout_status"],
            "delta_direction": "broader minus concentrated",
            "profile": json.loads((output / "profile.json").read_text()),
            "execution_plan": json.loads((output / "execution-plan.json").read_text()),
            "trials": rows,
            "blocks": blocks,
            "across_blocks": {
                metric: {
                    "mean_delta": mean(block[metric]["mean_delta"] for block in blocks),
                    "source_block_sample_std": stdev(block[metric]["mean_delta"] for block in blocks),
                }
                for metric in ("validation_agreement", "validation_cross_entropy")
            },
            "case_means": {
                case: {
                    metric: mean(row[metric] for row in rows if row["case"] == case)
                    for metric in ("train_agreement", "validation_agreement", "validation_cross_entropy")
                }
                for case in ("concentrated", "broader")
            },
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "profile", "run", "summarize"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.stage == "prepare":
        if args.data is None or args.audit is None:
            parser.error("prepare requires --data and --audit")
        prepare(args.data, args.audit, args.output)
    elif args.stage == "summarize":
        if args.report is None:
            parser.error("summarize requires --report")
        summarize(args.output, args.report)
    else:
        execute(args.output, profile=args.stage == "profile")


if __name__ == "__main__":
    main()
