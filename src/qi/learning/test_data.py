"""Data validation rejects leakage before optimization can consume any labels."""

import pytest
from pydantic import ValidationError

from qi.game import Game
from qi.learning.data import Dataset, reserved_inputs
from qi.players.policy.encoding import input_key


def test_splits_are_by_source_and_observations_are_disjoint(tiny_dataset):
    train = {label.input_sha256 for label in tiny_dataset.split_labels("train")}
    validation = {label.input_sha256 for label in tiny_dataset.split_labels("validation")}
    assert len(train) == 9 and len(validation) == 3
    assert not train & validation
    assert not (train | validation) & reserved_inputs(tiny_dataset.reserved_corpus)
    loaded = Dataset.model_validate_json(tiny_dataset.model_dump_json())
    assert loaded.digest == tiny_dataset.digest


@pytest.mark.parametrize(
    "corruption", ["duplicate", "reserved", "wrong_source", "illegal", "identity", "teacher", "split"]
)
def test_invalid_label_sets_are_rejected(tiny_dataset, corruption):
    data = tiny_dataset.model_dump()
    label = data["labels"][0]
    if corruption == "duplicate":
        data["labels"].append(label.copy())
    elif corruption == "reserved":
        label["analysis"]["snapshot"]["moves"] = []
        label["analysis"]["move"] = "b2e2"
        label["analysis"]["state_hash"] = Game().state_hash
        label["input_sha256"] = input_key(Game())
    elif corruption == "wrong_source":
        label["source_id"] = "missing"
    elif corruption == "illegal":
        label["analysis"]["move"] = "a0a9"
    elif corruption == "identity":
        label["input_sha256"] = "0" * 64
    elif corruption == "teacher":
        label["analysis"]["engine_sha256"] = "c" * 64
    else:
        for source in data["sources"]:
            source["split"] = "train"
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


def test_equivalent_boards_share_input_identity_despite_history():
    game = Game()
    repeated = game.apply("b0c2").apply("b9c7").apply("c2b0").apply("c7b9")
    assert game.state_hash != repeated.state_hash
    assert input_key(game) == input_key(repeated)
