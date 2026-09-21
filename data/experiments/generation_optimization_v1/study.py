"""Frozen native-step comparison and isolated one-versus-two-worker experiment."""

import argparse
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import monotonic, sleep

from checks import combined

ROOT = Path(__file__).resolve().parents[3]
PROFILE = Path("data/experiments/generation_profile_v1")
BOOTSTRAP = """
import runpy, sys
from pathlib import Path
root = Path(sys.argv.pop(1))
import qi, qi_game
if not Path(qi.__file__).is_relative_to(root / 'src'):
    raise RuntimeError('Wrong application source root')
if not Path(qi_game.__file__).is_relative_to(root / 'packages/qi-game/src'):
    raise RuntimeError('Wrong referee source root')
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""


def write(path, value):
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    with path.open("x") as stream:
        stream.write(content)


def runtime_files(root):
    paths = [root / "pyproject.toml", root / "uv.lock"]
    for directory in (root / "src/qi", root / "packages", root / PROFILE):
        paths.extend(
            p
            for p in directory.rglob("*")
            if p.suffix in {".py", ".cpp", ".hpp", ".so", ".toml"} and "build" not in p.parts
        )
    return sorted(set(paths))


def fingerprint(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in runtime_files(root)}


def freeze(output):
    output.mkdir(parents=True, exist_ok=False)
    for source in runtime_files(ROOT):
        target = output / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    write(output / "manifest.json", fingerprint(output))


def command(runtime, script, arguments):
    env = {
        **os.environ,
        "PYTHONHASHSEED": "0",
        "PYTHONPATH": os.pathsep.join(
            map(
                str,
                (
                    runtime / "src",
                    runtime / "packages/qi-game/src",
                    runtime / "packages/qi-game-native/src",
                ),
            )
        ),
    }
    return [sys.executable, "-c", BOOTSTRAP, str(runtime), str(script), *map(str, arguments)], env


def process_rss(processes, roots):
    """Sum sampled worker/descendant RSS; shared resident pages may be counted twice."""
    selected = set(roots)
    while True:
        children = {pid for pid, parent, _ in processes if parent in selected}
        if children <= selected:
            break
        selected |= children
    return sum(rss for pid, _, rss in processes if pid in selected or pid == os.getpid()) / 1024


def run_group(jobs, limit, output, deadline, *, sample=False):
    """Bound worker lifetimes and preserve every log/result on failure."""
    started = monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    active, rows, peak, samples = {}, [], 0.0, 0
    pending = iter(jobs)
    exhausted = False
    last_sample = 0.0
    try:
        with ExitStack() as logs:
            while active or not exhausted:
                while len(active) < limit and not exhausted:
                    job = next(pending, None)
                    if job is None:
                        exhausted = True
                        break
                    runtime, script, arguments, cell = job
                    argv, env = command(runtime, script, arguments)
                    log = logs.enter_context(cell.with_suffix(".log").open("x"))
                    process = subprocess.Popen(
                        argv, cwd=runtime, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
                    )
                    active[process] = cell, monotonic()
                now = monotonic()
                if now >= deadline or any(now - tick >= 180 for _, tick in active.values()):
                    raise TimeoutError("Worker/comparison allowance exhausted.")
                if sample and now - last_sample >= 0.1:
                    table = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss="], text=True, timeout=3)
                    processes = [tuple(map(int, line.split())) for line in table.splitlines()]
                    peak = max(peak, process_rss(processes, {p.pid for p in active}))
                    samples += 1
                    last_sample = now
                for process, (cell, _) in list(active.items()):
                    code = process.poll()
                    if code is None:
                        continue
                    if code:
                        raise RuntimeError(f"Worker exited {code}; see {cell.with_suffix('.log')}.")
                    rows.append({"path": str(cell), **json.loads((cell / "result.json").read_text())})
                    del active[process]
                if active:
                    sleep(0.02)
    except (Exception, KeyboardInterrupt) as error:
        for process in active:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in active:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # The worker can exit between the timeout and this signal.
                process.wait()
        write(output / "failure.json", {"status": "incomplete", "error": str(error), "completed": rows})
        raise
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return rows, {
        "job_wall_seconds": monotonic() - started,
        "waited_process_tree_cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
        "sampled_process_tree_rss_mib": peak if sample else None,
        "rss_samples": samples,
        "resource_boundary": "Worker startup through verified results; CPU includes ps probes and waited descendants; "
        "RSS sums coordinator/workers/descendants, may double-count shared pages and miss short peaks.",
    }


def worker_job(runtime, config, output, workload, arm="default"):
    return (
        runtime,
        runtime / PROFILE / "study.py",
        [
            "worker",
            "--config",
            config,
            "--output",
            output,
            "--workload",
            workload,
            "--arm",
            arm,
        ],
        output,
    )


def native(args, deadline):
    results = []
    for workload in ("controlled", "teacher", "actions"):
        signature = None
        for round_id in range(1, 4):
            arms = [
                ("baseline-native", args.baseline, "native"),
                ("candidate-native", args.candidate, "native"),
                ("candidate-python", args.candidate, "default"),
            ]
            if round_id % 2 == 0:
                arms.reverse()
            for label, runtime, arm in arms:
                cell = args.output / f"{workload}-{round_id}-{label}"
                if workload == "actions":
                    source = args.output / "controlled-1-baseline-native/semantic.json"
                    job = (
                        runtime,
                        runtime / PROFILE / "actions.py",
                        [
                            "--input",
                            source,
                            "--output",
                            cell,
                            "--repeats",
                            "3",
                            "--arm",
                            "python" if arm == "default" else arm,
                        ],
                        cell,
                    )
                else:
                    job = worker_job(runtime, args.inputs / f"{workload}.json", cell, workload, arm)
                rows, _ = run_group([job], 1, args.output, deadline)
                row = rows[0]
                signature = signature or row["semantic_sha256"]
                if row["semantic_sha256"] != signature:
                    raise ValueError(f"Semantic mismatch in {cell}.")
                seconds = median(row["elapsed_seconds"]) if workload == "actions" else row["wall_seconds"]
                results.append(
                    {"workload": workload, "round": round_id, "label": label, "seconds": seconds, "result": row}
                )
                print(f"{workload} {round_id} {label}: {seconds:.4f}s", flush=True)
    pairs = []
    for workload in ("controlled", "teacher", "actions"):
        for round_id in range(1, 4):
            cells = {r["label"]: r["seconds"] for r in results if r["workload"] == workload and r["round"] == round_id}
            pairs.append(
                {
                    "workload": workload,
                    "round": round_id,
                    "candidate_over_baseline_native": cells["baseline-native"] / cells["candidate-native"],
                    "native_over_python": cells["candidate-python"] / cells["candidate-native"],
                }
            )
    return {"results": results, "pairs": pairs}


def partitions(config):
    sources = config["sources"]
    if len(sources) < 2 or any(s["parent_trajectory"] is not None for s in sources):
        raise ValueError("Require at least two independent whole sources.")
    return [{**config, "sources": sources[offset::2]} for offset in (0, 1)]


def workers(args, deadline):
    configs = []
    for index, value in enumerate(partitions(json.loads((args.inputs / "teacher.json").read_text()))):
        path = args.output / f"shard-{index}.json"
        write(path, value)
        configs.append(path)
    results, signatures = [], {}
    reference = combined([args.reference])
    for round_id in range(1, 4):
        for limit in (1, 2) if round_id % 2 else (2, 1):
            group = args.output / f"round-{round_id}-workers-{limit}"
            group.mkdir()
            jobs = [
                worker_job(args.candidate, config, group / f"shard-{index}", "teacher")
                for index, config in enumerate(configs)
            ]
            rows, metrics = run_group(jobs, limit, group, deadline, sample=True)
            for row in rows:
                shard = Path(row["path"]).name
                expected = signatures.setdefault(shard, row["semantic_sha256"])
                if row["semantic_sha256"] != expected:
                    raise ValueError(f"Semantic mismatch in {row['path']}.")
            checked = combined([Path(row["path"]) / "collection.sqlite" for row in rows])
            if checked != reference:
                raise ValueError(f"Partitioned results differ from the full serial workload: {checked} != {reference}")
            selected = sum(row["selected"] for row in rows)
            result = {
                "round": round_id,
                "workers": limit,
                **metrics,
                "selected": selected,
                "selected_per_second": selected / metrics["job_wall_seconds"],
                "results": rows,
            }
            write(group / "resources.json", result)
            results.append(result)
            print(
                f"workers={limit} round={round_id}: {metrics['job_wall_seconds']:.3f}s, {selected} selections",
                flush=True,
            )
    pairs = []
    for round_id in range(1, 4):
        cells = {r["workers"]: r for r in results if r["round"] == round_id}
        pairs.append({"round": round_id, "two_over_one": cells[1]["job_wall_seconds"] / cells[2]["job_wall_seconds"]})
    return {"results": results, "pairs": pairs, "semantic_sha256": signatures, "combined": reference}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "native", "workers"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--reference", type=Path, help="Full serial teacher collection for partition equivalence.")
    args = parser.parse_args()
    for name in ("output", "candidate", "baseline", "inputs", "reference"):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.mode == "freeze":
        freeze(args.output)
        return
    if not args.candidate or not args.inputs or (args.mode == "native" and not args.baseline):
        parser.error("Comparisons require --candidate, --inputs and native also requires --baseline.")
    if args.mode == "workers" and not args.reference:
        parser.error("Worker comparisons also require --reference.")
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, args.output / "controller.py")
    for name in ("checks.py", "recovery.py"):
        shutil.copy2(Path(__file__).with_name(name), args.output / name)
    runtimes = {str(path): fingerprint(path) for path in (args.candidate, args.baseline) if path}
    write(args.output / "runtime-manifests.json", runtimes)
    for source in args.inputs.glob("*.json"):
        shutil.copy2(source, args.output / ("input-" + source.name))
    try:
        summary = {"native": native, "workers": workers}[args.mode](args, monotonic() + 1200)
        if any(fingerprint(Path(path)) != expected for path, expected in runtimes.items()):
            raise ValueError("Frozen runtime changed during comparison.")
        write(args.output / "summary.json", {"sources_verified": True, **summary})
    except (Exception, KeyboardInterrupt) as error:
        if not (args.output / "failure.json").exists():
            write(args.output / "failure.json", {"status": "incomplete", "error": str(error)})
        raise


if __name__ == "__main__":
    main()
