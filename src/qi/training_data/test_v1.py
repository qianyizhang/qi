"""Data validation rejects leakage before optimization can consume any labels."""

import pytest
from pydantic import ValidationError
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves

from qi.players.policy.encoding import input_key
from qi.teacher import TeacherConfig
from qi.training_data.v1 import Dataset, generate, reserved_inputs


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


def test_scaled_parallel_generation_preserves_serial_selection_and_splits(tiny_dataset, tmp_path):
    teacher = TeacherConfig(tmp_path / "fake-engine", tmp_path / "fake-network")

    def labeler(game, config):
        return tiny_dataset.labels[0].analysis.model_copy(
            update={
                "snapshot": Snapshot(moves=list(game.moves)),
                "state_hash": game.state_hash,
                "move": sorted(legal_moves(game.board, game.turn))[0],
            }
        )

    kwargs = dict(seed=211, games=72, plies=24, samples=16, labeler=labeler)
    serial = generate(tiny_dataset.reserved_corpus, teacher, **kwargs)
    parallel = generate(tiny_dataset.reserved_corpus, teacher, workers=4, **kwargs)
    assert len(serial.sources) > 64 and len(serial.labels) > 1024
    assert parallel.digest == serial.digest
    assert len({label.input_sha256 for label in serial.labels}) == len(serial.labels)
    assert Dataset.model_validate_json(parallel.model_dump_json()).digest == serial.digest


@pytest.mark.parametrize("kwargs", [{"games": 2049}, {"workers": 0}, {"workers": 5}, {"seconds": 7201}])
def test_generation_limits_reject_before_teacher_calls(tiny_dataset, tmp_path, kwargs):
    teacher = TeacherConfig(tmp_path / "fake-engine", tmp_path / "fake-network")
    with pytest.raises(GameError, match="4-2048"):
        generate(tiny_dataset.reserved_corpus, teacher, labeler=lambda *_: pytest.fail("Unexpected query"), **kwargs)
