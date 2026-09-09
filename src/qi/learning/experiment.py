"""Bounded learning curves over fixed data, nested subsets, and explicit seeds."""

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from random import Random
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


def source_identity() -> dict:
    root = Path(__file__).resolve().parents[3]
    files = [*sorted((root / "src/qi").rglob("*.py")), root / "pyproject.toml", root / "uv.lock"]
    digest = sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    identity = {"source_sha256": digest.hexdigest(), "python": sys.version, "git_revision": None, "git_dirty": None}
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "src/qi", "pyproject.toml", "uv.lock"],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except OSError:
        return identity
    identity.update(
        git_revision=revision.stdout.strip() if revision.returncode == 0 else None,
        git_dirty=bool(status.stdout) if status.returncode == 0 else None,
    )
    return identity


def summarize(trials: list[dict], plan: LearningPlan) -> list[dict]:
    """Compatibility projection of the shared complete-seed summaries."""
    from qi.learning.runs import summarize_cases

    planned = [{"case": f"size-{size}"} for size in plan.sizes for _ in plan.seeds]
    converted = [{**trial, "case": f"size-{trial['size']}"} for trial in trials]
    rows = summarize_cases(converted, planned)
    for size, row in zip(plan.sizes, rows, strict=True):
        row.pop("case")
        row["size"] = size
    return rows


def run_experiment(dataset: Dataset, corpus: Corpus, plan: LearningPlan, output: Path) -> dict:
    """Keep the flag-based curve API as an adapter to the configured executor."""
    from qi.learning.config import Recipe
    from qi.learning.runs import _execute

    manifest = preview(dataset, corpus, plan)
    recipe = Recipe.model_validate(
        {
            "name": "learning-curve",
            "data": {"dataset": str((output / "dataset.json").resolve()), "subset_seed": plan.subset_seed},
            "optimizer": {"learning_rate": plan.learning_rate},
            "training": {"updates": plan.steps},
            "execution": {
                "device": plan.device,
                "threads": plan.threads,
                "fit_seconds": plan.fit_seconds,
                "total_seconds": plan.total_seconds,
            },
            "cases": [{"name": f"size-{size}", "overrides": {"data": {"train_size": size}}} for size in plan.sizes],
            "seeds": plan.seeds,
        }
    )
    return _execute(recipe, dataset, output, legacy_manifest=manifest, legacy_plan=plan)
