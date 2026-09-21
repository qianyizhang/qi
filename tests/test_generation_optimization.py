"""The bounded worker study preserves identities and cleans up failed groups."""

import importlib.util
import json
import os
from pathlib import Path
from time import monotonic

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def study(monkeypatch):
    folder = ROOT / "data/experiments/generation_optimization_v1"
    monkeypatch.syspath_prepend(str(folder))
    spec = importlib.util.spec_from_file_location("optimization_study", folder / "study.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_partition_preserves_source_ids_and_game_indices(study):
    config = {"seed": 17, "sources": [{"id": str(i), "games": 4, "parent_trajectory": None} for i in range(4)]}
    parts = study.partitions(config)
    assert [[s["id"] for s in p["sources"]] for p in parts] == [["0", "2"], ["1", "3"]]
    assert all(p["seed"] == 17 and all(s["games"] == 4 for s in p["sources"]) for p in parts)
    with pytest.raises(ValueError):
        study.partitions({"sources": [{"parent_trajectory": "parent"}, {"parent_trajectory": None}]})


def test_process_memory_includes_descendants_not_unrelated_processes(study):
    rows = [(os.getpid(), 1, 1024), (10, os.getpid(), 2048), (11, 10, 4096), (12, 11, 512), (13, 1, 8192)]
    assert study.process_rss(rows, {10}) == 7.5


@pytest.mark.parametrize("limit", [1, 2])
def test_worker_limit_and_parallel_execution(study, tmp_path, limit):
    script = tmp_path / "worker.py"
    script.write_text("""import json, sys, time
from pathlib import Path
root, cell, limit = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
cell.mkdir()
lock = root / "exclusive"
if limit == 1:
    lock.mkdir()
else:
    (root / (cell.name + ".ready")).touch()
    deadline = time.monotonic() + 5
    while len(list(root.glob("*.ready"))) < 2:
        if time.monotonic() >= deadline: raise RuntimeError("second worker never started")
        time.sleep(0.01)
time.sleep(0.02)
if limit == 1: lock.rmdir()
(cell / "result.json").write_text(json.dumps({"complete": True}))
""")
    jobs = [(ROOT, script, [tmp_path, tmp_path / f"cell-{i}", limit], tmp_path / f"cell-{i}") for i in range(2)]
    rows, metrics = study.run_group(jobs, limit, tmp_path, monotonic() + 10)
    assert len(rows) == 2 and all(row["complete"] for row in rows)
    assert metrics["job_wall_seconds"] > 0


def test_failed_group_stops_remaining_worker_and_keeps_evidence(study, tmp_path):
    script = tmp_path / "worker.py"
    script.write_text("""import os, sys, time
from pathlib import Path
root, mode = Path(sys.argv[1]), sys.argv[2]
pid = root / "running.pid"
if mode == "wait":
    pid.write_text(str(os.getpid()))
    time.sleep(20)
else:
    deadline = time.monotonic() + 5
    while not pid.exists() and time.monotonic() < deadline: time.sleep(0.01)
    raise RuntimeError("intentional worker failure")
""")
    jobs = [(ROOT, script, [tmp_path, mode], tmp_path / mode) for mode in ("wait", "fail")]
    with pytest.raises(RuntimeError, match="Worker exited"):
        study.run_group(jobs, 2, tmp_path, monotonic() + 10)
    assert json.loads((tmp_path / "failure.json").read_text())["status"] == "incomplete"
    assert "intentional worker failure" in (tmp_path / "fail.log").read_text()
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "running.pid").read_text()), 0)


def test_combined_results_ignore_local_row_ids_and_reject_duplicate_sources(study, tmp_path):
    from qi.training_data.generation_runner import PolicyGenerationConfig, generate_policies
    from qi.training_data.store import Collection

    spec = importlib.util.spec_from_file_location("profile_fixtures", ROOT / study.PROFILE / "evidence.py")
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    inputs = tmp_path / "inputs"
    fixtures.prepare_controlled(inputs)
    config = PolicyGenerationConfig.model_validate_json((inputs / "controlled.json").read_text())
    source = config.sources[0].model_copy(update={"games": 1, "additional_plies": 8})
    config.sources = [source.model_copy(update={"id": name}) for name in ("a", "b")]
    config.seconds = 30
    full = tmp_path / "full.sqlite"
    with Collection(full) as store:
        generate_policies(store, config, provider=fixtures.fixture_provider)
    shards = []
    for index, value in enumerate(study.partitions(config.model_dump())):
        path = tmp_path / f"shard-{index}.sqlite"
        with Collection(path) as store:
            generate_policies(store, PolicyGenerationConfig.model_validate(value), provider=fixtures.fixture_provider)
        shards.append(path)
    assert study.combined(shards) == study.combined([full])
    with pytest.raises(ValueError, match="ownership overlaps"):
        study.combined([*shards, shards[0]])


def test_timeout_cleanup_tolerates_worker_exit_race(study, monkeypatch, tmp_path):
    class Exiting:
        pid = 123
        waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if timeout is not None:
                raise study.subprocess.TimeoutExpired("worker", timeout)
            return 0

    process = Exiting()

    def kill(_pid, sig):
        if sig == study.signal.SIGKILL:
            raise ProcessLookupError()

    monkeypatch.setattr(study.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(study.os, "killpg", kill)
    with pytest.raises(TimeoutError, match="allowance"):
        study.run_group([(ROOT, tmp_path / "worker.py", [], tmp_path / "cell")], 1, tmp_path, monotonic() - 1)
    assert process.waits == 2
    assert "allowance" in json.loads((tmp_path / "failure.json").read_text())["error"]
