"""Explicit subsets of historical labels without claiming to rerun their generator."""

from typing import Literal

from pydantic import Field

from qi.training_data.v1 import Dataset


class SelectedDataset(Dataset):
    """Reuse v1 replay/leakage checks; preserve the parent identity separately."""

    schema_version: Literal["selected-legacy-dataset-v1"] = "selected-legacy-dataset-v1"
    generator: Literal["explicit-input-selection-v1"] = "explicit-input-selection-v1"
    parent_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selection_id: str = Field(min_length=1)


def select_training(parent: Dataset, inputs: list[str], *, selection_id: str) -> SelectedDataset:
    """Retain exact training inputs and the entire original held-out split."""
    parent = type(parent).model_validate(parent.model_dump())
    available = {label.input_sha256 for label in parent.split_labels("train")}
    selected = set(inputs)
    if not inputs or len(selected) != len(inputs) or not selected <= available:
        raise ValueError("Select distinct, existing training inputs only.")
    selected.update(label.input_sha256 for label in parent.split_labels("validation"))
    labels = [label for label in parent.labels if label.input_sha256 in selected]
    source_ids = {label.source_id for label in labels}
    return SelectedDataset(
        seed=parent.seed,
        reserved_corpus=parent.reserved_corpus,
        sources=[source for source in parent.sources if source.id in source_ids],
        labels=labels,
        parent_dataset_sha256=parent.digest,
        selection_id=selection_id,
    )
