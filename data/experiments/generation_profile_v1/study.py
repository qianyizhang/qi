"""AB-LEARN-008: matched generation timings and disposable diagnostic profiles."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter
from contextlib import ExitStack, contextmanager
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

from evidence import fixture_provider, prepare_controlled, semantic_records, write_new
from qi_game.execution import ReplaySession
from qi_game.reference import legal_moves, replay
from qi_game.trajectory import PythonTrajectory

from qi.artifacts import digest, provenance
from qi.profiling import Measurement, Timings
from qi.teacher import TeacherSession, UciProcess
from qi.training_data.generation_runner import PolicyGenerationConfig, generate_policies
from qi.training_data.store import Collection

ROOT = Path(__file__).resolve().parents[3]
ARMS = ("default", "native", "python-session")
MODES = ("timing", "profile", "off")
STAMP = "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"


@contextmanager
def instrument(timings: Timings, native: bool):
    """Only called in a fresh diagnostic worker; production functions stay on disk."""
    original_connect = sqlite3.connect

    class TimedConnection(sqlite3.Connection):
        def execute(self, *args, **kwargs):
            with timings.span("sqlite.execute"):
                return super().execute(*args, **kwargs)

        def __exit__(self, *args):
            with timings.span("sqlite.transaction_exit"):
                return super().__exit__(*args)

    with ExitStack() as hooks:
        hooks.enter_context(
            patch.object(sqlite3, "connect", lambda *a, **kw: original_connect(*a, **kw, factory=TimedConnection))
        )
        for owner, name, label in (
            (Collection, "append", "collection.append"),
            (ReplaySession, "inspect", "replay_session.inspect"),
            (TeacherSession, "analyze", "teacher.analyze"),
            (UciProcess, "line", "teacher.read_line"),
        ):
            hooks.enter_context(timings.wrap(owner, name, label))
        yield measured_native(timings) if native else None


def measured_native(timings: Timings):
    from qi_game_native.backend import NativeTrajectory

    class NativeCalls:
        def __init__(self, state):
            self.state = state

        def step(self, move):
            with timings.span("native.binding_step"):
                return self.state.step(move)

        def inspect(self):
            with timings.span("native.binding_inspect"):
                return self.state.inspect()

    class MeasuredNative(NativeTrajectory):
        def __init__(self, snapshot):
            with timings.span("native.construct"):
                super().__init__(snapshot)
            self._state = NativeCalls(self._state)

    return MeasuredNative


def worker(args):
    args.output.mkdir(parents=True, exist_ok=False)
    config = PolicyGenerationConfig.model_validate_json(args.config.read_text()).resolve(args.config.parent)
    options = {"provider": fixture_provider} if args.workload == "controlled" else {}
    if args.arm == "native":
        from qi_game_native.backend import NativeTrajectory

        options["trajectory_factory"] = NativeTrajectory
        identity = NativeTrajectory.identity()
    else:
        identity = PythonTrajectory.identity()
        if args.arm == "python-session":
            options["trajectory_factory"] = PythonTrajectory
    origin = provenance()
    measurement = Measurement(functions=args.mode == "profile")
    replay.cache_clear()
    legal_moves.cache_clear()
    write_new(args.output / "config.json", config.model_dump())
    with ExitStack() as hooks:
        if args.mode == "profile":
            factory = hooks.enter_context(instrument(measurement.timings, args.arm == "native"))
            if factory is not None:
                options["trajectory_factory"] = factory
        with Collection(args.output / "collection.sqlite") as store:
            if args.mode == "off":
                # Disposable sensitivity diagnostic; weaker durability is never adopted.
                store.db.execute("PRAGMA synchronous=OFF")
            pragmas = {key: store.db.execute(f"PRAGMA {key}").fetchone()[0] for key in ("journal_mode", "synchronous")}
            with measurement:
                result = generate_policies(store, config, **options)
            metrics = measurement.result
            rule_cache = legal_moves.cache_info()._asdict()
            if args.mode == "profile":
                measurement.export_functions(args.output / "functions")
            records = semantic_records(store)
            write_new(args.output / "semantic.json", records)
            plies = sum(
                len(g["game"]["snapshot"]["moves"]) - len(g["game"]["initial"]["moves"]) for g in records["games"]
            )
            selected = sum(result["selected_by_phase"].values())
            summary = {
                "produced_by": STAMP,
                "arm": args.arm,
                "mode": args.mode,
                "workload": args.workload,
                "identity": identity,
                "origin": origin,
                "pragmas": pragmas,
                **metrics,
                "games": len(records["games"]),
                "plies": plies,
                "selected": selected,
                "plies_per_second": plies / metrics["wall_seconds"],
                "selected_per_second": selected / metrics["wall_seconds"],
                "semantic_sha256": digest(records),
                "reference_rule_cache": rule_cache,
                "outcomes": dict(
                    Counter(g["outcome"]["reason"] if g["outcome"] else g["stop_reason"] for g in records["games"])
                ),
                "result": result,
            }
            write_new(args.output / "result.json", summary)
    print(json.dumps({k: summary[k] for k in ("arm", "mode", "wall_seconds", "plies", "selected", "semantic_sha256")}))


def prepare(args):
    prepare_controlled(args.output)
    old = ROOT / "data/experiments/learning/generation-resource-v1/plausible-p96-n10000-g128.json"
    teacher = PolicyGenerationConfig.model_validate_json(old.read_text()).resolve(old.parent)
    book = json.loads((ROOT / "data/evaluation/human-openings-v1/development.json").read_text())
    seen, starts = set(), []
    for start in book["starts"]:
        if start["family"] not in seen:
            seen.add(start["family"])
            starts.append(start)
        if len(starts) == 4:
            break
    source = teacher.sources[0].model_dump()
    sources = []
    for start in starts:
        item = json.loads(json.dumps(source))
        item.update(id=start["id"], games=4)
        item["start"].update(id=start["id"], family_id=start["family"], snapshot=start["snapshot"])
        sources.append(item)
    value = teacher.model_dump()
    value.update(name="generation-bottleneck-teacher", seconds=180.0, sources=sources)
    teacher = PolicyGenerationConfig.model_validate(value)
    write_new(args.output / "teacher.json", teacher.model_dump())


def freeze(output, config):
    paths = [
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        Path(__file__),
        Path(__file__).with_name("evidence.py"),
        config,
    ]
    for base in (ROOT / "src/qi", ROOT / "packages"):
        paths += [
            p for p in base.rglob("*") if p.suffix in (".py", ".cpp", ".hpp", ".so", ".toml") and "build" not in p.parts
        ]
    manifest = []
    for path in sorted({p.resolve() for p in paths}):
        relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path("external") / path.name
        content = path.read_bytes()
        manifest.append(
            {"source": str(path), "frozen": str(Path("frozen") / relative), "sha256": sha256(content).hexdigest()}
        )
        target = output / "frozen" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    write_new(output / "manifest.json", manifest)
    return manifest


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    started = perf_counter()
    try:
        manifest = freeze(args.output, args.config)
        for r in range(1, args.rounds + 1):
            cells = [(a, m) for m in args.modes for a in args.arms]
            if r % 2 == 0:
                cells.reverse()
            for arm, mode in cells:
                remaining = 1200 - (perf_counter() - started)
                if remaining <= 0:
                    raise TimeoutError("Comparison reached its 20-minute allowance.")
                out = args.output / f"round-{r}-{arm}-{mode}"
                command = [
                    sys.executable,
                    str(Path(__file__)),
                    "worker",
                    "--config",
                    str(args.config),
                    "--output",
                    str(out),
                    "--workload",
                    args.workload,
                    "--arm",
                    arm,
                    "--mode",
                    mode,
                ]
                with out.with_suffix(".log").open("x") as log:
                    subprocess.run(
                        command,
                        cwd=ROOT,
                        env={**os.environ, "PYTHONHASHSEED": "0"},
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=min(180, remaining),
                    )
                row = json.loads((out / "result.json").read_text())
                row["round"] = r
                row["path"] = str(out.resolve())
                results.append(row)
                print(
                    f"{r} {arm} {mode}: {row['wall_seconds']:.3f}s, {row['plies']} plies, {row['selected']} selections",
                    flush=True,
                )
                if len({x["semantic_sha256"] for x in results}) != 1:
                    raise ValueError("Semantic mismatch; retained evidence requires investigation.")
        for entry in manifest:
            if sha256(Path(entry["source"]).read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Source changed: {entry['source']}")
    except (Exception, KeyboardInterrupt) as error:
        write_new(
            args.output / "failure.json",
            {
                "status": "incomplete",
                "error_type": type(error).__name__,
                "error": str(error),
                "elapsed_seconds": perf_counter() - started,
                "results": results,
                "sources_verified": False,
            },
        )
        raise
    pairs = []
    for r in range(1, args.rounds + 1):
        cells = {(x["arm"], x["mode"]): x for x in results if x["round"] == r}
        for mode in args.modes:
            if ("default", mode) in cells and ("native", mode) in cells:
                pairs.append(
                    {
                        "round": r,
                        "mode": mode,
                        "native_over_python": cells[("default", mode)]["wall_seconds"]
                        / cells[("native", mode)]["wall_seconds"],
                    }
                )
    write_new(
        args.output / "summary.json",
        {
            "results": results,
            "pairs": pairs,
            "median_native_over_python": {
                m: median(p["native_over_python"] for p in pairs if p["mode"] == m)
                for m in sorted({p["mode"] for p in pairs})
            },
            "sources_verified": True,
        },
    )


def axis(choices):
    def parse(value):
        values = value.split(",")
        if len(set(values)) != len(values) or any(v not in choices for v in values):
            raise argparse.ArgumentTypeError(f"Expected distinct comma-separated choices from {choices}.")
        return values

    return parse


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be a positive integer.")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "worker", "run"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
        if name != "prepare":
            command.add_argument("--config", type=Path, required=True)
            command.add_argument("--workload", choices=["controlled", "teacher"], default="controlled")
        if name == "worker":
            command.add_argument("--arm", choices=ARMS, default="default")
            command.add_argument("--mode", choices=MODES, default="timing")
        elif name == "run":
            command.add_argument("--arms", type=axis(ARMS), default="default,native")
            command.add_argument("--modes", type=axis(MODES), default="timing")
            command.add_argument("--rounds", type=positive_int, default=3)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.command != "prepare":
        args.config = args.config.resolve()
    {"prepare": prepare, "worker": worker, "run": run}[args.command](args)


if __name__ == "__main__":
    main()
