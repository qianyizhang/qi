"""Optional torch integration: optimization, artifact integrity, and player adapters."""

import json
import subprocess

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.arena import play_match
from qi.game import Game, GameError, legal_moves
from qi.players import PlayerConfig, choose
from qi.protocol import Snapshot

torch = pytest.importorskip("torch", reason="Install the learning extra to run policy integration tests.")
from qi.learning.train import train  # noqa: E402
from qi.players.policy.encoding import action_id  # noqa: E402
from qi.players.policy.runtime import load_checkpoint  # noqa: E402


@pytest.fixture
def fitted(tmp_path, tiny_dataset):
    path = tmp_path / "policy.pt"
    report = train(tiny_dataset, path, steps=100, diagnostic_examples=4)
    return path, report


def test_overfit_reload_and_teacher_free_adapters(fitted, monkeypatch, tmp_path):
    path, report = fitted
    assert report["train"]["agreement"] == 1
    assert report["final_loss"] < report["initial_loss"] / 10
    assert report["reload_predictions_equal"]
    assert report["validation"]["legal_outputs"] == report["validation"]["positions"]
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(path))
    monkeypatch.setattr("qi.arena.platform", lambda: "test-platform")
    # INVARIANT: In-process policy play cannot call an external teacher.
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("Teacher subprocess during inference"))
    choice = choose(Game(), PlayerConfig("policy"))
    assert choice.move in legal_moves(Game().board, "red")
    assert choice.checkpoint_sha256 == report["checkpoint_sha256"]
    assert choice.model_calls == 1 and choice.nodes == 0
    with TestClient(create_app()) as client:
        metadata = client.get("/api/players").json()[-1]
        assert metadata["id"] == "policy" and metadata["checkpoint_sha256"] == choice.checkpoint_sha256
        response = client.post(
            "/api/opponent",
            json={"snapshot": Snapshot().model_dump(), "expected_state_hash": Game().state_hash, "player": "policy"},
        )
        assert response.status_code == 200
        assert response.json()["choice"]["move"] == choice.move
        stale = client.post(
            "/api/opponent",
            json={"snapshot": Snapshot().model_dump(), "expected_state_hash": "0" * 64, "player": "policy"},
        )
        assert stale.status_code == 409
    match = play_match(PlayerConfig("policy"), PlayerConfig("random", seed=9))
    assert match.snapshot.game().outcome.reason == match.reason
    assert match.red.checkpoint_sha256 == choice.checkpoint_sha256


def test_policy_cli_has_checkpoint_identity(fitted, monkeypatch, tmp_path):
    path, report = fitted
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(path))
    state = tmp_path / "game.json"
    state.write_text(Snapshot().model_dump_json())
    result = subprocess.run(
        ["qi", "choose", "--state", str(state), "--player", "policy"], text=True, capture_output=True, check=True
    )
    assert json.loads(result.stdout)["checkpoint_sha256"] == report["checkpoint_sha256"]


@pytest.mark.parametrize("corruption", ["architecture", "shape", "nan", "overlap", "garbage", "missing"])
def test_corrupt_checkpoints_fail_explicitly(fitted, tmp_path, corruption):
    original, _ = fitted
    path = tmp_path / f"{corruption}.pt"
    payload = torch.load(original, weights_only=True)
    if corruption == "architecture":
        payload["metadata"]["architecture"] = "unknown"
    elif corruption == "shape":
        payload["state_dict"]["0.weight"] = torch.zeros(1)
    elif corruption == "nan":
        payload["state_dict"]["0.weight"][0, 0] = float("nan")
    elif corruption == "overlap":
        payload["metadata"]["validation_inputs"] = payload["metadata"]["train_inputs"]
    if corruption == "garbage":
        path.write_bytes(b"not a checkpoint")
    elif corruption != "missing":
        torch.save(payload, path)
    with pytest.raises(GameError) as error:
        load_checkpoint(str(path))
    assert error.value.code == "invalid_checkpoint"


def test_mask_excludes_highest_illegal_logit_and_checkpoint_stays_pinned(fitted, monkeypatch):
    path, report = fitted
    payload = torch.load(path, weights_only=True)
    for tensor in payload["state_dict"].values():
        tensor.zero_()
    payload["state_dict"]["2.bias"][action_id("a0a9")] = 1000
    payload["state_dict"]["2.bias"][action_id("b2e2")] = 100
    other = path.with_name("mask.pt")
    torch.save(payload, other)
    monkeypatch.setenv("QI_POLICY_CHECKPOINT", str(other))
    choice = choose(Game(), PlayerConfig("policy"))
    assert choice.move == "b2e2"
    other.write_bytes(b"replaced after loading")
    again = choose(Game(), PlayerConfig("policy"))
    assert (again.move, again.checkpoint_sha256) == (choice.move, choice.checkpoint_sha256)
    with pytest.raises(GameError, match="pinned"):
        choose(Game(), PlayerConfig("policy", checkpoint_sha256=report["checkpoint_sha256"]))


def test_cpu_configuration_metrics_and_legacy_checkpoint_metadata(tiny_dataset, tmp_path):
    path = tmp_path / "cpu.pt"
    report = train(tiny_dataset, path, steps=10, threads=2)
    assert report["training_device"] == "cpu" and report["training_threads"] == 2
    assert report["status"] == "complete" and report["inference_device"] == "cpu"
    for split in ("train", "validation"):
        assert report[split]["cross_entropy"] >= 0
        assert 0 < report[split]["random_legal_agreement"] <= 1
    payload = torch.load(path, weights_only=True)
    del payload["metadata"]["training_device"]
    del payload["metadata"]["training_threads"]
    legacy = tmp_path / "legacy.pt"
    torch.save(payload, legacy)
    assert load_checkpoint(str(legacy)).metadata.training_device == "cpu"


def test_invalid_device_and_validation_subset_leave_no_checkpoint(tiny_dataset, tmp_path, monkeypatch):
    path = tmp_path / "rejected.pt"
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    with pytest.raises(GameError, match="MPS requires"):
        train(tiny_dataset, path, device="mps")
    with pytest.raises(GameError, match="training inputs only"):
        train(tiny_dataset, path, train_inputs=[tiny_dataset.split_labels("validation")[0].input_sha256])
    assert not path.exists()


def test_learning_curve_runs_same_seeds_and_held_out_inputs(tiny_dataset, tmp_path):
    from qi.learning.experiment import LearningPlan, run_experiment

    output = tmp_path / "curve"
    result = run_experiment(
        tiny_dataset, tiny_dataset.reserved_corpus, LearningPlan(sizes=[3, 6], seeds=[7, 17], steps=5), output
    )
    assert result["status"] == "complete" and len(result["trials"]) == 4
    manifest = json.loads((output / "manifest.json").read_text())
    assert json.loads((output / "summary.json").read_text()) == result
    for trial in result["trials"]:
        metadata = trial["report"]["metadata"]
        assert metadata["validation_inputs"] == manifest["validation_inputs"]
        assert metadata["train_inputs"] == manifest["ordered_train_inputs"][: trial["size"]]
        assert metadata["seed"] == trial["seed"]
    assert all(row["complete_seeds"] == 2 and "validation_agreement_mean" in row for row in result["curve"])
    with pytest.raises(GameError, match="fresh experiment"):
        run_experiment(tiny_dataset, tiny_dataset.reserved_corpus, LearningPlan(sizes=[3]), output)


@pytest.mark.parametrize("stop", ["deadline", "failure"])
def test_learning_curve_preserves_completed_work_on_stop(tiny_dataset, tmp_path, monkeypatch, stop):
    import importlib

    experiment = importlib.import_module("qi.learning.experiment")
    trainer = importlib.import_module("qi.learning.train")
    clock = [0.0]
    calls = []
    monkeypatch.setattr(importlib.import_module("qi.learning.runs"), "perf_counter", lambda: clock[0])

    def interrupted_train(*args, **kwargs):
        if calls:
            raise GameError("injected_failure", "test failure")
        report = train(*args, **kwargs)
        calls.append(report)
        if stop == "deadline":
            clock[0] = 601
        return report

    monkeypatch.setattr(trainer, "train", interrupted_train)
    output = tmp_path / stop
    plan = experiment.LearningPlan(sizes=[3], seeds=[7, 17], steps=2)
    if stop == "failure":
        with pytest.raises(GameError, match="test failure"):
            experiment.run_experiment(tiny_dataset, tiny_dataset.reserved_corpus, plan, output)
    else:
        experiment.run_experiment(tiny_dataset, tiny_dataset.reserved_corpus, plan, output)
    saved = json.loads((output / "summary.json").read_text())
    assert saved["status"] == ("failed" if stop == "failure" else "deadline")
    assert len(saved["trials"]) == 1
    assert saved["curve"] == [{"size": 3, "complete_seeds": 1, "expected_seeds": 2}]


def test_experiment_cli_preview_creates_no_output(tiny_dataset, tmp_path):
    from typer.testing import CliRunner

    from qi.cli import app

    data, corpus, output = tmp_path / "data.json", tmp_path / "corpus.json", tmp_path / "run"
    data.write_text(tiny_dataset.model_dump_json())
    corpus.write_text(tiny_dataset.reserved_corpus.model_dump_json())
    result = CliRunner().invoke(
        app,
        [
            "learn",
            "experiment",
            "--data",
            str(data),
            "--corpus",
            str(corpus),
            "--output",
            str(output),
            "--sizes",
            "3,6",
            "--preview",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["planned_trials"] == 6
    assert not output.exists()


def test_selected_dataset_runs_and_reloads_saved_config(tiny_dataset, tmp_path):
    from qi.learning.config import DataSettings, Recipe, TrainingSettings, load_recipe
    from qi.learning.runs import run_recipe
    from qi.training_data.loading import load_dataset
    from qi.training_data.selection import select_training

    selected = select_training(
        tiny_dataset, [label.input_sha256 for label in tiny_dataset.split_labels("train")[:2]], selection_id="two"
    )
    path = tmp_path / "selected.json"
    path.write_text(selected.model_dump_json())
    recipe = Recipe(data=DataSettings(dataset=str(path)), training=TrainingSettings(updates=2))
    source = tmp_path / "recipe.json"
    source.write_text(recipe.model_dump_json())
    result = run_recipe(recipe, selected, tmp_path / "run", source_config=source)
    saved = load_recipe(tmp_path / "run" / "config.json")
    assert load_dataset(type(path)(saved.data.dataset)).digest == selected.digest
    report = result["trials"][0]["report"]
    assert report["metadata"]["dataset_sha256"] == selected.digest
    assert report["train"]["positions"] == 2
    assert report["validation"]["positions"] == len(tiny_dataset.split_labels("validation"))
    assert report["reload_predictions_equal"]


def test_experiment_deadline_cli_exits_nonzero_and_retains_status(tiny_dataset, tmp_path):
    data, corpus, output = tmp_path / "data.json", tmp_path / "corpus.json", tmp_path / "run"
    data.write_text(tiny_dataset.model_dump_json())
    corpus.write_text(tiny_dataset.reserved_corpus.model_dump_json())
    result = subprocess.run(
        [
            "qi",
            "learn",
            "experiment",
            "--data",
            str(data),
            "--corpus",
            str(corpus),
            "--output",
            str(output),
            "--sizes",
            "3",
            "--total-seconds",
            "0.000000001",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "deadline"
    assert json.loads(result.stderr)["error"]["code"] == "experiment_incomplete"
    assert json.loads((output / "summary.json").read_text())["trials"] == []


def test_independent_checkpoint_bindings_paired_evaluation_and_pure_reload(fitted, monkeypatch, tmp_path):
    from qi.evaluation import Corpus, EvalRun, EvalSpec, Opening, run_evaluation
    from qi.players import bind_config, list_players

    first, _report = fitted
    payload = torch.load(first, weights_only=True)
    payload["state_dict"]["2.bias"][0] += 0.01
    second = tmp_path / "second.pt"
    torch.save(payload, second)
    configuration = tmp_path / "players.json"
    configuration.write_text(
        json.dumps(
            {
                "players": [
                    {"id": name, "label": name, "implementation": "policy", "checkpoint": str(path)}
                    for name, path in (("model-a", first), ("model-b", second))
                ]
            }
        )
    )
    monkeypatch.setenv("QI_PLAYERS_CONFIG", str(configuration))
    a, b = bind_config(PlayerConfig("model-a")), bind_config(PlayerConfig("model-b"))
    assert a.checkpoint_sha256 != b.checkpoint_sha256
    assert a.binding_sha256 != b.binding_sha256
    assert {entry.id for entry in list_players()} >= {"model-a", "model-b"}
    spec = EvalSpec(
        corpus=Corpus(
            id="binding-proof",
            provenance="Two distinct hermetic checkpoints",
            openings=[Opening(id="initial", description="Initial position", snapshot=Snapshot())],
        ),
        player_a=a,
        player_b=b,
    )
    result = run_evaluation(spec)
    assert result.schema_version == result.spec.schema_version == 2
    assert all(entry.status == "complete" and entry.match.schema_version == 2 for entry in result.games)
    for entry in result.games:
        for turn in entry.match.turns:
            config = entry.match.red if turn.side == "red" else entry.match.black
            assert turn.choice.checkpoint_sha256 == config.checkpoint_sha256
            assert turn.choice.binding_sha256 == config.binding_sha256
    raw = result.model_dump_json()
    monkeypatch.delenv("QI_PLAYERS_CONFIG")
    monkeypatch.setattr(
        "qi.players.policy.runtime.load_checkpoint", lambda *_: pytest.fail("Model loaded during validation")
    )
    monkeypatch.setattr("qi.players.choose", lambda *_: pytest.fail("Player executed during validation"))
    assert EvalRun.model_validate_json(raw) == result
