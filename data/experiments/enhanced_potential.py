"""Bounded, preregistered search study using shared players, arena and replay/scoring.

Run with QI_PLAYERS_CONFIG pointing at the pinned Pikafish binding. Source snapshots
retain dirty-code bytes; this script is an experiment, not a new benchmark protocol.
"""

import argparse
import hashlib
import json
import tarfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from qi.arena import play_match
from qi.artifacts import provenance, write_json
from qi.benchmark.models import Book
from qi.evaluation import EvalGame, EvalRun, EvalSpec, summarize_evaluation
from qi.game import legal_moves, replay
from qi.players import PlayerConfig, bind_config, choose
from qi.players.catalog import get_player


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory):
    """Reconstruct summaries only from validated saved game evidence."""
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if sha(directory / name) != expected:
            raise ValueError(f"Changed source/config artifact: {name}")
    results = {}
    completed = failed = 0
    for name in manifest["runs"]:
        path = directory / f"{name}.json"
        run = EvalRun.model_validate_json(path.read_text())
        summary = summarize_evaluation(run).model_dump(mode="json")
        costs = {}
        for who in ("a", "b"):
            choices = [
                t.choice for g in run.games if g.match for t in g.match.turns if (t.side == g.a_side) == (who == "a")
            ]
            n = len(choices)
            costs[who] = {
                "decisions": n,
                "mean_move_ms": sum(c.elapsed_ms for c in choices) / n if n else None,
                "mean_completed_depth": sum(c.completed_depth for c in choices) / n if n else None,
                "fallback_decisions": sum(c.completed_depth == 0 for c in choices),
                "qi_nodes": sum(c.nodes for c in choices),
                "qnodes": sum(c.qnodes for c in choices),
                "see_nodes": sum(c.search_stats.see_nodes for c in choices if c.search_stats),
                "engine_nodes": sum(c.engine.reported_nodes or 0 for c in choices if c.engine),
            }
        completed += summary["players"]["a"]["completed_games"]
        failed += summary["players"]["a"]["failed_games"]
        results[name] = {
            "summary": summary,
            "costs": costs,
            "terminations": dict(Counter(g.match.reason for g in run.games if g.match)),
            "sha256": sha(path),
        }
    output = {
        "id": manifest["id"],
        "planned_games": 72,
        "completed_games": completed,
        "failed_games": failed,
        "selected": manifest.get("selected"),
        "runs": results,
        "manifest_sha256": sha(directory / "manifest.json"),
        "verified": True,
        "verification": (
            "Every retained game replayed; identities, choices, hard budgets and terminal outcomes validated. "
            "Source/config archive hashes checked."
        ),
    }
    write_json(directory / "summary.json", output, indent=2)
    return output


def execute(config_path, directory):
    cfg = json.loads(config_path.read_text())
    book = Book.model_validate_json(Path(cfg["book"]).read_text())
    if book.use != "development":
        raise ValueError("This exploratory study only accepts development books.")
    seen, starts = set(), []
    for start in book.starts:
        if start.family not in seen:
            starts.append(start)
            seen.add(start.family)
        if len(starts) == cfg["screen_families"] + cfg["followup_families"]:
            break
    if len(starts) != cfg["screen_families"] + cfg["followup_families"]:
        raise ValueError("Insufficient distinct development families.")
    profiles = {k: bind_config(PlayerConfig(**v, seed=cfg["seed"])) for k, v in cfg["profiles"].items()}
    opponents = {k: bind_config(PlayerConfig(**v, seed=cfg["seed"])) for k, v in cfg["opponents"].items()}
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "config.json", cfg, indent=2)
    write_json(directory / "starts.json", [s.model_dump(mode="json") for s in starts], indent=2)
    source_files = [
        *sorted(Path("src/qi").rglob("*.py")),
        Path("uv.lock"),
        Path("pyproject.toml"),
        Path(__file__),
        config_path,
    ]
    with tarfile.open(directory / "source.tar.gz", "w:gz") as archive:
        for path in source_files:
            archive.add(path, arcname=str(path.resolve().relative_to(Path.cwd())))
    manifest = {
        "id": cfg["id"],
        "provenance": provenance(),
        "profiles": {k: asdict(v) for k, v in profiles.items()},
        "opponents": {k: asdict(v) for k, v in opponents.items()},
        "files": {name: sha(directory / name) for name in ("config.json", "starts.json", "source.tar.gz")},
        "runs": [],
    }
    write_json(directory / "manifest.json", manifest, indent=2)
    probes = []
    for index, start in enumerate(starts):
        settings = [(kind, nodes) for kind, budgets in cfg["probes"].items() for nodes in budgets]
        # Rotate recipe order; clear referee caches for each independent decision.
        settings = settings[index % len(settings) :] + settings[: index % len(settings)]
        for kind, nodes in settings:
            game = start.snapshot.game()
            legal_moves.cache_clear()
            replay.cache_clear()
            choice = choose(game, PlayerConfig(kind, seed=cfg["seed"], nodes=nodes, depth=4))
            probes.append(
                {"start": start.id, "family": start.family, "kind": kind, "budget": nodes, "choice": asdict(choice)}
            )
            write_json(directory / "probes.json", probes)
        print(f"probes {index + 1}/{len(starts)}", flush=True)
    manifest["files"]["probes.json"] = sha(directory / "probes.json")
    deadline = perf_counter() + cfg["game_seconds"]
    game_started = perf_counter()
    runs = {}

    def prepare(name, a, b, subset):
        spec = EvalSpec(
            schema_version=2 if a.binding_sha256 or b.binding_sha256 else 1,
            corpus=book.corpus([s.id for s in subset]),
            player_a=a,
            player_b=b,
        )
        run = EvalRun(
            schema_version=spec.schema_version,
            spec=spec,
            spec_sha256=spec.digest,
            provenance=manifest["provenance"],
            player_versions={"a": get_player(a.kind).info.version, "b": get_player(b.kind).info.version},
            games=[EvalGame(opening_id=s.id, a_side=side) for s in subset for side in ("red", "black")],
        )
        runs[name] = run
        manifest["runs"].append(name)
        write_json(directory / f"{name}.json", run.model_dump(mode="json"))
        write_json(directory / "manifest.json", manifest, indent=2)

    def play(names):
        # Interleave profiles by opening/color and rotate their order.
        for index in range(max(len(runs[name].games) for name in names)):
            order = names[index % len(names) :] + names[: index % len(names)]
            for name in order:
                run = runs[name]
                if index >= len(run.games) or any(g.status == "failed" for g in run.games):
                    continue
                if perf_counter() >= deadline:
                    return
                entry = run.games[index]
                entry.status = "running"
                write_json(directory / f"{name}.json", run.model_dump(mode="json"))
                try:
                    red, black = run.spec.configurations(index // 2, entry.a_side)
                    legal_moves.cache_clear()
                    replay.cache_clear()
                    match = play_match(red, black, run.spec.corpus.openings[index // 2].snapshot.game())
                    done = EvalGame(opening_id=entry.opening_id, a_side=entry.a_side, status="complete", match=match)
                    run.validate_match(index // 2, done)
                    run.games[index] = done
                    score = "D" if match.winner is None else "W" if match.winner == entry.a_side else "L"
                    print(
                        f"{name} {index + 1}/{len(run.games)} {score} {match.reason} "
                        f"{len(match.turns)} plies; {perf_counter() - game_started:.1f}s",
                        flush=True,
                    )
                except (Exception, KeyboardInterrupt) as exc:
                    entry.status = "incomplete" if isinstance(exc, KeyboardInterrupt) else "failed"
                    entry.error = f"{type(exc).__name__}: {exc}"
                    print(f"{name}: {entry.error}", flush=True)
                write_json(directory / f"{name}.json", run.model_dump(mode="json"))
                if run.games[index].status == "incomplete":
                    return

    screen = starts[: cfg["screen_families"]]
    followup = starts[cfg["screen_families"] :]
    for key, profile in profiles.items():
        prepare(f"screen-{key}", profile, opponents["small"], screen)
    play(list(runs))
    candidates = {key: summarize_evaluation(runs[f"screen-{key}"]) for key in profiles if key != "original"}
    if all(result.status == "complete" for result in candidates.values()):
        selected = min(
            candidates,
            key=lambda key: (
                -candidates[key].players["a"].score_rate,
                candidates[key].players["a"].mean_elapsed_ms,
                key,
            ),
        )
        manifest["selected"] = selected
        print(f"selected {selected}", flush=True)
        for key, opponent in opponents.items():
            prepare(f"followup-{key}", profiles[selected], opponent, followup)
        prepare("followup-control", profiles[selected], profiles["original"], followup[: cfg["control_families"]])
        play(["followup-small", "followup-large", "followup-control"])
    manifest["game_elapsed_seconds"] = perf_counter() - game_started
    manifest["files"].update({f"{name}.json": sha(directory / f"{name}.json") for name in manifest["runs"]})
    write_json(directory / "manifest.json", manifest, indent=2)
    result = verify(directory)
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify), indent=2))
    elif args.config and args.output:
        execute(args.config, args.output)
    else:
        parser.error("Use --config FILE --output FRESH_DIRECTORY or --verify DIRECTORY.")
