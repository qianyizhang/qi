"""Reusable harness for the repository's retained generation comparisons."""

import argparse
import cProfile
import importlib.util
import json
import os
import re
import resource
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter, process_time
from typing import Any, Literal, Protocol

from qi_game.contracts import Snapshot
from qi_game.reference import legal_moves, replay, restore
from qi_game.trajectory import PythonTrajectory, TrajectoryFactory

from qi.artifacts import ROOT as RUNTIME_ROOT
from qi.artifacts import digest, provenance
from qi.evaluation import Corpus, Opening
from qi.players.policy.encoding import input_key
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity
from qi.training_data.contracts import Example, classify_phase, state_fingerprint
from qi.training_data.generation_io import analysis_spec
from qi.training_data.generation_policies import ActorPolicy, SamplingPolicy
from qi.training_data.generation_runner import (
    GenerationSource,
    GenerationTeacher,
    PolicyGenerationConfig,
    generate_policies,
)
from qi.training_data.store import Collection

ROOT = Path(__file__).resolve().parents[1]

# Retained evidence and frozen runner modules cross a deliberately dynamic JSON boundary.
type JsonObject = dict[str, Any]
type GenerationRunner = Callable[..., dict[str, Any]]
type BaselineKind = Literal["generation-module", "runtime-tree"]


@dataclass(frozen=True, slots=True)
class BenchmarkProtocol:
    """The two retained comparison shapes and their evidence-compatible differences."""

    baseline_kind: BaselineKind
    include_inverse_default_metric: bool = False


NATIVE_GENERATION_COMPARISON = BenchmarkProtocol("generation-module")
RUNTIME_TREE_COMPARISON = BenchmarkProtocol("runtime-tree")
INCREMENTAL_RUNTIME_COMPARISON = BenchmarkProtocol("runtime-tree", include_inverse_default_metric=True)


class BenchmarkArguments(argparse.Namespace):
    command: Literal["prepare", "worker", "compare"]
    output: Path
    config: Path | None
    teacher_config: Path | None
    baseline: Path | None
    workload: Literal["controlled", "teacher"]
    arm: str
    reference_arm: Literal["python", "default"]
    rounds: int
    profile: bool


class GeneratedGame(Protocol):
    board: str
    turn: Literal["red", "black"]
    moves: tuple[str, ...]
    state_hash: str


def required_path(value: Path | None, option: str) -> Path:
    if value is None:
        raise ValueError(f"{option} is required for this command.")
    return value


def write_new(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def fixture_analysis(
    game: GeneratedGame, settings: TeacherConfig, moves: tuple[str, ...] | list[str]
) -> TeacherAnalysis:
    identity = TeacherIdentity.read(settings)
    spec = analysis_spec(settings, identity).supervision
    return TeacherAnalysis(
        schema_version=int(spec["adapter"][-1]),
        adapter_version=spec["adapter"],
        snapshot=Snapshot(moves=list(game.moves)),
        state_hash=game.state_hash,
        move=sorted(moves)[0],
        engine_name="deterministic-legal-fixture",
        engine_sha256=identity.engine_sha256,
        network_sha256=identity.network_sha256,
        settings=spec["settings"],
        requested_nodes=settings.nodes,
        requested_depth=settings.depth,
        timeout_seconds=settings.timeout_seconds,
        reported_nodes=settings.nodes,
        reported_depth=1,
        elapsed_ms=0.0,
        score=None,
        search_info=[],
    )


def reference_fixture_provider(game: GeneratedGame, settings: TeacherConfig) -> TeacherAnalysis:
    return fixture_analysis(game, settings, legal_moves(game.board, game.turn))


def execution_fixture_provider(game: GeneratedGame, settings: TeacherConfig) -> TeacherAnalysis:
    moves = game.legal_moves if hasattr(game, "legal_moves") else legal_moves(game.board, game.turn)
    return fixture_analysis(game, settings, moves)


def semantic_records(store: Collection, *, independently_verify: bool) -> JsonObject:
    games = []
    for row in store.db.execute("SELECT id,status,stop_reason,outcome FROM games ORDER BY id"):
        game = store.game(row[0])
        reference = restore(game.snapshot)
        stored_outcome = json.loads(row[3]) if row[3] else None
        if independently_verify:
            expected_outcome = asdict(reference.outcome) if reference.outcome else None
            if stored_outcome != expected_outcome:
                raise ValueError("Stored outcome differs from independent replay.")
            for decision in game.actor["generation_result"]["decisions"]:
                if decision["move"] != game.snapshot.moves[decision["ply"]]:
                    raise ValueError("Actor decision differs from replay history.")
        games.append(
            {
                "game": game.model_dump(exclude={"actor_ms"}),
                "status": row[1],
                "stop_reason": row[2],
                "outcome": stored_outcome,
                "state_hash": reference.state_hash,
            }
        )
    occurrences = [
        list(row)
        for row in store.db.execute(
            "SELECT game_id,ply_count,board,turn,state_hash,input_hash,phase,json(payload) "
            "FROM position_occurrences ORDER BY id"
        )
    ]
    if independently_verify:
        for game_id, ply, board, turn, state_hash, occurrence_input, phase, _ in occurrences:
            snapshot = store.game(game_id).snapshot
            checked_snapshot = Snapshot(moves=snapshot.moves[:ply])
            checked = restore(checked_snapshot)
            if (board, turn, state_hash, occurrence_input, phase) != (
                checked.board,
                checked.turn,
                state_fingerprint(checked_snapshot),
                input_key(checked),
                classify_phase(checked),
            ):
                raise ValueError("Occurrence differs from independent replay.")
    analyses = []
    for row in store.db.execute("SELECT occurrence_id,status,json(payload) FROM analyses ORDER BY id"):
        payload = json.loads(row[2])
        answer = payload.get("answer")
        if answer:
            if independently_verify:
                Example.model_validate({"analysis": answer, "source_ids": ["independent-verification"]})
            answer.pop("elapsed_ms", None)
            answer["settings"].pop("EvalFile", None)
            answer["search_info"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", line) for line in answer["search_info"]]
            if independently_verify:
                payload["raw"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", line) for line in payload["raw"]]
        analyses.append([row[0], row[1], payload])
    if store.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity check failed.")
    if store.db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("SQLite foreign key check failed.")
    return {"games": games, "occurrences": occurrences, "analyses": analyses}


def load_frozen_runner(path: Path) -> GenerationRunner:
    spec = importlib.util.spec_from_file_location("frozen_generation_baseline", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load generation baseline: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.generate_policies


def select_runner(
    args: BenchmarkArguments, protocol: BenchmarkProtocol
) -> tuple[GenerationRunner, TrajectoryFactory, dict[str, object]]:
    options: dict[str, object] = {}
    native_arm = args.arm in {"native", "old-native"}
    if native_arm:
        from qi_game_native.backend import NativeTrajectory

        factory = NativeTrajectory
    else:
        factory = PythonTrajectory
    runner: GenerationRunner = generate_policies
    if protocol.baseline_kind == "generation-module" and args.arm == "legacy":
        runner = load_frozen_runner(required_path(args.baseline, "--baseline"))
    elif native_arm or (protocol.baseline_kind == "generation-module" and args.arm != "default"):
        options["trajectory_factory"] = factory
    return runner, factory, options


def worker(args: BenchmarkArguments, protocol: BenchmarkProtocol) -> None:
    args.output.mkdir(parents=True, exist_ok=False)
    config_path = required_path(args.config, "--config")
    if protocol.baseline_kind == "runtime-tree":
        expected_root = required_path(args.baseline, "--baseline").resolve() if args.arm.startswith("old-") else ROOT
        if RUNTIME_ROOT.resolve() != expected_root:
            raise ValueError("Worker imported the wrong runtime.")
    config = PolicyGenerationConfig.model_validate_json(config_path.read_text()).resolve(config_path.parent)
    tick = perf_counter()
    runner, factory, options = select_runner(args, protocol)
    identity = factory.identity()
    load_seconds = perf_counter() - tick
    if args.workload == "controlled":
        options["provider"] = (
            execution_fixture_provider if protocol.baseline_kind == "runtime-tree" else reference_fixture_provider
        )
    replay.cache_clear()
    legal_moves.cache_clear()
    profile = cProfile.Profile() if args.profile else None
    write_new(args.output / "config.json", config.model_dump())
    with Collection(args.output / "collection.sqlite") as store:
        wall, cpu = perf_counter(), process_time()
        if profile:
            profile.enable()
        result = runner(store, config, **options)
        if profile:
            profile.disable()
            profile.dump_stats(str(args.output / "diagnostic.prof"))
        elapsed, cpu_seconds = perf_counter() - wall, process_time() - cpu
        rule_cache = legal_moves.cache_info()._asdict()
        records = semantic_records(store, independently_verify=protocol.baseline_kind == "runtime-tree")
        write_new(args.output / "semantic.json", records)
        plies = sum(
            len(row["game"]["snapshot"]["moves"]) - len(row["game"]["initial"]["moves"]) for row in records["games"]
        )
        selected = sum(result["selected_by_phase"].values())
        summary: JsonObject = {
            "arm": args.arm,
            "workload": args.workload,
            "identity": identity,
            "origin": provenance(),
        }
        if protocol.baseline_kind == "runtime-tree":
            summary["runtime_root"] = str(RUNTIME_ROOT)
            summary["reference_rule_cache_before_verification"] = rule_cache
        summary.update(
            {
                "load_seconds": load_seconds,
                "wall_seconds": elapsed,
                "cpu_seconds": cpu_seconds,
                "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                / (1024**2 if sys.platform == "darwin" else 1024),
                "plies": plies,
                "selected": selected,
                "plies_per_second": plies / elapsed,
                "selected_per_second": selected / elapsed,
                "semantic_sha256": digest(records),
                "outcomes": dict(
                    Counter(
                        row["outcome"]["reason"] if row["outcome"] else row["stop_reason"] for row in records["games"]
                    )
                ),
                "result": result,
            }
        )
        write_new(args.output / "result.json", summary)
    print(json.dumps({key: summary[key] for key in ("arm", "wall_seconds", "plies", "selected", "semantic_sha256")}))


def prepare(args: BenchmarkArguments) -> None:
    args.output.mkdir(parents=True, exist_ok=False)
    engine = args.output / "fixture-engine"
    network = args.output / "fixture-network"
    engine.write_text("controlled fixture, no executable teacher\n")
    network.write_text("controlled fixture, no learned network\n")
    teacher = GenerationTeacher(
        engine=str(engine.resolve()),
        network=str(network.resolve()),
        engine_sha256=sha256(engine.read_bytes()).hexdigest(),
        network_sha256=sha256(network.read_bytes()).hexdigest(),
        nodes=1000,
        timeout_seconds=5.0,
    )
    config = PolicyGenerationConfig(
        name="native-integration",
        seed=29,
        seconds=180.0,
        corpus=Corpus(
            id="initial-control",
            provenance="Standard initial position excluded from selections.",
            openings=[Opening(id="initial", description="Initial board", snapshot=Snapshot())],
        ),
        teachers={"teacher": teacher},
        actor_teacher="teacher",
        supervision=["teacher"],
        sources=[
            GenerationSource(
                id="controlled",
                games=64,
                split="train",
                additional_plies=300,
                actor=ActorPolicy(mode="random"),
                sampling=SamplingPolicy(),
            )
        ],
    )
    write_new(args.output / "controlled.json", config.model_dump())
    if args.teacher_config:
        historical = PolicyGenerationConfig.model_validate_json(args.teacher_config.read_text())
        real = next(iter(historical.teachers.values())).model_copy(update={"nodes": 1000, "threads": 1})
        config.teachers = {"teacher": real}
        config.sources = [
            GenerationSource(
                id="teacher-pilot",
                games=4,
                split="train",
                additional_plies=32,
                actor=ActorPolicy(mode="plausible"),
                sampling=SamplingPolicy(),
            )
        ]
        write_new(args.output / "teacher.json", config.model_dump())


def benchmark_sources(entrypoint: Path, config: Path, baseline: Path, protocol: BenchmarkProtocol) -> list[Path]:
    sources = [ROOT / "pyproject.toml", ROOT / "uv.lock", entrypoint, Path(__file__), config]
    roots = [ROOT / "src/qi", ROOT / "packages"]
    if protocol.baseline_kind == "runtime-tree":
        sources.extend([baseline / "pyproject.toml", baseline / "uv.lock"])
        roots.extend([baseline / "src/qi", baseline / "packages"])
    else:
        sources.append(baseline)
    for base in roots:
        sources.extend(
            path
            for path in base.rglob("*")
            if path.suffix in (".py", ".cpp", ".hpp", ".toml", ".so") and "build" not in path.parts
        )
    return sources


def freeze_sources(output: Path, paths: list[Path]) -> None:
    manifest = {}
    for path in sorted(set(paths)):
        relative = path.resolve().relative_to(ROOT)
        manifest[str(relative)] = sha256(path.read_bytes()).hexdigest()
        frozen = output / "frozen" / relative
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_bytes(path.read_bytes())
    write_new(output / "manifest.json", manifest)


def comparison_arms(args: BenchmarkArguments, protocol: BenchmarkProtocol) -> list[str]:
    if protocol.baseline_kind == "runtime-tree":
        return (
            ["old-default", "old-native", "default", "native"]
            if args.workload == "controlled"
            else [
                "default",
                "native",
            ]
        )
    return (
        ["legacy", args.reference_arm, "native"]
        if args.workload == "controlled"
        else [
            args.reference_arm,
            "native",
        ]
    )


def worker_environment(arm: str, baseline: Path, protocol: BenchmarkProtocol) -> dict[str, str] | None:
    if protocol.baseline_kind == "generation-module":
        return None
    runtime = baseline.resolve() if arm.startswith("old-") else ROOT
    return {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            map(str, [runtime / "src", runtime / "packages/qi-game/src", runtime / "packages/qi-game-native/src"])
        ),
    }


def paired_result(
    round_index: int, cells: dict[str, JsonObject], args: BenchmarkArguments, protocol: BenchmarkProtocol
) -> JsonObject:
    if protocol.baseline_kind == "generation-module":
        reference_seconds = cells[args.reference_arm]["wall_seconds"]
        row = {
            "round": round_index,
            f"{args.reference_arm}_over_native": reference_seconds / cells["native"]["wall_seconds"],
        }
        if "legacy" in cells:
            row["legacy_over_native"] = cells["legacy"]["wall_seconds"] / cells["native"]["wall_seconds"]
            row[f"{args.reference_arm}_over_legacy"] = reference_seconds / cells["legacy"]["wall_seconds"]
        return row
    reference_seconds = cells["default"]["wall_seconds"]
    row = {"round": round_index, "default_over_native": reference_seconds / cells["native"]["wall_seconds"]}
    if "old-default" in cells:
        row["old_native_over_native"] = cells["old-native"]["wall_seconds"] / cells["native"]["wall_seconds"]
        row["default_over_old_default"] = reference_seconds / cells["old-default"]["wall_seconds"]
        if protocol.include_inverse_default_metric:
            row["old_default_over_default"] = cells["old-default"]["wall_seconds"] / reference_seconds
    return row


def compare(args: BenchmarkArguments, protocol: BenchmarkProtocol, entrypoint: Path) -> None:
    args.output.mkdir(parents=True, exist_ok=False)
    config = required_path(args.config, "--config")
    baseline = required_path(args.baseline, "--baseline")
    freeze_sources(args.output, benchmark_sources(entrypoint, config, baseline, protocol))
    results = []
    started = perf_counter()
    for round_index in range(args.rounds):
        arms = comparison_arms(args, protocol)
        if round_index % 2:
            arms.reverse()
        for arm in arms:
            if perf_counter() - started > 1200:
                raise TimeoutError("Comparison exceeded its total allowance.")
            output = args.output / f"round-{round_index + 1}-{arm}"
            command = [
                sys.executable,
                str(entrypoint),
                "worker",
                "--arm",
                arm,
                "--workload",
                args.workload,
                "--config",
                str(config),
                "--baseline",
                str(baseline),
                "--output",
                str(output),
            ]
            with (args.output / f"round-{round_index + 1}-{arm}.log").open("x") as log:
                subprocess.run(
                    command,
                    cwd=ROOT,
                    env=worker_environment(arm, baseline, protocol),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=180,
                )
            result = json.loads((output / "result.json").read_text())
            result["round"] = round_index + 1
            results.append(result)
            print(f"Round {round_index + 1} {arm}: {result['wall_seconds']:.3f}s", flush=True)
    if len({result["semantic_sha256"] for result in results}) != 1:
        raise ValueError("Semantic mismatch; inspect retained per-cell records.")
    paired = []
    for round_index in range(1, args.rounds + 1):
        cells = {result["arm"]: result for result in results if result["round"] == round_index}
        paired.append(paired_result(round_index, cells, args, protocol))
    summary = {
        "results": results,
        "paired": paired,
        "medians": {key: median(row[key] for row in paired) for key in paired[0] if key != "round"},
    }
    write_new(args.output / "summary.json", summary)
    print(json.dumps(summary["medians"]))


def main(*, protocol: BenchmarkProtocol, entrypoint: Path, description: str) -> None:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("command", choices=["prepare", "worker", "compare"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--teacher-config", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--workload", choices=["controlled", "teacher"], default="controlled")
    if protocol.baseline_kind == "generation-module":
        parser.add_argument("--arm", choices=["python", "native", "legacy", "default"], default="python")
        parser.add_argument("--reference-arm", choices=["python", "default"], default="python")
    else:
        parser.add_argument("--arm", choices=["native", "default", "old-native", "old-default"], default="default")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args(namespace=BenchmarkArguments())
    if args.command == "prepare":
        prepare(args)
    elif args.command == "worker":
        worker(args, protocol)
    else:
        compare(args, protocol, entrypoint)
