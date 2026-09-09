"""Historical selection preserves supervision and never changes held-out membership."""

import pytest

from qi.learning.config import DataSettings, Recipe
from qi.learning.runs import preview_recipe
from qi.training_data.loading import load_dataset
from qi.training_data.selection import SelectedDataset, select_training


def test_selection_roundtrip_preserves_labels_and_heldout(tiny_dataset, tmp_path):
    parent = tiny_dataset.model_dump_json()
    wanted = tiny_dataset.split_labels("train")[::2]
    selected = select_training(tiny_dataset, [label.input_sha256 for label in wanted], selection_id="fixed")
    assert selected.split_labels("train") == wanted
    assert selected.split_labels("validation") == tiny_dataset.split_labels("validation")
    assert selected.parent_dataset_sha256 == tiny_dataset.digest
    assert tiny_dataset.model_dump_json() == parent
    path = tmp_path / "dataset.json"
    path.write_text(selected.model_dump_json())
    loaded = load_dataset(path)
    assert isinstance(loaded, SelectedDataset)
    assert loaded.digest == selected.digest
    preview = preview_recipe(Recipe(data=DataSettings(dataset=str(path))), loaded)
    assert set(preview["trials"][0]["train_inputs"]) == {label.input_sha256 for label in wanted}


@pytest.mark.parametrize("selection", ["duplicate", "heldout", "unknown", "empty"])
def test_selection_rejects_invalid_inputs(tiny_dataset, selection):
    key = tiny_dataset.split_labels("train")[0].input_sha256
    inputs = {
        "duplicate": [key, key],
        "heldout": [tiny_dataset.split_labels("validation")[0].input_sha256],
        "unknown": ["f" * 64],
        "empty": [],
    }[selection]
    with pytest.raises(ValueError, match="training inputs"):
        select_training(tiny_dataset, inputs, selection_id="invalid")


def test_selection_still_validates_replay(tiny_dataset):
    selected = select_training(
        tiny_dataset, [tiny_dataset.split_labels("train")[0].input_sha256], selection_id="fixed"
    ).model_dump()
    selected["labels"][0]["input_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="identity"):
        SelectedDataset.model_validate(selected)
