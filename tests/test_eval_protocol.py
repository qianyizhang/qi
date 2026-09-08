"""Spec execution, durable failures, replay validation, and independent scoring."""

import json
import subprocess
import sys
from dataclasses import replace

import pytest
from typer.testing import CliRunner

from qi import evaluation
from qi.cli import app
from qi.evaluation import EvalRun, EvalSpec, run_evaluation, summarize_evaluation
from qi.players import PlayerConfig
from qi.protocol import Snapshot


@pytest.fixture(scope="module")
def spec():
    return EvalSpec(
        corpus={
            "id": "test",
            "provenance": "Hermetic paired test.",
            "openings": [
                {"id": "initial", "description": "Initial board", "snapshot": Snapshot()},
            ],
        },
        player_a=PlayerConfig("random", seed=8),
        player_b=PlayerConfig("random", seed=9),
    )


@pytest.fixture(scope="module")
def evidence(spec):
    return run_evaluation(spec)


def test_round_trip_summary_replays_without_search(evidence, monkeypatch):
    def forbidden(*args):
        pytest.fail("Summarization must not run engines.")

    monkeypatch.setattr(evaluation, "play_match", forbidden)
    restored = EvalRun.model_validate_json(evidence.model_dump_json())
    summary = summarize_evaluation(restored)
    assert summary.status == "complete"
    assert summary.spec_sha256 == restored.spec.digest
    a, b = summary.players["a"], summary.players["b"]
    wins = sum(entry.match.winner == entry.a_side for entry in restored.games)
    draws = sum(entry.match.winner is None for entry in restored.games)
    assert a.score_rate == (wins + 0.5 * draws) / 2
    assert a.score_rate + b.score_rate == 1
    assert a.wins == b.losses and a.draws == b.draws
    assert restored.games[0].match.red == restored.games[1].match.black


@pytest.mark.parametrize("field", ["digest", "outcome", "moves", "budget", "latency", "version", "slots"])
def test_tampered_evidence_is_rejected(evidence, field):
    raw = evidence.model_dump(mode="json")
    match = raw["games"][0]["match"]
    if field == "digest":
        raw["spec"]["player_a"]["nodes"] += 1
    elif field == "outcome":
        match["reason"] = "invented"
    elif field == "moves":
        match["turns"].pop()
    elif field == "budget":
        match["turns"][0]["choice"]["nodes"] = 100000
    elif field == "latency":
        match["turns"][0]["choice"]["elapsed_ms"] = -1
    elif field == "version":
        match["turns"][0]["choice"]["player_version"] = "invented"
    else:
        raw["games"][1] = raw["games"][0]
    with pytest.raises(ValueError):
        EvalRun.model_validate(raw)


@pytest.mark.parametrize(
    "error,status", [(RuntimeError("engine failed"), "failed"), (KeyboardInterrupt(), "incomplete")]
)
def test_failure_keeps_completed_partner_but_no_score(spec, evidence, monkeypatch, error, status):
    calls = 0
    saved = []

    def fail_second(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise error
        return evidence.games[0].match

    monkeypatch.setattr(evaluation, "play_match", fail_second)
    run = run_evaluation(spec, save=lambda run: saved.append(run.model_dump_json()))
    assert EvalRun.model_validate_json(saved[-1]) == run
    summary = summarize_evaluation(run)
    assert summary.status == status
    assert summary.players["a"].score_rate is None
    assert summary.players["a"].unpaired_completed_games == 1
    assert run.games[1].error
    assert any('"status":"running"' in snapshot for snapshot in saved)


def test_spec_identity_includes_budgets_and_rejects_unknown_protocol(spec):
    changed = spec.model_copy(update={"player_a": replace(spec.player_a, nodes=64)})
    assert changed.digest != spec.digest
    with pytest.raises(ValueError):
        EvalSpec.model_validate({**spec.model_dump(), "protocol": "elo"})


def test_cli_persists_evidence_and_recomputes_summary(spec, evidence, tmp_path, monkeypatch):
    matches = iter(entry.match for entry in evidence.games)
    monkeypatch.setattr(evaluation, "play_match", lambda *args: next(matches))
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(spec.model_dump_json())
    output = tmp_path / "run"
    runner = CliRunner()
    first = runner.invoke(app, ["eval", "run", "--spec", str(spec_path), "--output", str(output)])
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, ["eval", "summarize", "--run", str(output / "run.json")])
    assert second.exit_code == 0, second.output
    assert json.loads(first.stdout) == json.loads(second.stdout)
    before = (output / "run.json").read_bytes()
    assert runner.invoke(app, ["eval", "run", "--spec", str(spec_path), "--output", str(output)]).exit_code != 0
    assert (output / "run.json").read_bytes() == before


def test_cli_failure_is_nonzero_and_saved(spec, tmp_path, monkeypatch):
    def fail(*args):
        raise RuntimeError("engine failed")

    monkeypatch.setattr(evaluation, "play_match", fail)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(spec.model_dump_json())
    output = tmp_path / "run"
    result = CliRunner().invoke(app, ["eval", "run", "--spec", str(spec_path), "--output", str(output)])
    assert result.exit_code == 1
    run = EvalRun.model_validate_json((output / "run.json").read_text())
    assert run.games[0].status == "failed" and run.games[1].status == "pending"
    assert json.loads(result.stdout)["players"]["a"]["score_rate"] is None


def test_process_failure_exit_preserves_structured_evidence(spec, tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(spec.model_dump_json())
    output = tmp_path / "run"
    script = """
from qi import evaluation
from qi.cli import main
def fail(*args):
    raise RuntimeError('engine failed')
evaluation.play_match = fail
main()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, "eval", "run", "--spec", str(spec_path), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"]["code"] == "evaluation_failed"
    assert json.loads(result.stdout)["status"] == "failed"
    assert EvalRun.model_validate_json((output / "run.json").read_text()).games[0].status == "failed"
