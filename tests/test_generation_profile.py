"""Measurement boundaries must exclude verification and preserve generated data."""

import importlib.util
import json
import sqlite3
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "data/experiments/generation_profile_v1/study.py"


def test_prepare_creates_its_own_fixture_assets(tmp_path):
    output = tmp_path / "inputs"
    subprocess.run(
        [sys.executable, str(STUDY), "prepare", "--output", str(output)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    config = json.loads((output / "controlled.json").read_text())
    teacher = config["teachers"]["teacher"]
    assert config["sources"][0]["games"] == 64
    for key in ("engine", "network"):
        path = Path(teacher[key])
        assert path.parent == output
        assert sha256(path.read_bytes()).hexdigest() == teacher[key + "_sha256"]


@pytest.mark.parametrize("arm", ["default", "native"])
def test_profile_matches_uninstrumented_data_and_excludes_verification(tmp_path, arm):
    if arm == "native":
        pytest.importorskip("qi_game_native")
    from qi_game.contracts import Snapshot

    from qi.evaluation import Corpus, Opening
    from qi.training_data.generation_runner import GenerationSource, GenerationTeacher, PolicyGenerationConfig

    engine, network = tmp_path / "engine", tmp_path / "network"
    engine.write_text("fixture engine")
    network.write_text("fixture network")
    teacher = GenerationTeacher(
        engine=str(engine),
        network=str(network),
        engine_sha256=sha256(engine.read_bytes()).hexdigest(),
        network_sha256=sha256(network.read_bytes()).hexdigest(),
        nodes=1000,
    )
    config = PolicyGenerationConfig(
        name="profile-test",
        seed=29,
        seconds=30,
        corpus=Corpus(
            id="initial",
            provenance="Disposable test",
            openings=[Opening(id="initial", description="Start", snapshot=Snapshot())],
        ),
        teachers={"teacher": teacher},
        actor_teacher="teacher",
        supervision=["teacher"],
        sources=[GenerationSource(id="test", games=2, split="train", additional_plies=12)],
    )
    path = tmp_path / "config.json"
    path.write_text(config.model_dump_json())
    rows = []
    for mode in ("timing", "profile"):
        output = tmp_path / mode
        subprocess.run(
            [
                sys.executable,
                str(STUDY),
                "worker",
                "--config",
                str(path),
                "--output",
                str(output),
                "--mode",
                mode,
                "--arm",
                arm,
            ],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        rows.append(json.loads((output / "result.json").read_text()))
    assert rows[0]["semantic_sha256"] == rows[1]["semantic_sha256"]
    assert rows[1]["pragmas"] == {"journal_mode": "wal", "synchronous": 2}
    assert rows[1]["spans"]["collection.append"]["calls"] == rows[1]["plies"] == 24
    assert 0 < rows[1]["unwrapped_seconds"] < rows[1]["wall_seconds"]
    functions = json.loads((tmp_path / "profile/functions/functions.json").read_text())
    assert not any(row["name"] == "semantic_records" for row in functions)
    if arm == "native":
        signatures = []
        for action_arm in ("python", "native", "raw-native"):
            action_output = tmp_path / action_arm
            subprocess.run(
                [
                    sys.executable,
                    "-O",
                    str(STUDY.with_name("actions.py")),
                    "--input",
                    str(tmp_path / "timing/semantic.json"),
                    "--output",
                    str(action_output),
                    "--arm",
                    action_arm,
                    "--repeats",
                    "1",
                ],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            signatures.append(json.loads((action_output / "result.json").read_text())["semantic_sha256"])
        assert len(set(signatures)) == 1
    else:
        subprocess.run(
            [
                sys.executable,
                str(STUDY),
                "run",
                "--config",
                str(path),
                "--output",
                str(tmp_path / "sweep"),
                "--arms",
                "default",
                "--modes",
                "timing,profile",
                "--rounds",
                "1",
            ],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        sweep = json.loads((tmp_path / "sweep/summary.json").read_text())
        assert sweep["sources_verified"]
        assert {row["semantic_sha256"] for row in sweep["results"]} == {rows[0]["semantic_sha256"]}
    before = (tmp_path / "profile/result.json").read_bytes()
    repeated = subprocess.run(
        [
            sys.executable,
            str(STUDY),
            "worker",
            "--config",
            str(path),
            "--output",
            str(tmp_path / "profile"),
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert repeated.returncode != 0
    assert (tmp_path / "profile/result.json").read_bytes() == before


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(STUDY.parent))
    spec = importlib.util.spec_from_file_location("generation_profile_study", STUDY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_instrumentation_restores_after_exception(study):
    from qi.profiling import Timings
    from qi.training_data.store import Collection

    connect, append = sqlite3.connect, Collection.append
    with pytest.raises(ValueError), study.instrument(Timings(), False):
        assert sqlite3.connect is not connect
        assert Collection.append is not append
        raise ValueError("stop")
    assert sqlite3.connect is connect
    assert Collection.append is append


def test_failed_sweep_retains_completed_results_and_bounds_timeout(study, monkeypatch, tmp_path):
    config = tmp_path / "config.json"
    config.write_text("{}")
    args = SimpleNamespace(
        output=tmp_path / "run",
        config=config,
        rounds=1,
        arms=["default", "native"],
        modes=["timing"],
        workload="controlled",
    )
    timeouts = []

    def fake_run(command, **kwargs):
        timeouts.append(kwargs["timeout"])
        if len(timeouts) == 2:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        output = Path(command[command.index("--output") + 1])
        output.mkdir()
        (output / "result.json").write_text(
            json.dumps(
                {
                    "wall_seconds": 1,
                    "plies": 1,
                    "selected": 1,
                    "semantic_sha256": "fixture",
                }
            )
        )

    ticks = iter([0, 0, 1199, 1200])
    monkeypatch.setattr(study, "perf_counter", lambda: next(ticks))
    monkeypatch.setattr(study.subprocess, "run", fake_run)
    with pytest.raises(subprocess.TimeoutExpired):
        study.run(args)
    assert timeouts == [180, 1]
    failure = json.loads((args.output / "failure.json").read_text())
    assert failure["status"] == "incomplete"
    assert len(failure["results"]) == 1
    assert not (args.output / "summary.json").exists()
    manifest = json.loads((args.output / "manifest.json").read_text())
    assert all(sha256((args.output / row["frozen"]).read_bytes()).hexdigest() == row["sha256"] for row in manifest)


@pytest.mark.parametrize(
    "flag,value", [("--arms", ""), ("--arms", "default,default"), ("--modes", "unknown"), ("--rounds", "0")]
)
def test_invalid_sweep_does_not_create_evidence(tmp_path, flag, value):
    output = tmp_path / "invalid"
    result = subprocess.run(
        [
            sys.executable,
            str(STUDY),
            "run",
            "--config",
            str(tmp_path / "missing.json"),
            "--output",
            str(output),
            flag,
            value,
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 2
    assert not output.exists()
