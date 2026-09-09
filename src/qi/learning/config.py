"""Small declarative recipes; importing or previewing one needs no trainer."""

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from qi.game import GameError
from qi.players.policy.encoding import ARCHITECTURE, ENCODING
from qi.training_data.loading import PreparedDataset
from qi.training_data.v1 import MAX_LABELS


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class DataSettings(Settings):
    dataset: str = Field(min_length=1)
    train_size: int | None = Field(default=None, ge=1, le=MAX_LABELS)
    selection: Literal["source-order", "source-interleaved"] = "source-interleaved"
    subset_seed: int = 7


class ModelSettings(Settings):
    architecture: Literal[ARCHITECTURE] = ARCHITECTURE
    encoding: Literal[ENCODING] = ENCODING


class ObjectiveSettings(Settings):
    name: Literal["legal-masked-teacher-move"] = "legal-masked-teacher-move"


class OptimizerSettings(Settings):
    name: Literal["adam"] = "adam"
    learning_rate: float = Field(default=0.01, gt=0, le=0.1)


class TrainingSettings(Settings):
    batching: Literal["full"] = "full"
    updates: int = Field(default=200, ge=1, le=2000)
    seed: int = Field(default=7, ge=-(2**63), lt=2**64)
    precision: Literal["float32"] = "float32"


class EvaluationSettings(Settings):
    split: Literal["validation"] = "validation"
    metrics: list[Literal["agreement", "cross_entropy"]] = Field(default_factory=lambda: ["agreement", "cross_entropy"])

    @model_validator(mode="after")
    def fixed_metrics(self) -> Self:
        if self.metrics != ["agreement", "cross_entropy"]:
            raise ValueError("This trainer reports agreement and cross_entropy, in that order.")
        return self


class ExecutionSettings(Settings):
    device: Literal["cpu", "mps"] = "cpu"
    threads: int = Field(default=1, ge=1, le=32)
    fit_seconds: float = Field(default=60.0, gt=0, le=600)
    total_seconds: float = Field(default=600.0, gt=0, le=7200)


class RunConfig(Settings):
    schema_version: Literal[1] = 1
    name: str = Field(default="policy", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    derived_from: str | None = None
    origin_config: str | None = None
    data: DataSettings
    model: ModelSettings = Field(default_factory=ModelSettings)
    objective: ObjectiveSettings = Field(default_factory=ObjectiveSettings)
    optimizer: OptimizerSettings = Field(default_factory=OptimizerSettings)
    training: TrainingSettings = Field(default_factory=TrainingSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)

    def training_inputs(self, dataset: PreparedDataset) -> list[str]:
        from qi.learning.experiment import ordered_inputs

        inputs = (
            ordered_inputs(dataset, self.data.subset_seed)
            if self.data.selection == "source-interleaved"
            else [label.input_sha256 for label in dataset.split_labels("train")]
        )
        size = self.data.train_size or len(inputs)
        if size > len(inputs):
            raise GameError("insufficient_data", f"Requested {size} training inputs; dataset has {len(inputs)}.")
        return inputs[:size]


class Case(Settings):
    name: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    overrides: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)


class Recipe(RunConfig):
    cases: list[Case] = Field(default_factory=list, max_length=16)
    seeds: list[int] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def valid_cases(self) -> Self:
        if len({case.name.casefold() for case in self.cases}) != len(self.cases):
            raise ValueError("Case names must be distinct even on case-insensitive filesystems.")
        if len({seed % 2**64 for seed in self.seeds}) != len(self.seeds) or any(
            not -(2**63) <= seed < 2**64 for seed in self.seeds
        ):
            raise ValueError("Seeds must be distinct PyTorch initializations in [-2**63, 2**64).")
        self.expand()
        return self

    def expand(self) -> list[tuple[str, RunConfig]]:
        trials = []
        for case in self.cases or [Case(name=self.name)]:
            values = self.model_dump(exclude={"cases", "seeds"})
            for section, changes in case.overrides.items():
                if section not in {"data", "model", "objective", "optimizer", "training", "evaluation", "execution"}:
                    raise ValueError(f"Unknown override section: {section}.")
                if (
                    (section == "data" and "dataset" in changes)
                    or (section == "execution" and "total_seconds" in changes)
                    or (section == "training" and "seed" in changes)
                ):
                    raise ValueError("Dataset, total allowance and initialization seeds belong to the shared recipe.")
                values[section].update(changes)
            for seed in self.seeds or [self.training.seed]:
                values["training"]["seed"] = seed
                values["name"] = case.name
                trials.append((case.name, RunConfig.model_validate(values)))
        return trials


def load_recipe(path: Path) -> Recipe:
    recipe = Recipe.model_validate_json(path.read_text())
    dataset = Path(recipe.data.dataset)
    recipe.data.dataset = str((path.parent / dataset).resolve())
    for field in ("origin_config", "derived_from"):
        value = getattr(recipe, field)
        if value is not None:
            setattr(recipe, field, str((path.parent / value).resolve()))
    return recipe
