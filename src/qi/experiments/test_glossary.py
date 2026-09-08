"""The report's vocabulary remains tied to its authority and diagnostic contracts."""

from dataclasses import fields

import pytest

from qi.experiments.glossary import load_glossary
from qi.experiments.model import Plan
from qi.players.core import Choice, EvaluationBreakdown, MctsStats, PlayerConfig, RootMove, SearchStats
from qi.protocol import Snapshot


def test_glossary_covers_report_diagnostic_and_plan_fields():
    entries = load_glossary()["entries"]
    names = {name.casefold() for entry in entries for name in [entry["term"], *entry["aliases"]]}
    required = set(Plan.model_fields) | set(Snapshot.model_fields)
    for model in (Choice, EvaluationBreakdown, MctsStats, PlayerConfig, RootMove, SearchStats):
        required.update(field.name for field in fields(model))
    assert required <= names, f"Missing help: {required - names}"


@pytest.mark.parametrize(
    "bad_row",
    [
        "| Second | 二 | Conflicting meaning | None | first |",
        "| First | 一 | Duplicate | None | — |",
        "| Broken | Missing columns |",
    ],
)
def test_ambiguous_or_malformed_authority_fails_generation(tmp_path, bad_row):
    source = tmp_path / "glossary.md"
    source.write_text("## Terms\n| First | 一 | Meaning | None | alias |\n" + bad_row)
    with pytest.raises(ValueError):
        load_glossary(source)
