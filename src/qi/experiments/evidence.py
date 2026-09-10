"""Replay and recompute before presenting evidence; saved summaries are not authority."""

import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path

from pydantic import TypeAdapter

from qi.experiments.model import Plan, digest
from qi.game import Game
from qi.players.core import Choice, PlayerConfig
from qi.players.validation import validate_decision
from qi.protocol import Snapshot


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_choice(raw: dict, config: dict, game: Game, version: str, *, match: bool) -> Choice:
    choice = TypeAdapter(Choice).validate_python(raw)
    require(choice.state_hash == game.state_hash, "Choice state hash differs from replay.")
    require(choice.player_version == version, "Player version differs from manifest.")
    require(choice.seed == config["seed"] + (len(game.moves) if match else 0), "Choice seed differs from plan.")
    require(isfinite(choice.elapsed_ms) and choice.elapsed_ms >= 0, "Invalid measured latency.")
    validate_decision(choice, PlayerConfig(**config), game)
    require(
        choice.model_calls == 0 and choice.checkpoint_sha256 is None,
        "Unexpected learned inference in search experiment.",
    )
    return choice


def load_run(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    plan = Plan.model_validate(manifest["plan"])
    require(manifest["schema_version"] == 1, "Unsupported run schema.")
    require(
        manifest["plan_sha256"] == digest(manifest["plan"]) and manifest["corpus_sha256"] == plan.corpus.digest,
        "Manifest identity mismatch.",
    )
    jobs = {job["id"]: job for job in plan.jobs()}
    openings = {entry.id: entry for entry in plan.corpus.openings}
    units = []
    for path in sorted((directory / "units").glob("*.json")):
        unit = json.loads(path.read_text())
        job = unit["job"]
        require(path.stem in jobs and job == jobs[path.stem], "Unit differs from planned job.")
        require(unit["status"] in ("running", "complete", "incomplete", "failed"), "Unknown unit status.")
        game = openings[job["opening"]].snapshot.game()
        frames = [{"board": game.board, "side": game.turn}]
        for turn in unit["turns"]:
            require(
                not game.outcome and turn["side"] == game.turn and turn["ply"] == len(game.moves) + 1,
                "Turn does not follow replay.",
            )
            who = "a" if job["kind"] == "probe" or game.turn == job["a_side"] else "b"
            config = job[who]
            choice = check_choice(
                turn["choice"], config, game, manifest["player_versions"][config["kind"]], match=job["kind"] == "game"
            )
            game = game.apply(choice.move, choice.state_hash)
            frames.append({"board": game.board, "side": game.turn})
        require(Snapshot.model_validate(unit["snapshot"]).game() == game, "Saved final snapshot differs from replay.")
        if job["kind"] == "probe":
            require(
                len(unit["turns"]) <= 1 and (unit["status"] != "complete" or len(unit["turns"]) == 1),
                "Probe must have exactly one completed decision.",
            )
            require("outcome" not in unit, "Probe is not a match outcome.")
        elif unit["status"] == "complete":
            require(
                game.outcome is not None and unit.get("outcome") == asdict(game.outcome),
                "Completed match outcome differs from referee.",
            )
        else:
            require("outcome" not in unit, "Incomplete games must not carry an outcome.")
        units.append({**unit, "sha256": digest(unit), "frames": frames})
    status = json.loads((directory / "status.json").read_text())
    require(status["status"] in ("running", "complete", "deadline", "failed", "interrupted"), "Unknown run status.")
    completed = sum(unit["status"] == "complete" for unit in units)
    if status["status"] == "complete":
        require(completed == len(jobs), "Run claims completion with missing units.")
    # A process can stop between its atomic unit and status writes. Derive counts.
    return {
        "manifest": manifest,
        "preview": plan.preview(),
        "status": status,
        "units": units,
        "completed": completed,
        "planned": len(jobs),
        "validation": "replay, identities, seeds, budgets and counters checked",
        "directory": str(directory.resolve()),
    }


def comparable_choice(choice: dict) -> dict:
    return {key: value for key, value in choice.items() if key != "elapsed_ms"}
