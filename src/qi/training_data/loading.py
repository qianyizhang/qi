"""Load supported prepared-data formats without importing a trainer."""

from pathlib import Path

from pydantic import TypeAdapter

from qi.training_data.assembly import TrainingDataset
from qi.training_data.v1 import Dataset

type PreparedDataset = Dataset | TrainingDataset


def load_dataset(path: Path) -> PreparedDataset:
    dataset = TypeAdapter(PreparedDataset).validate_json(path.read_text())
    if isinstance(dataset, TrainingDataset):
        dataset.require_complete()
    return dataset
