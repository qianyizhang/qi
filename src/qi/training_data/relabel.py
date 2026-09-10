"""Replace supervision on frozen inputs without claiming to regenerate sources."""

from typing import Literal

from pydantic import Field

from qi.teacher import TeacherAnalysis
from qi.training_data.selection import SelectedDataset
from qi.training_data.v1 import Dataset, Label


class RelabeledDataset(Dataset):
    schema_version: Literal["relabeled-dataset-v1"] = "relabeled-dataset-v1"
    generator: Literal["fixed-input-relabel-v1"] = "fixed-input-relabel-v1"
    parent_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def select_validation(parent: Dataset, inputs: list[str], *, selection_id: str) -> SelectedDataset:
    """Keep all training labels and explicitly select held-out labels in source order."""
    parent = type(parent).model_validate(parent.model_dump())
    available = {label.input_sha256 for label in parent.split_labels("validation")}
    if not inputs or len(set(inputs)) != len(inputs) or not set(inputs) <= available:
        raise ValueError("Select distinct existing validation inputs.")
    keep = set(inputs) | {label.input_sha256 for label in parent.split_labels("train")}
    labels = [label for label in parent.labels if label.input_sha256 in keep]
    sources = {label.source_id for label in labels}
    return SelectedDataset(
        seed=parent.seed,
        reserved_corpus=parent.reserved_corpus,
        sources=[source for source in parent.sources if source.id in sources],
        labels=labels,
        parent_dataset_sha256=parent.digest,
        selection_id=selection_id,
    )


def relabel(parent: Dataset, answers: dict[str, TeacherAnalysis]) -> RelabeledDataset:
    """Require one fresh legal answer per unchanged full-history input, in original order."""
    parent = type(parent).model_validate(parent.model_dump())
    if set(answers) != {label.input_sha256 for label in parent.labels}:
        raise ValueError("Relabeling must cover exactly the frozen inputs.")
    labels = []
    for label in parent.labels:
        answer = answers[label.input_sha256]
        if answer.snapshot != label.analysis.snapshot or answer.state_hash != label.analysis.state_hash:
            raise ValueError("Relabeling changed the full-history input.")
        labels.append(Label(source_id=label.source_id, input_sha256=label.input_sha256, analysis=answer))
    return RelabeledDataset(
        seed=parent.seed,
        reserved_corpus=parent.reserved_corpus,
        sources=parent.sources,
        labels=labels,
        parent_dataset_sha256=parent.digest,
    )
