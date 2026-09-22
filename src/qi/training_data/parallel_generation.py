"""Opt-in two-process policy generation with durable shards and atomic publication."""

import argparse
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
from collections import Counter
from contextlib import ExitStack, contextmanager
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

from qi_game.core import GameError

from qi.artifacts import ROOT, provenance, write_json
from qi.teacher import digest
from qi.training_data.collection_combine import combine_shards
from qi.training_data.generation_runner import PolicyGenerationConfig, generate_policies, pin_teachers
from qi.training_data.resource_probe import enforce_resources
from qi.training_data.snapshots import SnapshotReader, export_snapshot, verify_snapshot
from qi.training_data.store import Collection


@contextmanager
def interrupt_on_termination():
    """Let SIGTERM take the same retained-cleanup path as Ctrl-C."""
    previous = signal.getsignal(signal.SIGTERM)

    def interrupt(*_):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        raise KeyboardInterrupt("Generation terminated")

    signal.signal(signal.SIGTERM, interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@contextmanager
def exclusive_lock(path):
    with Path(path).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Generation output or collection already has a writer.") from None
        yield


def partitions(config):
    if len(config.sources) < 2 or any(s.parent_trajectory is not None for s in config.sources):
        raise ValueError(
            "Parallel generation requires at least two independent sources; generated parents use serial execution."
        )
    return [config.model_copy(update={"sources": [source]}, deep=True) for source in config.sources]


def validate_parallel(config, limits):
    partitions(config)
    if limits.get("max_write_bytes") is not None:
        raise ValueError("The OS-write guard is not yet supported across worker processes; use serial execution.")


def archive_sources(directory):
    files = [ROOT / "pyproject.toml", ROOT / "uv.lock", ROOT / "scripts/run_generation_pilot.py"]
    files.extend((ROOT / "src/qi").rglob("*.py"))
    files.extend(
        p
        for p in (ROOT / "packages").rglob("*")
        if p.suffix in {".py", ".hpp", ".cpp", ".toml"} and "build" not in p.parts
    )
    hashes = {}
    for path in sorted(set(files)):
        relative = path.relative_to(ROOT)
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        hashes[str(relative)] = digest(target)
    return hashes


def pool_resources(processes, peak=0):
    """Sample coordinator, workers and descendants; RSS may double-count shared pages."""
    try:
        table = subprocess.check_output(
            ["ps", "-axo", "pid=,ppid=,rss="], text=True, stderr=subprocess.DEVNULL, timeout=3
        )
        rows = [tuple(map(int, line.split())) for line in table.splitlines()]
    except (OSError, subprocess.SubprocessError):
        return {"process": {"available": False}, "disk_write_bytes": None, "peak_sampled_combined_rss_bytes": peak}
    selected = {p.pid for p in processes}
    while True:
        children = {pid for pid, parent, _ in rows if parent in selected}
        if children <= selected:
            break
        selected |= children
    rss = sum(rss for pid, _, rss in rows if pid in selected or pid == os.getpid()) * 1024
    return {
        "process": {"available": True},
        "disk_write_bytes": None,
        "sampled_combined_rss_bytes": rss,
        "peak_sampled_combined_rss_bytes": max(peak, rss),
    }


def stop_workers(processes):
    # Interrupt Python first so its finally blocks close/reap teacher children.
    for process in processes:
        if process.poll() is None:
            try:
                process.send_signal(signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = monotonic() + 3
    for process in processes:
        try:
            process.wait(timeout=max(0.01, deadline - monotonic()))
        except subprocess.TimeoutExpired:
            pass
        # A crashed worker may leave a teacher in its process group.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_workers(configs, output, execution, deadline, limits, origin):
    active, results = {}, {}
    next_source, peak = 0, 0
    started = monotonic()
    sample = {}
    with ExitStack() as logs:
        try:
            while active or next_source < len(configs):
                if monotonic() >= deadline:
                    raise GameError("dataset_timeout", "Parallel invocation allowance exhausted.")
                sample = pool_resources(active, peak)
                peak = sample["peak_sampled_combined_rss_bytes"]
                enforce_resources(sample, limits, shutil.disk_usage(output).free)
                # Poll before dispatch: a failure prevents any further source starts.
                for process, index in list(active.items()):
                    code = process.poll()
                    if code is None:
                        continue
                    if code:
                        raise RuntimeError(
                            f"Source worker {index} exited {code}; see {execution / f'worker-{index}.log'}"
                        )
                    result = json.loads((execution / f"worker-{index}" / "summary.json").read_text())
                    if result.get("generation_status") != "complete" or result.get("source_sha256") != origin:
                        raise ValueError("Worker did not complete under the frozen implementation.")
                    results[index] = result
                    # No engine descendants may survive a successful worker either.
                    stop_workers([process])
                    del active[process]
                while len(active) < 2 and next_source < len(configs):
                    index = next_source
                    next_source += 1
                    shard = output / "shards" / f"source-{index}"
                    shard.mkdir(parents=True, exist_ok=True)
                    config_path = shard / "config.json"
                    if config_path.exists():
                        if json.loads(config_path.read_text()) != configs[index].model_dump():
                            raise ValueError("Shard config differs from the frozen source.")
                    else:
                        write_json(config_path, configs[index].model_dump(), indent=2)
                    worker_output = execution / f"worker-{index}"
                    worker_output.mkdir()
                    log = logs.enter_context((execution / f"worker-{index}.log").open("x"))
                    command = [
                        sys.executable,
                        "-m",
                        "qi.training_data.parallel_generation",
                        "--config",
                        str(config_path),
                        "--store",
                        str(shard / "collection.sqlite"),
                        "--output",
                        str(worker_output),
                        "--deadline",
                        str(deadline),
                        "--source-sha256",
                        origin,
                    ]
                    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    active[process] = index
                write_json(
                    execution / "progress.json",
                    {
                        "active_sources": sorted(active.values()),
                        "completed_sources": sorted(results),
                        "resources": sample,
                    },
                    indent=2,
                )
                if active:
                    sleep(0.1)
        finally:
            stop_workers(list(active))
            write_json(
                execution / "pool.json",
                {"completed_sources": sorted(results), "resources": sample, "seconds": monotonic() - started},
                indent=2,
            )
    return [results[i] for i in range(len(configs))], sample


def _export(collection, export, execution, summary):
    if export is None:
        return
    started = monotonic()
    destination = execution / "snapshot"
    with Collection(collection, readonly=True) as store:
        manifest = export_snapshot(store, export, destination)
    verify_snapshot(destination)
    rows = sum(len(batch) for batch in SnapshotReader(destination).batches(128))
    summary["snapshot"] = {"path": str(destination), "rows": manifest["rows"], "read_rows": rows}
    summary["export_seconds"] = monotonic() - started


def run_parallel(config, output: Path, *, resume=False, export=None, limits=None):
    """Own an output directory; completed publication is immutable to this runner."""
    limits = limits or {}
    validate_parallel(config, limits)
    if export is not None and (not export.selected_only or export.reserved_corpus != config.corpus):
        raise ValueError("Parallel exports require selected_only and the same frozen corpus.")
    pin_teachers(config)
    origin = provenance()
    if not origin["source_sha256"]:
        raise ValueError("Parallel generation currently requires a source-and-lockfile checkout.")
    output = output.resolve()
    if not resume:
        output.mkdir(parents=True, exist_ok=False)
    collection = output / "collection.sqlite"
    with (
        interrupt_on_termination(),
        exclusive_lock(output / "pool.lock"),
        exclusive_lock(output / "collection.sqlite.writer.lock"),
    ):
        frozen = {
            "version": "parallel-generation-v1",
            "workers": 2,
            "config": config.model_dump(),
            "export": export.model_dump() if export else None,
            "resource_limits": limits,
            "source_sha256": origin["source_sha256"],
            "python": origin["python"],
            "packages": origin["packages"],
        }
        if resume:
            if json.loads((output / "frozen.json").read_text()) != frozen:
                raise ValueError(
                    "Parallel resume requires identical config, implementation, runtime, export and resource limits."
                )
        else:
            write_json(output / "frozen.json", frozen, indent=2)
        execution = output / "executions" / uuid4().hex
        execution.mkdir(parents=True)
        hashes = archive_sources(execution / "source")
        write_json(execution / "provenance.json", {"runtime": origin, "source_files": hashes}, indent=2)
        if provenance()["source_sha256"] != origin["source_sha256"]:
            raise ValueError("Source changed during archive.")
        started = monotonic()
        deadline = started + config.seconds
        summary = {"status": "failed", "collection": str(collection), "workers": 2}
        try:

            def check():
                if monotonic() >= deadline:
                    raise GameError("dataset_timeout", "Parallel generation/combination allowance exhausted.")
                sample = pool_resources(())
                enforce_resources(sample, limits, shutil.disk_usage(output).free)

            check()
            publication = output / "publication.json"
            if collection.exists():
                receipt = json.loads(publication.read_text())
                if digest(collection) != receipt["sha256"] or Path(str(collection) + "-wal").exists():
                    raise ValueError("Published collection changed; it will not be overwritten.")
                summary.update(receipt["summary"], reused_games=receipt["summary"]["games"], reused_publication=True)
            else:
                configs = partitions(config)
                results, resources = run_workers(configs, output, execution, deadline, limits, origin["source_sha256"])
                shards = [output / "shards" / f"source-{i}" / "collection.sqlite" for i in range(len(configs))]
                pending = execution / "combined.sqlite"
                tick = monotonic()
                with ExitStack() as locks:
                    for shard in shards:
                        locks.enter_context(exclusive_lock(shard.with_suffix(".sqlite.writer.lock")))
                    counts = combine_shards(shards, configs, pending, check=check)
                    shard_hashes = {str(p.relative_to(output)): digest(p) for p in shards}
                summary.update(
                    generation_status="complete",
                    collection_counts=counts,
                    resources=resources,
                    combine_seconds=monotonic() - tick,
                    worker_results=results,
                    reused_publication=False,
                )
                for key in ("games", "reused_games", "rejected_games", "reused_rejections", "planned_games"):
                    summary[key] = sum(r[key] for r in results)
                for key in ("selected_by_phase", "shortfall_by_phase", "execution_counters"):
                    values = Counter()
                    for result in results:
                        values.update(result[key])
                    summary[key] = dict(values)
                summary["status"] = "shortfall" if any(r["status"] == "shortfall" for r in results) else "complete"
                if provenance()["source_sha256"] != origin["source_sha256"]:
                    raise ValueError("Implementation changed during generation; shards retained without publication.")
                check()
                # Receipt first: a crash before/after the atomic link is recoverable.
                write_json(
                    publication, {"sha256": digest(pending), "shards": shard_hashes, "summary": summary}, indent=2
                )
                os.link(pending, collection)  # No overwrite, even if a noncooperating writer created a file.
                pending.unlink()
                directory = os.open(output, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            _export(collection, export, execution, summary)
            return summary
        except BaseException as exc:
            summary.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            summary["seconds"] = monotonic() - started
            summary["source_sha256"] = origin["source_sha256"]
            write_json(execution / "summary.json", summary, indent=2)
            write_json(output / "latest.json", {"execution": str(execution), "status": summary["status"]}, indent=2)


def worker_main():
    parser = argparse.ArgumentParser(description="Internal source worker for the parallel policy runner")
    for name in ("config", "store", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--deadline", type=float, required=True)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()

    def interrupted(*_):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        raise KeyboardInterrupt("Coordinator stopped the worker")

    signal.signal(signal.SIGTERM, interrupted)
    result = {"status": "failed"}
    try:
        if provenance()["source_sha256"] != args.source_sha256:
            raise ValueError("Worker implementation differs from the frozen coordinator.")
        config = PolicyGenerationConfig.model_validate_json(args.config.read_text())
        with Collection(args.store) as store, (args.output / "events.jsonl").open("x") as events:

            def event(value):
                events.write(json.dumps(value) + "\n")
                events.flush()

            result = generate_policies(store, config, event=event, deadline=args.deadline)
        result["source_sha256"] = provenance()["source_sha256"]
    except BaseException as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(args.output / "summary.json", result, indent=2)


if __name__ == "__main__":
    worker_main()
