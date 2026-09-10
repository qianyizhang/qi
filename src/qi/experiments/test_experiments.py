"""Saved evidence survives interruption and rejects false completion or identity."""

import json

import pytest

from qi.experiments import runner
from qi.experiments.evidence import load_run
from qi.experiments.glossary import load_glossary
from qi.experiments.inspect import inspect_decision, load_traces
from qi.experiments.model import Plan
from qi.experiments.report import report, summarize
from qi.protocol import Snapshot


def plan(games=False):
    return Plan(
        name="Small fixture",
        question="Does evidence retain its meaning?",
        corpus={
            "id": "test",
            "provenance": "Hermetic initial position.",
            "openings": [{"id": "initial", "description": "Initial board", "snapshot": Snapshot()}],
        },
        players=["alphabeta", "quiescence"],
        budgets=[8],
        seeds=[7],
        pairs=[("alphabeta", "quiescence")] if games else [],
        game_openings=["initial"] if games else [],
    )


def test_run_trace_and_report_recompute_evidence(tmp_path):
    directory = tmp_path / "run"
    assert runner.run(plan(), directory)["status"] == "complete"
    checked = load_run(directory)
    assert checked["completed"] == checked["planned"] == 2
    assert all(row["samples"] == row["expected"] == 1 for row in summarize(checked)["probes"])
    trace = directory / "traces/first.json"
    assert inspect_decision(directory, "unit-00000", 0, trace)["decision_equal"]
    assert load_traces(directory, checked)[0]["recording"]["complete"]
    result = report(directory, directory / "report.html")
    assert result["completed"] == 2
    assert "REPORT_DATA" not in (directory / "report.html").read_text()
    with pytest.raises(FileExistsError):
        runner.run(plan(), directory)
    with pytest.raises(ValueError, match="fresh trace"):
        inspect_decision(directory, "unit-00000", 0, trace)


def test_deadline_keeps_partial_game_without_inventing_a_draw(tmp_path):
    ticks = iter(range(100))
    directory = tmp_path / "run"
    status = runner.run(plan(games=True), directory, seconds=10, clock=lambda: next(ticks))
    assert status["status"] == "deadline"
    checked = load_run(directory)
    partial = checked["units"][-1]
    assert partial["job"]["kind"] == "game" and partial["status"] == "incomplete"
    assert len(partial["turns"]) > 0 and "outcome" not in partial
    assert summarize(checked)["matches"][0]["score_rate"] is None


def test_player_failure_preserves_previous_decisions(tmp_path, monkeypatch):
    original = runner.choose
    calls = 0

    def fail(game, config):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise RuntimeError("fixture failure")
        return original(game, config)

    monkeypatch.setattr(runner, "choose", fail)
    directory = tmp_path / "run"
    assert runner.run(plan(games=True), directory)["status"] == "failed"
    unit = load_run(directory)["units"][-1]
    assert unit["status"] == "failed" and len(unit["turns"]) == 1
    assert "fixture failure" in unit["error"]


@pytest.mark.parametrize(
    "field,value", [("state_hash", "wrong"), ("seed", -1), ("nodes", 999), ("player_version", "other")]
)
def test_altered_decision_is_rejected(tmp_path, field, value):
    directory = tmp_path / "run"
    runner.run(plan(), directory)
    path = directory / "units/unit-00000.json"
    unit = json.loads(path.read_text())
    unit["turns"][0]["choice"][field] = value
    runner.write_json(path, unit)
    with pytest.raises(ValueError):
        load_run(directory)


def test_missing_unit_cannot_be_presented_as_complete(tmp_path):
    directory = tmp_path / "run"
    runner.run(plan(), directory)
    (directory / "units/unit-00000.json").unlink()
    with pytest.raises(ValueError, match="missing units"):
        load_run(directory)


def test_trace_rejects_changed_code_and_missing_work(tmp_path, monkeypatch):
    from qi.experiments import inspect

    directory = tmp_path / "run"
    runner.run(plan(), directory)
    output = directory / "traces/trace.json"
    inspect_decision(directory, "unit-00000", 0, output)
    trace = json.loads(output.read_text())
    next(item for item in trace["recording"]["events"] if item["kind"] == "work")["visit"] = 999
    runner.write_json(output, trace)
    with pytest.raises(ValueError, match="work sequence"):
        load_traces(directory, load_run(directory))
    original = inspect.provenance()
    monkeypatch.setattr(inspect, "provenance", lambda: {**original, "source_sha256": "changed"})
    with pytest.raises(ValueError, match="Code or runtime changed"):
        inspect_decision(directory, "unit-00000", 0, directory / "other.json")


def test_unknown_source_identities_cannot_certify_trace_parity(tmp_path, monkeypatch):
    from qi.experiments import inspect

    directory = tmp_path / "run"
    runner.run(plan(), directory)
    output = directory / "traces/trace.json"
    inspect_decision(directory, "unit-00000", 0, output)
    trace = json.loads(output.read_text())
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["provenance"]["source_sha256"] = None
    runner.write_json(manifest_path, manifest)
    trace["source_sha256"] = None
    runner.write_json(output, trace)
    # Unknown identities may be recorded, but two unknowns do not prove equality.
    run = load_run(directory)
    with pytest.raises(ValueError, match="code identity missing"):
        load_traces(directory, run)
    original = inspect.provenance()
    monkeypatch.setattr(inspect, "provenance", lambda: {**original, "source_sha256": None})
    with pytest.raises(ValueError, match="known checkout source identity"):
        inspect_decision(directory, "unit-00000", 0, directory / "other.json")
    assert not (directory / "other.json").exists()


def test_html_embeds_untrusted_text_as_inert_data(tmp_path):
    specification = plan().model_copy(update={"question": "</script><script>alert('injected')</script>"})
    directory = tmp_path / "run"
    runner.run(specification, directory)
    report(directory, directory / "report.html")
    html = (directory / "report.html").read_text()
    assert "</script><script>alert" not in html
    assert "\\u003c/script>" in html
    payload = html.split('<script type="application/json" id="data">')[1].split("</script>")[0]
    assert json.loads(payload)["glossary"] == load_glossary()


def test_matrix_rejects_false_tactical_targets_and_duplicate_pairs():
    specification = plan().model_dump()
    specification["winning_moves"] = {"initial": ["b2e2"]}
    with pytest.raises(ValueError, match="immediate win"):
        Plan.model_validate(specification)
    specification = plan(games=True).model_dump()
    specification["pairs"] *= 2
    with pytest.raises(ValueError, match="duplicates"):
        Plan.model_validate(specification)


def test_committed_plan_embeds_the_reserved_corpus():
    from qi.evaluation import Corpus
    from qi.experiments.model import ROOT

    specification = Plan.model_validate_json((ROOT / "data/experiments/search-components-v1.json").read_text())
    corpus = Corpus.model_validate_json((ROOT / "data/evaluation/search-positions-v1.json").read_text())
    assert specification.corpus == corpus
    assert len(specification.winning_moves) == 2


def test_only_complete_color_pairs_contribute_outcomes():
    specification = plan(games=True)
    game_jobs = [job for job in specification.jobs() if job["kind"] == "game"]
    units = [
        {"status": "complete", "job": game_jobs[0], "outcome": {"winner": "red"}},
        {"status": "incomplete", "job": game_jobs[1]},
    ]
    data = {"manifest": {"plan": specification.model_dump(mode="json")}, "units": units}
    assert summarize(data)["matches"][0]["score_rate"] is None
    assert summarize(data)["unpaired_completed_games"] == 1
    units[1] = {"status": "complete", "job": game_jobs[1], "outcome": {"winner": None}}
    result = summarize(data)["matches"][0]
    assert (result["wins"], result["draws"], result["losses"], result["pairs"]) == (1, 1, 0, 1)
    assert result["score_rate"] == 0.75
    assert result["scorer"] == "game-score-v1"
    assert result["completed_pairs"] == result["planned_pairs"] == 1


def test_mcts_and_search_round_trip_without_player_execution(tmp_path, monkeypatch):
    from qi import players

    directory = tmp_path / "diagnostics"
    specification = plan().model_copy(update={"players": ["mcts", "mcts-quiescence", "alphabeta-enhanced"]})
    assert runner.run(specification, directory)["status"] == "complete"

    def forbidden(*args, **kwargs):
        pytest.fail("Saved evidence validation must not execute players or bind checkpoints.")

    monkeypatch.setattr(runner, "choose", forbidden)
    monkeypatch.setattr(players, "get_player", forbidden)
    monkeypatch.setattr(players, "bind_config", forbidden)
    checked = load_run(directory)
    assert checked["completed"] == checked["planned"] == 3
    assert checked["units"][0]["turns"][0]["choice"]["mcts"] is not None
    assert checked["units"][1]["turns"][0]["choice"]["mcts"] is not None
    assert checked["units"][2]["turns"][0]["choice"]["search_stats"] is not None
    path = directory / "units/unit-00000.json"
    unit = json.loads(path.read_text())
    unit["turns"][0]["choice"]["mcts"]["simulations"] += 1
    path.write_text(json.dumps(unit))
    with pytest.raises(ValueError, match="MCTS simulation totals disagree"):
        load_run(directory)
