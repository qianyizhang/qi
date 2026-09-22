"""Real worker processes, durable SQLite shards, publication and recovery."""

import json
import os
import signal
import subprocess
import sys
from time import monotonic, sleep

import pytest
from qi_game.contracts import Snapshot

from qi.evaluation import Corpus, Opening
from qi.teacher import digest
from qi.training_data.collection_combine import combine_shards
from qi.training_data.generation_policies import ActorPolicy, SamplingPolicy
from qi.training_data.generation_runner import (
    GenerationSource,
    GenerationTeacher,
    PolicyGenerationConfig,
    generate_policies,
)
from qi.training_data.parallel_generation import (
    exclusive_lock,
    partitions,
    run_parallel,
    stop_workers,
    validate_parallel,
)
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, export_snapshot, verify_snapshot
from qi.training_data.store import Collection


@pytest.fixture
def config(tmp_path):
    engine = tmp_path / "teacher"
    engine.write_text(f"""#!{sys.executable}
import json, os, sys, time
from pathlib import Path
from qi_game.reference import replay, legal_moves
root = Path({str(tmp_path)!r})
with (root / 'starts').open('a') as f:
    f.write(str(os.getpid()) + '\\n')
moves, multipv = [], 1
for line in sys.stdin:
    line = line.strip()
    if line == 'uci':
        print('id name parallel-test')
        for name in ('Threads', 'Hash', 'MultiPV', 'Ponder', 'EvalFile'):
            print('option name ' + name + ' type string')
        print('uciok', flush=True)
    elif line == 'isready':
        print('readyok', flush=True)
    elif line.startswith('setoption name MultiPV'):
        multipv = int(line.split()[-1])
    elif line.startswith('position startpos'):
        moves = line.split()[3:]
    elif line.startswith('go '):
        if (root / 'fail').exists():
            print('bestmove a0a9', flush=True)
            continue
        while (root / 'hold').exists():
            time.sleep(.02)
        game = replay(tuple(moves))
        legal = sorted(legal_moves(game.board, game.turn))
        for i, move in enumerate(legal[:multipv]):
            print(f'info depth 3 multipv {{i+1}} score cp {{100-10*i}} nodes 100 pv {{move}}')
        print('bestmove ' + legal[0], flush=True)
    elif line == 'quit':
        break
""")
    engine.chmod(0o700)
    network = tmp_path / "network"
    network.write_bytes(b"test-network")
    teacher = GenerationTeacher(
        engine=str(engine),
        network=str(network),
        engine_sha256=digest(engine),
        network_sha256=digest(network),
        nodes=100,
        timeout_seconds=2.0,
    )
    return PolicyGenerationConfig(
        name="parallel-test",
        seconds=120.0,
        seed=17,
        corpus=Corpus(
            id="reserved",
            provenance="test",
            openings=[Opening(id="initial", description="initial", snapshot=Snapshot())],
        ),
        teachers={"main": teacher},
        actor_teacher="main",
        supervision=["main"],
        actor_audit_every=2,
        sources=[
            GenerationSource(
                id=name,
                games=2,
                split=split,
                additional_plies=8,
                actor=ActorPolicy(mode="random"),
                sampling=SamplingPolicy(phase_counts={"opening": 1}, min_spacing=1, min_ply=1),
            )
            for name, split in (("first", "train"), ("second", "validation"))
        ],
    )


def canonical(path):
    # Ignore local row IDs, random attempt IDs, wall timers and run envelopes.
    with Collection(path, readonly=True) as store:
        rows = []
        for row in store.db.execute("SELECT id,status,stop_reason FROM games ORDER BY logical_key,created"):
            game = store.game(row["id"])
            if row["status"] != "complete":
                continue
            occurrences = []
            for occurrence in store.db.execute(
                "SELECT id,ply_count,json(payload) AS data FROM position_occurrences "
                "WHERE game_id=? ORDER BY ply_count",
                (row["id"],),
            ):
                labels = [
                    json.loads(r[0])
                    for r in store.db.execute(
                        "SELECT json(payload) FROM analyses WHERE occurrence_id=? ORDER BY request", (occurrence["id"],)
                    )
                ]
                for label in labels:
                    if label.get("answer"):
                        label["answer"].pop("elapsed_ms")
                occurrences.append((occurrence["ply_count"], json.loads(occurrence["data"]), labels))
            rows.append((game.model_dump(exclude={"actor_ms"}), row["stop_reason"], occurrences))
        return rows


def test_parallel_matches_serial_preserves_identities_exports_and_reuses(tmp_path, config):
    serial = tmp_path / "serial.sqlite"
    with Collection(serial) as store:
        generate_policies(store, config)
    output = tmp_path / "parallel"
    result = run_parallel(config, output)
    assert result["generation_status"] == "complete" and result["games"] == 4
    assert canonical(serial) == canonical(output / "collection.sqlite")
    starts = (tmp_path / "starts").read_text()
    before = digest(output / "collection.sqlite")
    second = run_parallel(config, output, resume=True)
    assert second["reused_games"] == 4 and second["reused_publication"]
    assert (tmp_path / "starts").read_text() == starts
    assert digest(output / "collection.sqlite") == before
    # Portable attempts survive combination exactly; local SQL IDs may differ.
    with Collection(output / "collection.sqlite", readonly=True) as merged:
        attempts = {r[0] for r in merged.db.execute("SELECT attempt FROM analyses")}
        originals = set()
        for shard in sorted((output / "shards").glob("*/collection.sqlite")):
            with Collection(shard, readonly=True) as source:
                originals.update(r[0] for r in source.db.execute("SELECT attempt FROM analyses"))
        assert attempts == originals
        spec = merged.db.execute("SELECT identity FROM analysis_specs LIMIT 1").fetchone()[0]
        # Freeze explicit disjoint observations for one row in each split.
        choices = {}
        for split in ("train", "validation"):
            rows = merged.db.execute(
                "SELECT DISTINCT input_hash FROM position_occurrences o JOIN games g ON g.id=o.game_id "
                "WHERE g.split=? AND json_extract(o.payload,'$.metadata.selected')=1 ORDER BY input_hash",
                (split,),
            ).fetchall()
            choices[split] = [r[0] for r in rows]
        shared = set(choices["train"]) & set(choices["validation"])
        recipe = SelectionRecipe(
            version="sql-selection-v2",
            analysis_spec=spec,
            reserved_corpus=config.corpus,
            selected_only=True,
            excluded_inputs={h: "shared test observation" for h in shared},
            buckets=[SnapshotBucket(id=split, split=split, count=1) for split in choices],
        )
        export_snapshot(merged, recipe, tmp_path / "snapshot")
    assert verify_snapshot(tmp_path / "snapshot")["rows"] == 2


def test_worker_failure_retained_and_explicit_resume(tmp_path, config):
    (tmp_path / "fail").touch()
    output = tmp_path / "parallel"
    with pytest.raises(RuntimeError, match="worker"):
        run_parallel(config, output)
    assert not (output / "collection.sqlite").exists()
    assert json.loads((output / "latest.json").read_text())["status"] == "failed"
    (tmp_path / "fail").unlink()
    result = run_parallel(config, output, resume=True)
    assert result["games"] == 4
    with Collection(output / "collection.sqlite", readonly=True) as store:
        assert store.db.execute("SELECT count(*) FROM games WHERE status!='complete'").fetchone()[0] >= 1
        assert store.db.execute("SELECT count(*) FROM analyses WHERE status='failed'").fetchone()[0] >= 1
    for pid in (tmp_path / "starts").read_text().splitlines():
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid), 0)


@pytest.mark.parametrize("stop_signal", [signal.SIGINT, signal.SIGTERM])
def test_pool_interrupt_reaps_engines_and_resumes(tmp_path, config, stop_signal):
    # Two slots start; the third source stays queued until a slot is free.
    config.sources.append(config.sources[0].model_copy(update={"id": "third"}, deep=True))
    # A barrier proves simultaneous teacher lifetimes without a timing speed assertion.
    (tmp_path / "hold").touch()
    config_path = tmp_path / "config.json"
    config_path.write_text(config.model_dump_json())
    output = tmp_path / "parallel"
    command = [
        sys.executable,
        "scripts/run_generation_pilot.py",
        "--config",
        str(config_path),
        "--output",
        str(output),
        "--workers",
        "2",
    ]
    with (tmp_path / "driver.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            until = monotonic() + 15
            while monotonic() < until:
                starts = (tmp_path / "starts").read_text().splitlines() if (tmp_path / "starts").exists() else []
                if len(starts) >= 2:
                    break
                if process.poll() is not None:
                    pytest.fail((tmp_path / "driver.log").read_text())
                sleep(0.05)
            sleep(0.2)
            starts = (tmp_path / "starts").read_text().splitlines()
            assert len(starts) == 2
            process.send_signal(stop_signal)
            assert process.wait(timeout=10) != 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert not (output / "collection.sqlite").exists()
    for pid in starts:
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid), 0)
    (tmp_path / "hold").unlink()
    assert run_parallel(config, output, resume=True)["games"] == 6
    with Collection(output / "collection.sqlite", readonly=True) as store:
        assert store.db.execute("SELECT count(*) FROM games WHERE status='interrupted'").fetchone()[0] >= 1


def test_resume_refuses_config_and_implementation_drift(tmp_path, config, monkeypatch):
    from qi.training_data import parallel_generation as parallel

    output = tmp_path / "parallel"
    run_parallel(config, output)
    with pytest.raises(ValueError, match="identical"):
        run_parallel(config.model_copy(update={"seed": 99}), output, resume=True)
    original = parallel.provenance
    monkeypatch.setattr(parallel, "provenance", lambda: {**original(), "source_sha256": "different"})
    with pytest.raises(ValueError, match="identical"):
        run_parallel(config, output, resume=True)


def test_combine_rejects_conflict_without_publishing(tmp_path, config):
    # Teacher-best one-ply play is deterministic, so the two splits conflict exactly.
    for source in config.sources:
        source.games = 1
        source.additional_plies = 1
        source.actor = ActorPolicy(mode="plausible", candidate_count=1)
    output = tmp_path / "parallel"
    with pytest.raises(ValueError, match="trajectory crosses splits"):
        run_parallel(config, output)
    assert not (output / "collection.sqlite").exists()
    assert len(list((output / "shards").glob("*/collection.sqlite"))) == 2


def test_combine_rejects_tampered_occurrence(tmp_path, config):
    config.sources = [config.sources[0]]
    shard = tmp_path / "shard.sqlite"
    with Collection(shard) as source:
        generate_policies(source, config)
        source.db.execute("DROP TRIGGER occurrence_identity")
        with source.db:
            source.db.execute(
                "UPDATE position_occurrences SET input_hash='wrong' WHERE id=(SELECT min(id) FROM position_occurrences)"
            )
    with pytest.raises(ValueError, match="Occurrence differs"):
        combine_shards([shard], [config], tmp_path / "pending.sqlite")


def test_parallel_boundaries_and_locks(tmp_path, config):
    assert [c.sources[0].id for c in partitions(config)] == ["first", "second"]
    with pytest.raises(ValueError, match="OS-write guard"):
        validate_parallel(config, {"max_write_bytes": 100})
    with pytest.raises(ValueError, match="independent sources"):
        partitions(config.model_copy(update={"sources": config.sources[:1]}))
    lock = tmp_path / "lock"
    with exclusive_lock(lock), pytest.raises(ValueError, match="already has a writer"):
        with exclusive_lock(lock):
            pass


def test_stop_worker_exit_race():
    class Exited:
        pid = 99999999

        def poll(self):
            return 0

        def wait(self, **kwargs):
            return 0

    stop_workers([Exited()])


def test_completed_shard_work_survives_coordinator_failure(tmp_path, config, monkeypatch):
    from qi.training_data import parallel_generation as parallel

    output = tmp_path / "parallel"
    real = parallel.run_workers

    def stop_after_game(configs, output, execution, *args):
        shard = output / "shards/source-0"
        shard.mkdir(parents=True)

        def event(value):
            if value["kind"] == "completed-game":
                raise KeyboardInterrupt("after durable completion")

        with Collection(shard / "collection.sqlite") as store:
            generate_policies(store, configs[0], event=event)

    monkeypatch.setattr(parallel, "run_workers", stop_after_game)
    with pytest.raises(KeyboardInterrupt):
        run_parallel(config, output)
    with Collection(output / "shards/source-0/collection.sqlite", readonly=True) as store:
        attempt = store.db.execute("SELECT attempt FROM games WHERE status='complete'").fetchone()[0]
    monkeypatch.setattr(parallel, "run_workers", real)
    result = run_parallel(config, output, resume=True)
    assert result["reused_games"] == 1
    with Collection(output / "collection.sqlite", readonly=True) as store:
        assert store.db.execute("SELECT count(*) FROM games WHERE attempt=?", (attempt,)).fetchone()[0] == 1


def test_publication_crash_is_recoverable_and_modified_output_is_preserved(tmp_path, config, monkeypatch):
    from qi.training_data import parallel_generation as parallel

    output = tmp_path / "parallel"
    link = parallel.os.link

    def interrupted(*_):
        raise KeyboardInterrupt("before publication")

    monkeypatch.setattr(parallel.os, "link", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_parallel(config, output)
    starts = (tmp_path / "starts").read_text()
    assert not (output / "collection.sqlite").exists()
    monkeypatch.setattr(parallel.os, "link", link)
    assert run_parallel(config, output, resume=True)["reused_games"] == 4
    assert (tmp_path / "starts").read_text() == starts
    with Collection(output / "collection.sqlite") as store:
        with store.db:
            store.db.execute("UPDATE generation_runs SET failure='external annotation'")
    before = digest(output / "collection.sqlite")
    with pytest.raises(ValueError, match="will not be overwritten"):
        run_parallel(config, output, resume=True)
    assert digest(output / "collection.sqlite") == before


def test_parallel_preview_and_unsupported_guards_create_no_output(tmp_path, config):
    config_path = tmp_path / "config.json"
    config_path.write_text(config.model_dump_json())
    output = tmp_path / "out"
    command = [
        sys.executable,
        "scripts/run_generation_pilot.py",
        "--config",
        str(config_path),
        "--output",
        str(output),
        "--workers",
        "2",
    ]
    preview = subprocess.run([*command, "--preview"], capture_output=True, text=True)
    assert preview.returncode == 0 and json.loads(preview.stdout)["workers"] == 2
    refused = subprocess.run([*command, "--max-write-gb", "1"], capture_output=True, text=True)
    assert refused.returncode != 0 and "OS-write guard" in refused.stderr
    assert not output.exists() and not (tmp_path / "starts").exists()


def test_combination_preserves_first_success_and_analysis_attempts(tmp_path, config):
    from qi.training_data.store import AnalysisPayload

    config = partitions(config)[0]
    shard = tmp_path / "shard.sqlite"
    with Collection(shard) as source:
        generate_policies(source, config)
        row = source.db.execute(
            "SELECT occurrence_id,spec_id,attempt,json(payload) AS data FROM analyses "
            "WHERE status='success' ORDER BY success_order LIMIT 1"
        ).fetchone()
        answer = AnalysisPayload.model_validate_json(row["data"]).answer
        attempt = source.begin_analysis(row["occurrence_id"], row["spec_id"])
        source.finish_analysis(attempt, answer)
        identity = source.db.execute(
            "SELECT identity FROM position_occurrences WHERE id=?", (row["occurrence_id"],)
        ).fetchone()[0]
        attempts = {r[0] for r in source.db.execute("SELECT attempt FROM analyses")}
        first = row["attempt"]
    combined_path = tmp_path / "combined.sqlite"
    combine_shards([shard], [config], combined_path)
    with Collection(combined_path, readonly=True) as combined:
        assert attempts == {r[0] for r in combined.db.execute("SELECT attempt FROM analyses")}
        row = combined.db.execute(
            "SELECT a.attempt FROM analyses a JOIN position_occurrences o ON a.occurrence_id=o.id "
            "WHERE o.identity=? AND a.status='success' ORDER BY a.success_order LIMIT 1",
            (identity,),
        ).fetchone()
        assert row[0] == first


def test_shared_deadline_expires_before_teacher_query(tmp_path, config):
    from qi_game.core import GameError

    with Collection(tmp_path / "deadline.sqlite") as store:
        with pytest.raises(GameError, match="allowance exhausted"):
            generate_policies(store, config, deadline=monotonic() - 1)
        assert store.counts()["games"] == 0
    assert not (tmp_path / "starts").exists()


def test_requested_pool_rss_guard_fails_closed(tmp_path, config, monkeypatch):
    from qi_game.core import GameError

    from qi.training_data import parallel_generation as parallel

    monkeypatch.setattr(
        parallel,
        "pool_resources",
        lambda *args: {"process": {"available": False}, "disk_write_bytes": None, "peak_sampled_combined_rss_bytes": 0},
    )
    with pytest.raises(GameError, match="unavailable"):
        run_parallel(config, tmp_path / "parallel", limits={"max_rss_bytes": 1000000000})
    assert not (tmp_path / "starts").exists()
