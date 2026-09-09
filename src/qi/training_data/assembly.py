"""Deterministic, quota-accounted frozen composition over reusable examples."""

from hashlib import sha256
from random import Random
from typing import Literal, Self

from pydantic import Field, model_validator

from qi.players.policy.encoding import input_key
from qi.training_data.contracts import (
    PHASE_POLICY,
    Contract,
    Example,
    Library,
    Mode,
    Phase,
    Source,
    Split,
    example_phase,
    fingerprint,
)
from qi.training_data.legacy import Label, reserved_inputs


class Bucket(Contract):
    id: str = Field(min_length=1)
    split: Split
    count: int = Field(ge=1, le=32768)
    modes: list[Mode] = Field(default_factory=lambda: ["random", "teacher-guided"])
    phases: list[Phase] = Field(default_factory=lambda: ["opening", "middlegame", "endgame", "unknown"])
    themes: list[str] = Field(default_factory=list)
    objective: Literal["win-in-one"] | None = None

    def matches(self, example: Example, source: Source, library: Library) -> bool:
        plan = next(p for p in library.recipe.sources if p.id == source.plan_id)
        return (
            plan.split == self.split
            and plan.mode in self.modes
            and example_phase(example, plan) in self.phases
            and set(self.themes) <= set(plan.start.themes)
            and (self.objective is None or self.objective == plan.start.objective)
        )


class MixtureRecipe(Contract):
    id: str = Field(min_length=1)
    version: Literal["frozen-mixture-v1"] = "frozen-mixture-v1"
    seed: int = 7
    supervision_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    overlap_policy: Literal["first-bucket-wins"] = "first-bucket-wins"
    buckets: list[Bucket] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_recipe(self) -> Self:
        if len({b.id for b in self.buckets}) != len(self.buckets):
            raise ValueError("Quota bucket IDs must be unique.")
        if {b.split for b in self.buckets} != {"train", "validation"}:
            raise ValueError("Declare both training and held-out quotas.")
        if sum(b.count for b in self.buckets) > 32768:
            raise ValueError("At most 32768 retained examples.")
        return self


class Selection(Contract):
    example: str
    source_id: str
    bucket: str


class Manifest(Contract):
    schema_version: Literal["dataset-manifest-v1"] = "dataset-manifest-v1"
    phase_policy: Literal[PHASE_POLICY] = PHASE_POLICY
    recipe: MixtureRecipe
    selections: list[Selection]
    actual: dict[str, int]
    status: Literal["complete", "incomplete"]
    fingerprint: str


def select(library: Library, recipe: MixtureRecipe) -> tuple[list[Selection], dict[str, int]]:
    sources = {s.id: s for s in library.sources}
    plans = {p.id: p for p in library.recipe.sources}
    reserved = reserved_inputs(library.reserved_corpus)
    candidates = []
    targets, observation_splits = {}, {}
    for example in sorted(library.examples, key=lambda e: e.fingerprint):
        if example.supervision_fingerprint != recipe.supervision_fingerprint:
            continue
        key = input_key(example.analysis.snapshot.game())
        if key in reserved:
            continue
        splits = {plans[sources[sid].plan_id].split for sid in example.source_ids}
        observation_splits.setdefault(key, set()).update(splits)
        if len(observation_splits[key]) > 1:
            raise ValueError("Observation or contributing lineage crosses training and held-out splits.")
        previous = targets.setdefault(key, example.analysis.move)
        if previous != example.analysis.move:
            raise ValueError("Ambiguous supervision for the same model observation.")
        candidates.append(example)
    # Independent bucket RNGs keep the held-out selection fixed when training quotas change.
    selections, used = [], set()
    actual = {b.id: 0 for b in recipe.buckets}
    assigned = {b.id: [] for b in recipe.buckets}
    for example in candidates:
        for bucket in recipe.buckets:
            matches = sorted(sid for sid in example.source_ids if bucket.matches(example, sources[sid], library))
            if matches:
                assigned[bucket.id].append((example, matches[0]))
                break
    for bucket in recipe.buckets:
        rows = assigned[bucket.id]
        Random(fingerprint("bucket-order-v1", {"seed": recipe.seed, "bucket": bucket.id})).shuffle(rows)
        for example, source_id in rows:
            key = example.observation_fingerprint
            if key in used:
                continue
            if actual[bucket.id] == bucket.count:
                break
            used.add(key)
            selections.append(Selection(example=example.fingerprint, source_id=source_id, bucket=bucket.id))
            actual[bucket.id] += 1
    return selections, actual


def manifest_fingerprint(library: Library, recipe: MixtureRecipe, selections: list[Selection]) -> str:
    examples = library.example_index
    source_ids = sorted({sid for row in selections for sid in examples[row.example].source_ids})
    sources = {s.id: s for s in library.sources}
    plans = {p.id: p for p in library.recipe.sources}
    return fingerprint(
        "dataset-manifest-v1",
        {
            "recipe": recipe.model_dump(),
            "phase_policy": PHASE_POLICY,
            "observation_scheme": "observation-v1",
            "state_scheme": "replay-state-v1",
            "reserved_corpus": library.reserved_corpus.digest,
            "selections": [s.model_dump() for s in selections],
            "lineage": {row.example: sorted(examples[row.example].source_ids) for row in selections},
            "sources": [sources[sid].model_dump() for sid in source_ids],
            "plans": {sources[sid].plan_id: plans[sources[sid].plan_id].model_dump() for sid in source_ids},
            "generation_seed": library.recipe.seed,
        },
    )


class TrainingDataset(Contract):
    schema_version: Literal["training-dataset-v2"] = "training-dataset-v2"
    library: Library
    manifest: Manifest

    @model_validator(mode="after")
    def validate_dataset(self) -> Self:
        selections, actual = select(self.library, self.manifest.recipe)
        status = "complete" if all(actual[b.id] == b.count for b in self.manifest.recipe.buckets) else "incomplete"
        if (
            selections != self.manifest.selections
            or actual != self.manifest.actual
            or status != self.manifest.status
            or manifest_fingerprint(self.library, self.manifest.recipe, selections) != self.manifest.fingerprint
        ):
            raise ValueError("Manifest selection, quota accounting or fingerprint differs from its frozen recipe.")
        return self

    def require_complete(self) -> None:
        if self.manifest.status != "complete":
            raise ValueError("Incomplete mixture: retained unique-example quotas were not met.")

    @property
    def digest(self) -> str:
        # Byte-format digest remains distinct from semantic composition identity.
        return sha256(self.model_dump_json().encode()).hexdigest()

    @property
    def reserved_corpus(self):
        return self.library.reserved_corpus

    @property
    def labels(self) -> list[Label]:
        examples = self.library.example_index
        return [
            Label(
                source_id=row.source_id,
                input_sha256=input_key(examples[row.example].analysis.snapshot.game()),
                analysis=examples[row.example].analysis,
            )
            for row in self.manifest.selections
        ]

    def split_labels(self, split: Split) -> list[Label]:
        buckets = {b.id for b in self.manifest.recipe.buckets if b.split == split}
        return [
            label for label, row in zip(self.labels, self.manifest.selections, strict=True) if row.bucket in buckets
        ]

    def slice_inputs(self) -> dict[str, list[str]]:
        examples, sources = self.library.example_index, {s.id: s for s in self.library.sources}
        plans = {p.id: p for p in self.library.recipe.sources}
        result = {f"{b.split}/bucket:{b.id}": [] for b in self.manifest.recipe.buckets}
        for row in self.manifest.selections:
            example, source = examples[row.example], sources[row.source_id]
            plan = plans[source.plan_id]
            slices = [f"bucket:{row.bucket}", f"mode:{plan.mode}", f"phase:{example_phase(example, plan)}"]
            slices += [f"theme:{theme}" for theme in plan.start.themes]
            if plan.start.objective:
                slices.append(f"objective:{plan.start.objective}")
            for name in slices:
                result.setdefault(f"{plan.split}/{name}", []).append(input_key(example.analysis.snapshot.game()))
        return result


def assemble(library: Library, recipe: MixtureRecipe) -> TrainingDataset:
    library = Library.model_validate(library.model_dump())
    recipe = MixtureRecipe.model_validate(recipe.model_dump())
    selections, actual = select(library, recipe)
    status = "complete" if all(actual[b.id] == b.count for b in recipe.buckets) else "incomplete"
    return TrainingDataset(
        library=library,
        manifest=Manifest(
            recipe=recipe,
            selections=selections,
            actual=actual,
            status=status,
            fingerprint=manifest_fingerprint(library, recipe, selections),
        ),
    )
