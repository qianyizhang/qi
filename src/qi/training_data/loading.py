"""Load supported prepared-data formats without importing a trainer."""

from pathlib import Path

from pydantic import TypeAdapter

from qi.training_data.assembly import TrainingDataset
from qi.training_data.relabel import RelabeledDataset
from qi.training_data.selection import SelectedDataset
from qi.training_data.v1 import Dataset

type PreparedDataset = Dataset | TrainingDataset | SelectedDataset | RelabeledDataset


def load_dataset(path: Path) -> PreparedDataset:
    dataset = TypeAdapter(PreparedDataset).validate_json(path.read_text())
    if isinstance(dataset, TrainingDataset):
        dataset.require_complete()
    return dataset


def load_snapshot(path: Path):
    """Open a verified bounded reader; this does not opt the optimizer into a new protocol."""
    from qi.training_data.snapshots import SnapshotReader

    return SnapshotReader(path)
