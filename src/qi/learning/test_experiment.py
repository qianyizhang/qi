"""Learning-curve plans preserve data boundaries without importing a trainer."""

import pytest
from pydantic import ValidationError

from qi.game import GameError
from qi.learning.experiment import LearningPlan, ordered_inputs, preview, summarize


def test_nested_subsets_are_seeded_training_only_and_keep_validation_fixed(tiny_dataset):
    plan = LearningPlan(sizes=[3, 6, 9])
    manifest = preview(tiny_dataset, tiny_dataset.reserved_corpus, plan)
    ordered = manifest["ordered_train_inputs"]
    assert ordered == ordered_inputs(tiny_dataset, 7)
    assert ordered != ordered_inputs(tiny_dataset, 8)
    assert len(set(ordered)) == 9
    assert not set(ordered) & set(manifest["validation_inputs"])
    sources = {label.input_sha256: label.source_id for label in tiny_dataset.labels}
    assert len({sources[key] for key in ordered[:3]}) == 3
    assert set(ordered[:3]) < set(ordered[:6]) < set(ordered)
    assert manifest["planned_trials"] == 9


def test_insufficient_data_and_stale_reserved_corpus_fail_before_execution(tiny_dataset):
    with pytest.raises(GameError, match="dataset has"):
        preview(tiny_dataset, tiny_dataset.reserved_corpus, LearningPlan())
    other = tiny_dataset.reserved_corpus.model_copy(update={"id": "changed"})
    with pytest.raises(GameError, match="exact evaluation corpus"):
        preview(tiny_dataset, other, LearningPlan(sizes=[3]))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sizes": [3, 3]},
        {"sizes": [6, 3]},
        {"sizes": [0]},
        {"seeds": [7, 7]},
        {"seeds": [-1]},
        {"device": "cuda"},
        {"total_seconds": 601},
    ],
)
def test_invalid_plans_are_rejected(kwargs):
    with pytest.raises(ValidationError):
        LearningPlan(**kwargs)


def test_partial_seed_groups_have_no_comparison_metrics():
    plan = LearningPlan(sizes=[3], seeds=[7, 17])
    trials = [{"size": 3, "report": {"status": "complete"}}, {"size": 3, "report": {"status": "deadline"}}]
    assert summarize(trials, plan) == [{"size": 3, "complete_seeds": 1, "expected_seeds": 2}]
