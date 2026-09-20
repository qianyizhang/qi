"""AB-ARCH-007: compare incremental collection writes against complete c44e08d controls."""

import argparse
import cProfile
import json
import os
import re
import resource
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter, process_time

from qi_game.contracts import Snapshot
from qi_game.reference import legal_moves, replay, restore
from qi_game.trajectory import PythonTrajectory

from qi.artifacts import ROOT as RUNTIME_ROOT
from qi.artifacts import digest, provenance
from qi.evaluation import Corpus, Opening
from qi.players.policy.encoding import input_key
from qi.teacher import TeacherAnalysis, TeacherIdentity
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


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def fixture_provider(game, settings):
    identity = TeacherIdentity.read(settings)
    spec = analysis_spec(settings, identity).supervision
    return TeacherAnalysis(
        schema_version=int(spec["adapter"][-1]),
        adapter_version=spec["adapter"],
        snapshot=Snapshot(moves=list(game.moves)),
        state_hash=game.state_hash,
        move=sorted(game.legal_moves if hasattr(game, "legal_moves") else legal_moves(game.board, game.turn))[0],
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


def semantic_records(store):
    games = []
    for row in store.db.execute("SELECT id,status,stop_reason,outcome FROM games ORDER BY id"):
        game = store.game(row[0])
        reference = restore(game.snapshot)
        expected_outcome = asdict(reference.outcome) if reference.outcome else None
        assert (json.loads(row[3]) if row[3] else None) == expected_outcome
        for decision in game.actor["generation_result"]["decisions"]:
            assert decision["move"] == game.snapshot.moves[decision["ply"]]
        games.append(
            {
                "game": game.model_dump(exclude={"actor_ms"}),
                "status": row[1],
                "stop_reason": row[2],
                "outcome": json.loads(row[3]) if row[3] else None,
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
    for game_id, ply, board, turn, state_hash, input_hash, phase, _ in occurrences:
        snapshot = store.game(game_id).snapshot
        checked_snapshot = Snapshot(moves=snapshot.moves[:ply])
        checked = restore(checked_snapshot)
        assert (board, turn, state_hash, input_hash, phase) == (
            checked.board,
            checked.turn,
            state_fingerprint(checked_snapshot),
            input_key(checked),
            classify_phase(checked),
        )
    analyses = []
    for row in store.db.execute("SELECT occurrence_id,status,json(payload) FROM analyses ORDER BY id"):
        payload = json.loads(row[2])
        answer = payload.get("answer")
        if answer:
            Example.model_validate({"analysis": answer, "source_ids": ["independent-verification"]})
            answer.pop("elapsed_ms", None)
            answer["settings"].pop("EvalFile", None)
            answer["search_info"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", line) for line in answer["search_info"]]
            payload["raw"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", line) for line in payload["raw"]]
        analyses.append([row[0], row[1], payload])
    assert store.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not store.db.execute("PRAGMA foreign_key_check").fetchall()
    return {"games": games, "occurrences": occurrences, "analyses": analyses}


def worker(args):
    args.output.mkdir(parents=True, exist_ok=False)
    expected_root = args.baseline.resolve() if args.arm.startswith("old-") else ROOT
    assert RUNTIME_ROOT.resolve() == expected_root, "Worker imported the wrong runtime."
    config = PolicyGenerationConfig.model_validate_json(args.config.read_text())
    config = config.resolve(args.config.parent)
    runner, options = generate_policies, {}
    tick = perf_counter()
    if args.arm in {"native", "old-native"}:
        from qi_game_native.backend import NativeTrajectory

        factory = NativeTrajectory
    else:
        factory = PythonTrajectory
    identity = factory.identity()
    if args.arm in {"native", "old-native"}:
        options["trajectory_factory"] = factory
    load_seconds = perf_counter() - tick
    if args.workload == "controlled":
        options["provider"] = fixture_provider
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
        records = semantic_records(store)
        write_new(args.output / "semantic.json", records)
        plies = sum(
            len(row["game"]["snapshot"]["moves"]) - len(row["game"]["initial"]["moves"]) for row in records["games"]
        )
        selected = sum(result["selected_by_phase"].values())
        summary = {
            "arm": args.arm,
            "workload": args.workload,
            "identity": identity,
            "origin": provenance(),
            "runtime_root": str(RUNTIME_ROOT),
            "reference_rule_cache_before_verification": rule_cache,
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
                Counter(row["outcome"]["reason"] if row["outcome"] else row["stop_reason"] for row in records["games"])
            ),
            "result": result,
        }
        write_new(args.output / "result.json", summary)
    print(json.dumps({key: summary[key] for key in ("arm", "wall_seconds", "plies", "selected", "semantic_sha256")}))


def prepare(args):
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


def compare(args):
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        Path(__file__),
        args.config,
        args.baseline / "pyproject.toml",
        args.baseline / "uv.lock",
    ]
    for base in [ROOT / "src/qi", ROOT / "packages", args.baseline / "src/qi", args.baseline / "packages"]:
        sources += [
            p for p in base.rglob("*") if p.suffix in (".py", ".cpp", ".hpp", ".toml", ".so") and "build" not in p.parts
        ]
    manifest = {}
    for path in sorted(set(sources)):
        relative = path.resolve().relative_to(ROOT)
        manifest[str(relative)] = sha256(path.read_bytes()).hexdigest()
        frozen = args.output / "frozen" / relative
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_bytes(path.read_bytes())
    write_new(args.output / "manifest.json", manifest)
    results = []
    started = perf_counter()
    for round_index in range(args.rounds):
        arms = (
            ["old-default", "old-native", "default", "native"]
            if args.workload == "controlled"
            else ["default", "native"]
        )
        if round_index % 2:
            arms.reverse()
        for arm in arms:
            if perf_counter() - started > 1200:
                raise TimeoutError("Comparison exceeded its total allowance.")
            output = args.output / f"round-{round_index + 1}-{arm}"
            command = [
                sys.executable,
                str(Path(__file__)),
                "worker",
                "--arm",
                arm,
                "--workload",
                args.workload,
                "--config",
                str(args.config),
                "--baseline",
                str(args.baseline),
                "--output",
                str(output),
            ]
            with (args.output / f"round-{round_index + 1}-{arm}.log").open("x") as log:
                runtime = args.baseline.resolve() if arm.startswith("old-") else ROOT
                env = {
                    **os.environ,
                    "PYTHONPATH": os.pathsep.join(
                        map(
                            str,
                            [
                                runtime / "src",
                                runtime / "packages/qi-game/src",
                                runtime / "packages/qi-game-native/src",
                            ],
                        )
                    ),
                }
                subprocess.run(
                    command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180
                )
            result = json.loads((output / "result.json").read_text())
            result["round"] = round_index + 1
            results.append(result)
            print(f"Round {round_index + 1} {arm}: {result['wall_seconds']:.3f}s", flush=True)
    assert len({r["semantic_sha256"] for r in results}) == 1, "Semantic mismatch; inspect retained per-cell records."
    paired = []
    for index in range(1, args.rounds + 1):
        cells = {r["arm"]: r for r in results if r["round"] == index}
        reference_seconds = cells["default"]["wall_seconds"]
        row = {"round": index, "default_over_native": reference_seconds / cells["native"]["wall_seconds"]}
        if "old-default" in cells:
            row["old_native_over_native"] = cells["old-native"]["wall_seconds"] / cells["native"]["wall_seconds"]
            row["default_over_old_default"] = reference_seconds / cells["old-default"]["wall_seconds"]
            row["old_default_over_default"] = cells["old-default"]["wall_seconds"] / reference_seconds
        paired.append(row)
    summary = {
        "results": results,
        "paired": paired,
        "medians": {key: median(row[key] for row in paired) for key in paired[0] if key != "round"},
    }
    write_new(args.output / "summary.json", summary)
    print(json.dumps(summary["medians"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "worker", "compare"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--teacher-config", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--workload", choices=["controlled", "teacher"], default="controlled")
    parser.add_argument("--arm", choices=["native", "default", "old-native", "old-default"], default="default")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()
    {"prepare": prepare, "worker": worker, "compare": compare}[args.command](args)


if __name__ == "__main__":
    main()
