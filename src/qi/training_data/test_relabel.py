"""Frozen-input relabeling keeps source lineage and validates new supervision."""

import pytest

from qi.game import legal_moves
from qi.training_data.loading import load_dataset
from qi.training_data.relabel import RelabeledDataset, relabel, select_validation


def test_relabel_roundtrip_preserves_inputs_and_parent(tiny_dataset, tmp_path):
    before = tiny_dataset.model_dump_json()
    chosen = [tiny_dataset.split_labels("validation")[0].input_sha256]
    subset = select_validation(tiny_dataset, chosen, selection_id="test")
    assert subset.split_labels("train") == tiny_dataset.split_labels("train")
    assert [label.input_sha256 for label in subset.split_labels("validation")] == chosen
    answers = {
        label.input_sha256: label.analysis.model_copy(
            update={
                "requested_nodes": 100000,
                "requested_depth": None,
                "schema_version": 2,
                "adapter_version": "uci-teacher-v2",
                "move": sorted(legal_moves(label.analysis.snapshot.game().board, label.analysis.snapshot.game().turn))[
                    -1
                ],
            }
        )
        for label in subset.labels
    }
    derived = relabel(subset, answers)
    assert derived.parent_dataset_sha256 == subset.digest
    assert derived.sources == subset.sources
    assert [label.input_sha256 for label in derived.labels] == [label.input_sha256 for label in subset.labels]
    path = tmp_path / "relabeled.json"
    path.write_text(derived.model_dump_json())
    assert isinstance(load_dataset(path), RelabeledDataset)
    assert load_dataset(path) == derived
    assert tiny_dataset.model_dump_json() == before
    answers.pop(next(iter(answers)))
    with pytest.raises(ValueError, match="exactly"):
        relabel(subset, answers)


def test_relabel_rejects_changed_history_or_mixed_supervision(tiny_dataset):
    answers = {label.input_sha256: label.analysis for label in tiny_dataset.labels}
    key = next(iter(answers))
    answers[key] = answers[key].model_copy(update={"state_hash": "wrong"})
    with pytest.raises(ValueError, match="full-history"):
        relabel(tiny_dataset, answers)
    answers[key] = tiny_dataset.labels[0].analysis.model_copy(update={"requested_nodes": 999})
    with pytest.raises(ValueError, match="one teacher"):
        relabel(tiny_dataset, answers)
