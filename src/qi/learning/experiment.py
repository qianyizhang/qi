"""Bounded learning curves over fixed data, nested subsets, and explicit seeds."""

import json
import sys
from hashlib import sha256
from pathlib import Path
from random import Random
from statistics import mean, pstdev
from time import perf_counter
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qi.evaluation import Corpus
from qi.game import GameError
from qi.learning.data import MAX_LABELS, Dataset


class LearningPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    sizes: list[int] = Field(default_factory=lambda: [96, 192, 384, 768], min_length=1, max_length=8)
    seeds: list[int] = Field(default_factory=lambda: [7, 17, 27], min_length=1, max_length=8)
    subset_seed: int = 7
    device: Literal["cpu", "mps"] = "cpu"
    threads: int = Field(default=1, ge=1, le=32)
    steps: int = Field(default=200, ge=1, le=2000)
    learning_rate: float = Field(default=0.01, gt=0, le=0.1)
    fit_seconds: float = Field(default=60.0, gt=0, le=600)
    total_seconds: float = Field(default=600.0, gt=0, le=7200)

    @model_validator(mode="after")
    def validate_matrix(self) -> Self:
        if self.sizes != sorted(set(self.sizes)) or not 1 <= self.sizes[0] <= self.sizes[-1] <= MAX_LABELS:
            raise ValueError("Sizes must be distinct, increasing, and within 1-32768.")
        if len(set(self.seeds)) != len(self.seeds) or any(not 0 <= seed < 2**63 for seed in self.seeds):
            raise ValueError("Seeds must be distinct integers in [0, 2**63).")
        return self


def ordered_inputs(dataset: Dataset, seed: int) -> list[str]:
    """Interleave shuffled source games so small subsets span multiple games."""
    groups = {}
    for label in dataset.split_labels("train"):
        groups.setdefault(label.source_id, []).append(label.input_sha256)
    rng = Random(seed)
    ids = sorted(groups)
    rng.shuffle(ids)
    for source in ids:
        groups[source].sort()
        rng.shuffle(groups[source])
    return [
        groups[source][index]
        for index in range(max(map(len, groups.values())))
        for source in ids
        if index < len(groups[source])
    ]


def preview(dataset: Dataset, corpus: Corpus, plan: LearningPlan) -> dict:
    dataset = Dataset.model_validate(dataset.model_dump())
    plan = LearningPlan.model_validate(plan.model_dump())
    if dataset.reserved_corpus.digest != corpus.digest:
        raise GameError(
            "corpus_mismatch",
            "Generate a dataset reserving this exact evaluation corpus before running the experiment.",
        )
    inputs = ordered_inputs(dataset, plan.subset_seed)
    if plan.sizes[-1] > len(inputs):
        raise GameError("insufficient_data", f"Requested {plan.sizes[-1]} training inputs; dataset has {len(inputs)}.")
    return {
        "plan": plan.model_dump(),
        "dataset_sha256": dataset.digest,
        "reserved_corpus_sha256": corpus.digest,
        "ordered_train_inputs": inputs,
        "validation_inputs": [label.input_sha256 for label in dataset.split_labels("validation")],
        "planned_trials": len(plan.sizes) * len(plan.seeds),
    }


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def summarize(trials: list[dict], plan: LearningPlan) -> list[dict]:
    rows = []
    for size in plan.sizes:
        complete = [trial for trial in trials if trial["size"] == size and trial["report"]["status"] == "complete"]
        row = {"size": size, "complete_seeds": len(complete), "expected_seeds": len(plan.seeds)}
        # CONTRACT: Only complete seed groups enter the learning curve.
        if len(complete) == len(plan.seeds):
            for split in ("train", "validation"):
                for metric in ("agreement", "cross_entropy"):
                    values = [trial["report"][split][metric] for trial in complete]
                    row[f"{split}_{metric}_mean"] = mean(values)
                    row[f"{split}_{metric}_std"] = pstdev(values)
            row["random_legal_agreement"] = complete[0]["report"]["validation"]["random_legal_agreement"]
        rows.append(row)
    return rows


def run_experiment(dataset: Dataset, corpus: Corpus, plan: LearningPlan, output: Path) -> dict:
    manifest = preview(dataset, corpus, plan)
    from qi.learning.train import train, validate_device

    validate_device(plan.device, plan.threads)
    if output.exists():
        raise GameError(
            "experiment_exists", "Choose a fresh experiment directory; runs are never overwritten or resumed."
        )
    # Include the complete local implementation and dependency identity, not Git authorship.
    root = Path(__file__).resolve().parents[3]
    files = [*sorted((root / "src/qi").rglob("*.py")), root / "pyproject.toml", root / "uv.lock"]
    digest = sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    manifest.update(source_sha256=digest.hexdigest(), python=sys.version)
    output.mkdir(parents=True)
    (output / "dataset.json").write_text(dataset.model_dump_json() + "\n")
    write_json(output / "manifest.json", manifest)
    started = perf_counter()
    result = {"status": "running", "planned_trials": manifest["planned_trials"], "trials": [], "curve": []}

    def save() -> None:
        result["elapsed_seconds"] = perf_counter() - started
        result["curve"] = summarize(result["trials"], plan)
        write_json(output / "summary.json", result)

    save()
    try:
        for size in plan.sizes:
            for seed in plan.seeds:
                remaining = plan.total_seconds - (perf_counter() - started)
                if remaining <= 0:
                    result["status"] = "deadline"
                    save()
                    return result
                name = f"size-{size}-seed-{seed}"
                report = train(
                    dataset,
                    output / f"{name}.pt",
                    seed=seed,
                    steps=plan.steps,
                    seconds=min(plan.fit_seconds, remaining),
                    learning_rate=plan.learning_rate,
                    device=plan.device,
                    threads=plan.threads,
                    train_inputs=manifest["ordered_train_inputs"][:size],
                )
                write_json(output / f"{name}.json", report)
                result["trials"].append({"size": size, "seed": seed, "report": report})
                save()
        result["status"] = (
            "complete" if all(t["report"]["status"] == "complete" for t in result["trials"]) else "incomplete"
        )
    except (Exception, KeyboardInterrupt) as exc:
        result["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        save()
        raise
    save()
    return result
