"""Sequential execution with fresh paths and atomically saved partial evidence."""

import json
import os
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from qi.experiments.model import Plan, digest, provenance
from qi.players import PlayerConfig, choose
from qi.players.catalog import get_player
from qi.protocol import Snapshot


def write_json(path: Path, data) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        json.dump(data, stream, allow_nan=False, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def run(plan: Plan, directory: Path, seconds: float = 600, *, clock=monotonic) -> dict:
    if not 0 < seconds <= 3600:
        raise ValueError("Run allowance must be greater than zero and at most 3600 seconds.")
    plan = Plan.model_validate(plan.model_dump())
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "units").mkdir()
    manifest = {
        "schema_version": 1,
        "plan": plan.model_dump(mode="json"),
        "plan_sha256": digest(plan.model_dump(mode="json")),
        "corpus_sha256": plan.corpus.digest,
        "provenance": provenance(),
        "player_versions": {name: get_player(name).info.version for name in plan.players},
        "started_at": datetime.now(UTC).isoformat(),
        "allowance_seconds": seconds,
    }
    write_json(directory / "manifest.json", manifest)
    started = clock()
    deadline = started + seconds
    state = {"status": "running", "completed": 0, "elapsed_seconds": 0.0}
    write_json(directory / "status.json", state)
    openings = {entry.id: entry.snapshot for entry in plan.corpus.openings}
    active = None
    try:
        for job in plan.jobs():
            if clock() >= deadline:
                state["status"] = "deadline"
                break
            game = openings[job["opening"]].game()
            active = {"job": job, "status": "running", "turns": [], "snapshot": openings[job["opening"]].model_dump()}
            path = directory / "units" / (job["id"] + ".json")
            write_json(path, active)
            while not game.outcome:
                if clock() >= deadline:
                    active["status"] = "incomplete"
                    state["status"] = "deadline"
                    write_json(path, active)
                    break
                who = "a" if job["kind"] == "probe" or game.turn == job["a_side"] else "b"
                config = PlayerConfig(**job[who])
                if job["kind"] == "game":
                    config = replace(config, seed=config.seed + len(game.moves))
                choice = choose(game, config)
                active["turns"].append({"ply": len(game.moves) + 1, "side": game.turn, "choice": asdict(choice)})
                game = game.apply(choice.move, choice.state_hash)
                active["snapshot"] = Snapshot(moves=list(game.moves)).model_dump()
                if job["kind"] == "probe" or game.outcome:
                    active["status"] = "complete"
                    if job["kind"] == "game":
                        active["outcome"] = asdict(game.outcome)
                write_json(path, active)
                if active["status"] == "complete":
                    state["completed"] += 1
                    break
            write_json(directory / "status.json", {**state, "elapsed_seconds": clock() - started})
            if state["status"] == "deadline":
                break
        else:
            state["status"] = "complete"
    except (Exception, KeyboardInterrupt) as exc:
        state.update(
            status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        if active is not None:
            active.update(status="incomplete" if isinstance(exc, KeyboardInterrupt) else "failed", error=state["error"])
            write_json(directory / "units" / (active["job"]["id"] + ".json"), active)
    finally:
        state["elapsed_seconds"] = clock() - started
        write_json(directory / "status.json", state)
    return state
