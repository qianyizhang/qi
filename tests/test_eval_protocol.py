"""Spec execution, durable failures, replay validation, and independent scoring."""

import json
import subprocess
import sys
from dataclasses import asdict, fields, replace

import pytest
from typer.testing import CliRunner

from qi import evaluation, players
from qi.cli import app
from qi.evaluation import EvalRun, EvalSpec, run_evaluation, summarize_evaluation
from qi.experiments.evidence import check_choice
from qi.game import GameError, legal_moves
from qi.players import Decision, PlayerConfig
from qi.players.core import MctsStats, RootMove, SearchStats
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


@pytest.mark.parametrize(
    "corruption,reason",
    [
        (None, None),
        ("simulations", "MCTS simulation totals disagree"),
        ("root-visits", "Root visits disagree with simulations"),
        ("partition", "MCTS work does not partition total nodes"),
        ("root-actions", "root actions contain duplicates"),
        ("root-value", "finite mean value"),
        ("exchange", "exchange nodes overlap"),
        ("cache", "Search cache accounting"),
        ("cutoffs", "Search cutoffs"),
        ("extensions", "Search extensions"),
        ("max-extensions", "Search maximum extensions"),
        ("multiple", "MCTS simulation totals disagree"),
    ],
)
def test_diagnostics_have_same_meaning_at_all_boundaries(evidence, monkeypatch, corruption, reason):
    # Hand-counted evidence: two simulations charge two tree visits each.
    # Optional diagnostics have the same meaning regardless of player ID.
    entry = evidence.games[0]
    game = entry.match.opening.game()
    original = entry.match.turns[0].choice
    roots = tuple(
        RootMove(move, 2 if move == original.move else 0, 0.5 if move == original.move else None)
        for move in legal_moves(game.board, game.turn)
    )
    mcts = MctsStats(2, 4, 0, 0, 2, 0, 0, 1, roots)
    choice = replace(original, nodes=4, mcts=mcts, search_stats=SearchStats(cutoffs=1, tt_hits=2, tt_cutoffs=1))
    if corruption in ("simulations", "multiple"):
        choice = replace(choice, mcts=replace(mcts, simulations=3))
    elif corruption == "root-visits":
        choice = replace(
            choice, mcts=replace(mcts, root_moves=tuple(replace(row, visits=3) if row.visits else row for row in roots))
        )
    elif corruption == "partition":
        choice = replace(choice, mcts=replace(mcts, leaf_nodes=1))
    elif corruption == "root-actions":
        unvisited = next(row for row in roots if not row.visits)
        choice = replace(choice, mcts=replace(mcts, root_moves=(*roots, unvisited)))
    elif corruption == "root-value":
        choice = replace(
            choice,
            mcts=replace(
                mcts, root_moves=tuple(replace(row, mean_value=float("nan")) if row.visits else row for row in roots)
            ),
        )
    elif corruption == "exchange":
        choice = replace(choice, qnodes=1, search_stats=SearchStats(see_nodes=4))
    elif corruption == "cache":
        choice = replace(choice, search_stats=SearchStats(tt_hits=1, tt_cutoffs=2))
    elif corruption == "cutoffs":
        choice = replace(choice, search_stats=SearchStats(cutoffs=5))
    elif corruption == "extensions":
        choice = replace(choice, search_stats=SearchStats(extensions=-1))
    elif corruption == "max-extensions":
        choice = replace(choice, search_stats=SearchStats(max_extensions=5))
    if corruption == "multiple":
        choice = replace(choice, search_stats=SearchStats(cutoffs=-1))

    # All saved validation must remain usable with execution/catalog access disabled.
    def forbidden(*args, **kwargs):
        pytest.fail("Saved validation must not dispatch players or bind checkpoints.")

    monkeypatch.setattr(evaluation, "play_match", forbidden)
    monkeypatch.setattr(evaluation, "bind_config", forbidden)
    monkeypatch.setattr(evaluation, "get_player", forbidden)
    monkeypatch.setattr(players, "get_player", forbidden)
    config = entry.match.red
    raw = evidence.model_dump(mode="json")
    raw["games"][0]["match"]["turns"][0]["choice"] = asdict(choice)
    modified_match = replace(entry.match, turns=(replace(entry.match.turns[0], choice=choice), *entry.match.turns[1:]))
    modified = evidence.model_copy(
        update={"games": [entry.model_copy(update={"match": modified_match}), *evidence.games[1:]]}
    )

    def restore_arena():
        return EvalRun.model_validate(raw)

    def summarize_arena():
        return summarize_evaluation(modified)

    def restore_search():
        return check_choice(asdict(choice), asdict(config), game, original.player_version, match=True)

    for validate in (restore_arena, summarize_arena, restore_search):
        if reason:
            with pytest.raises(ValueError, match=reason):
                validate()
        else:
            validate()
    if reason is None:
        assert EvalRun.model_validate_json(restore_arena().model_dump_json()) == modified

    decision = Decision(**{field.name: getattr(choice, field.name) for field in fields(Decision)})
    player = players.Player(
        players.PlayerInfo(config.kind, original.player_version, "Fixture", "Fixture", False), lambda *_: decision
    )
    monkeypatch.setattr(players, "get_player", lambda *_: player)
    if reason:
        with pytest.raises(GameError, match=reason) as error:
            players.choose(game, config)
        assert error.value.code == "invalid_player_result"
    else:
        assert replace(players.choose(game, config), elapsed_ms=choice.elapsed_ms) == choice


@pytest.mark.parametrize("move,code", [("a0a9", "illegal_move"), ("bad", "invalid_move")])
def test_arena_retains_referee_transition_errors(evidence, move, code):
    entry = evidence.games[0]
    first = entry.match.turns[0]
    match = replace(
        entry.match, turns=(replace(first, choice=replace(first.choice, move=move)), *entry.match.turns[1:])
    )
    with pytest.raises(GameError) as error:
        evidence.validate_match(0, entry.model_copy(update={"match": match}))
    assert error.value.code == code
