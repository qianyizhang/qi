"""Post-game baseline-equivalence and fixed-position CPU diagnostics for AB-EVAL-006."""

import argparse
import cProfile
import hashlib
import io
import json
import pstats
import subprocess
import sys
import types
from dataclasses import asdict, replace
from functools import partial
from pathlib import Path

from qi.artifacts import write_json
from qi.benchmark.models import BookStart
from qi.game import legal_moves, replay
from qi.players import PlayerConfig, choose
from qi.players.components.extensions import CheckExtensions
from qi.players.components.positional import breakdown, evaluate
from qi.players.quiescence import quiesce


def diagnose(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    commit = manifest["provenance"]["commit"]
    baseline = subprocess.run(
        ["git", "show", f"{commit}:src/qi/players/alphabeta/__init__.py"], check=True, capture_output=True, text=True
    ).stdout
    (directory / "baseline-alphabeta.py").write_text(baseline)
    module = types.ModuleType("qi_baseline_alphabeta")
    sys.modules[module.__name__] = module
    exec(compile(baseline, str(directory / "baseline-alphabeta.py"), "exec"), module.__dict__)
    starts = [BookStart.model_validate(x) for x in json.loads((directory / "starts.json").read_text())]
    probes = json.loads((directory / "probes.json").read_text())
    original = {p["start"]: p["choice"] for p in probes if p["kind"] == "alphabeta-enhanced" and p["budget"] == 128}
    options = module.SearchOptions(
        evaluator=evaluate, ordering=True, exchange=True, extensions=CheckExtensions(2), table_capacity=2048
    )
    checks = []
    for start in starts:
        game = start.snapshot.game()
        old = replace(
            module.search(
                game, PlayerConfig(nodes=128, depth=4), partial(quiesce, evaluator=evaluate), options=options
            ),
            evaluation=breakdown(game),
        )
        differences = [key for key, value in asdict(old).items() if value != original[start.id][key]]
        if differences:
            raise ValueError(f"Baseline changed: {start.id}: {differences}")
        checks.append(start.id)
    game = starts[0].snapshot.game()
    legal_moves.cache_clear()
    replay.cache_clear()
    profile = cProfile.Profile()
    choice = profile.runcall(choose, game, PlayerConfig("alphabeta-pvs", nodes=1024, depth=4, seed=7))
    profile.dump_stats(directory / "profile.pstats")
    stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(25)
    stats.sort_stats("tottime").print_stats(15)
    (directory / "profile.txt").write_text(stream.getvalue())
    functions = [
        {
            "file": key[0],
            "line": key[1],
            "name": key[2],
            "primitive_calls": value[0],
            "calls": value[1],
            "self_seconds": value[2],
            "cumulative_seconds": value[3],
        }
        for key, value in pstats.Stats(profile).stats.items()
    ]
    result = {
        "baseline_commit": commit,
        "baseline_source_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
        "baseline_equivalent_starts": checks,
        "baseline_fields": "Every Decision field, excluding elapsed time.",
        "profile_start": starts[0].id,
        "profile_config": {"kind": "alphabeta-pvs", "nodes": 1024, "depth": 4, "seed": 7},
        "profile_choice": asdict(choice),
        "profile_total_seconds": stats.total_tt,
        "profile_functions": sorted(functions, key=lambda x: -x["cumulative_seconds"]),
        "limitations": "One instrumented decision locates costs; it is not a timing comparison or strength evidence.",
    }
    write_json(directory / "diagnostics.json", result, indent=2)
    print(f"Original enhanced unchanged on {len(checks)}/{len(starts)} frozen starts.")
    print(stream.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    diagnose(parser.parse_args().run)
