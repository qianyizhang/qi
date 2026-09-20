"""Preparation configs pin generation inputs and preserve incomplete evidence."""

import json
import os
import sys
from pathlib import Path

import pytest
from qi_game.core import GameError
from typer.testing import CliRunner

from qi.cli import app
from qi.teacher import digest
from qi.training_data.assembly import Bucket, MixtureRecipe
from qi.training_data.config import PreparationConfig, SupervisionSettings, load_preparation, prepare_dataset
from qi.training_data.contracts import fingerprint
from qi.training_data.generation import teacher_spec
from qi.training_data.loading import load_dataset


@pytest.fixture
def preparation(data_setup, tmp_path):
    recipe, corpus, teacher, labeler, calls = data_setup
    path = tmp_path / "corpus.json"
    path.write_text(corpus.model_dump_json())
    spec = teacher_spec(teacher)
    config = PreparationConfig(
        corpus="corpus.json",
        corpus_sha256=corpus.digest,
        generation=recipe,
        supervision=SupervisionSettings(
            engine="fake-engine",
            network="fake-network",
            engine_sha256=spec["engine_sha256"],
            network_sha256=spec["network_sha256"],
            nodes=teacher.nodes,
            depth=teacher.depth,
        ),
        assembly=MixtureRecipe(
            id="configured-mixture",
            supervision_fingerprint=fingerprint("supervision-v1", spec),
            buckets=[
                Bucket(id=f"{mode}-{split}", modes=[mode], split=split, count=2)
                for mode in ("random", "teacher-guided")
                for split in ("train", "validation")
            ],
        ),
    )
    config_path = tmp_path / "preparation.json"
    config_path.write_text(config.model_dump_json())
    return load_preparation(config_path), labeler, calls


def test_saved_config_runs_both_modes_and_can_be_copied(preparation, tmp_path):
    config, labeler, _ = preparation
    output = tmp_path / "prepared"
    result = prepare_dataset(config, output, labeler=labeler)
    assert result["status"] == "complete"
    dataset = load_dataset(output / "dataset.json")
    assert len(dataset.labels) == 8
    assert {source.actor_spec["mode"] for source in dataset.library.sources} == {"random", "teacher-guided"}
    copied = load_preparation(output / "config.json")
    assert copied == config
    second = prepare_dataset(copied, tmp_path / "copy", labeler=labeler)
    assert second["dataset_manifest_fingerprint"] == result["dataset_manifest_fingerprint"]
    before = (output / "dataset.json").read_bytes()
    with pytest.raises(GameError, match="fresh"):
        prepare_dataset(config, output, labeler=labeler)
    assert (output / "dataset.json").read_bytes() == before


@pytest.mark.parametrize(
    "field,code",
    [
        ("engine_sha256", "teacher_mismatch"),
        ("corpus_sha256", "corpus_mismatch"),
        ("supervision_fingerprint", "supervision_mismatch"),
    ],
)
def test_wrong_pins_fail_before_generation(preparation, tmp_path, field, code):
    config, labeler, calls = preparation
    target = (
        config
        if field == "corpus_sha256"
        else (config.assembly if field == "supervision_fingerprint" else config.supervision)
    )
    setattr(target, field, "0" * 64)
    output = tmp_path / "refused"
    with pytest.raises(GameError) as error:
        prepare_dataset(config, output, labeler=labeler)
    assert error.value.code == code
    assert not output.exists() and not calls


def test_actor_teacher_budget_is_independent_of_supervision(preparation, tmp_path):
    config, labeler, calls = preparation
    config.actor_teacher = config.supervision.model_copy(update={"nodes": 101})
    result = prepare_dataset(config, tmp_path / "separate", labeler=labeler)
    assert result["status"] == "complete"
    dataset = load_dataset(tmp_path / "separate" / "dataset.json")
    assert {nodes for _, nodes in calls} == {100, 101}
    assert {example.analysis.requested_nodes for example in dataset.library.examples} == {100}


def test_partial_generation_and_quota_shortfall_are_retained(preparation, tmp_path):
    config, labeler, _ = preparation

    def failing(game, teacher):
        raise GameError("teacher_timeout", "bounded failure")

    output = tmp_path / "partial"
    result = prepare_dataset(config, output, labeler=failing)
    assert result["status"] == result["generation_status"] == "incomplete"
    assert (output / "library.json").exists() and not (output / "dataset.json").exists()
    assert "bounded failure" in json.loads((output / "summary.json").read_text())["failure"]
    config.assembly.buckets[0].count = 100
    quota_output = tmp_path / "shortfall"
    result = prepare_dataset(config, quota_output, labeler=labeler)
    assert result["status"] == "incomplete" and result["generation_status"] == "complete"
    with pytest.raises(ValueError, match="Incomplete mixture"):
        load_dataset(quota_output / "dataset.json")


def test_prepare_cli_uses_saved_config_and_reports_incompleteness(preparation, tmp_path, monkeypatch):
    config, labeler, _ = preparation
    path = tmp_path / "submitted.json"
    path.write_text(config.model_dump_json())
    monkeypatch.setattr(
        "qi.training_data.cli.prepare_dataset", lambda config, output: prepare_dataset(config, output, labeler=labeler)
    )
    result = CliRunner().invoke(app, ["data", "prepare", "--config", str(path), "--output", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "complete"
    config.assembly.buckets[0].count = 100
    path.write_text(config.model_dump_json())
    result = CliRunner().invoke(app, ["data", "prepare", "--config", str(path), "--output", str(tmp_path / "short")])
    assert getattr(result.exception, "code", None) == "preparation_incomplete"


@pytest.fixture
def executable_preparation(preparation, tmp_path):
    config, _, _ = preparation
    engine = Path(config.supervision.engine)
    engine.write_text(f"""#!{sys.executable}
import os, sys
from pathlib import Path
from qi_game.reference import replay, legal_moves
Path({str(tmp_path / "pid")!r}).write_text(str(os.getpid()))
queries = 0
for raw in sys.stdin:
    command = raw.strip()
    if command == 'uci':
        print('id name Test Teacher')
        for name in ('Threads', 'Hash', 'MultiPV', 'Ponder', 'EvalFile'):
            print('option name ' + name + ' type string')
        print('uciok', flush=True)
    elif command == 'isready':
        print('readyok', flush=True)
    elif command.startswith('position startpos'):
        moves = command.split()[3:]
    elif command.startswith('go '):
        queries += 1
        if Path({str(tmp_path / "fail")!r}).exists() and queries == 4:
            sys.exit(3)
        game = replay(tuple(moves))
        print('bestmove ' + sorted(legal_moves(game.board, game.turn))[0], flush=True)
""")
    engine.chmod(0o700)
    config.supervision.engine_sha256 = digest(engine)
    config.assembly.supervision_fingerprint = fingerprint("supervision-v1", teacher_spec(config.supervision.teacher()))
    config.actor_teacher = config.supervision.model_copy(update={"nodes": 101})
    return config


def test_persistent_preparation_matches_fresh_and_hashes_once(executable_preparation, tmp_path, monkeypatch):
    config = executable_preparation
    fresh = tmp_path / "fresh"
    assert prepare_dataset(config, fresh)["status"] == "complete"
    config.teacher_process = "persistent"
    hashes = []

    def counted(path):
        hashes.append(path)
        return digest(path)

    monkeypatch.setattr("qi.teacher.digest", counted)
    output = tmp_path / "persistent"
    assert prepare_dataset(config, output)["status"] == "complete"
    assert hashes == [Path(config.supervision.engine), Path(config.supervision.network)]
    before = load_dataset(fresh / "dataset.json").model_dump()
    after = load_dataset(output / "dataset.json").model_dump()
    for dataset in (before, after):
        for example in dataset["library"]["examples"]:
            example["analysis"].pop("elapsed_ms")
    assert before == after
    assert load_preparation(output / "config.json").teacher_process == "persistent"
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_persistent_preparation_retains_partial_evidence(executable_preparation, tmp_path):
    config = executable_preparation
    config.teacher_process = "persistent"
    (tmp_path / "fail").touch()
    output = tmp_path / "partial-session"
    result = prepare_dataset(config, output)
    assert result["status"] == result["generation_status"] == "incomplete"
    assert result["examples"] == 3
    assert "exited" in result["failure"]
    assert len(json.loads((output / "library.json").read_text())["examples"]) == 3
    assert not (output / "dataset.json").exists()
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_persistent_preparation_rejects_conflicting_actor_pins(executable_preparation, tmp_path):
    config = executable_preparation
    config.teacher_process = "persistent"
    config.actor_teacher.network_sha256 = "0" * 64
    with pytest.raises(GameError, match="differ"):
        prepare_dataset(config, tmp_path / "bad-pins")
    assert not (tmp_path / "bad-pins").exists()
    assert not (tmp_path / "pid").exists()
