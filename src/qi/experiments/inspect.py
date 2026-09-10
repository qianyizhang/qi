"""Trace a selected saved decision under its original code and deterministic inputs."""

import json
from dataclasses import asdict, replace
from pathlib import Path

from qi.experiments.evidence import check_choice, comparable_choice, load_run, require
from qi.experiments.model import digest, provenance
from qi.experiments.runner import write_json
from qi.players import PlayerConfig, choose
from qi.players.trace import Recorder, recording
from qi.protocol import Snapshot


def inspect_decision(directory: Path, unit_id: str, turn_index: int, output: Path, limit: int = 100_000) -> dict:
    require(not output.exists(), "Choose a fresh trace path.")
    run = load_run(directory)
    current = provenance()
    saved = run["manifest"]["provenance"]
    require(current["source_sha256"] is not None, "Tracing requires a known checkout source identity.")
    require(
        all(current[key] == saved[key] for key in ("source_sha256", "python", "packages")),
        "Code or runtime changed; run a new benchmark before tracing.",
    )
    unit = next((unit for unit in run["units"] if unit["job"]["id"] == unit_id), None)
    require(unit is not None and 0 <= turn_index < len(unit["turns"]), "Unknown unit or decision index.")
    job = unit["job"]
    turn = unit["turns"][turn_index]
    game = Snapshot(moves=unit["snapshot"]["moves"][: turn["ply"] - 1]).game()
    who = "a" if job["kind"] == "probe" or game.turn == job["a_side"] else "b"
    config = PlayerConfig(**job[who])
    if job["kind"] == "game":
        config = replace(config, seed=config.seed + len(game.moves))
    recorder = Recorder(limit)
    with recording(recorder):
        choice = asdict(choose(game, config))
    equal = digest(comparable_choice(choice)) == digest(comparable_choice(turn["choice"]))
    require(equal, "Traced decision differs from benchmark; no trace published.")
    trace = {
        "schema_version": 1,
        "unit_id": unit_id,
        "turn_index": turn_index,
        "unit_sha256": unit["sha256"],
        "source_sha256": current["source_sha256"],
        "snapshot": Snapshot(moves=list(game.moves)).model_dump(),
        "config": asdict(config),
        "choice": choice,
        "decision_equal": equal,
        "recording": recorder.export(),
    }
    validate_trace(trace, unit, run["manifest"])
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, trace)
    return {
        "path": str(output.resolve()),
        "events": len(recorder.events),
        "complete": recorder.dropped == 0,
        "decision_equal": equal,
    }


def validate_trace(trace: dict, unit: dict, manifest: dict) -> None:
    require(
        trace["schema_version"] == 1
        and trace["unit_id"] == unit["job"]["id"]
        and trace["unit_sha256"] == unit["sha256"],
        "Trace source unit mismatch.",
    )
    require(
        trace["source_sha256"] is not None and trace["source_sha256"] == manifest["provenance"]["source_sha256"],
        "Trace code identity missing or mismatched.",
    )
    index = trace["turn_index"]
    require(0 <= index < len(unit["turns"]), "Trace decision index is invalid.")
    turn = unit["turns"][index]
    game = Snapshot(moves=unit["snapshot"]["moves"][: turn["ply"] - 1]).game()
    require(Snapshot.model_validate(trace["snapshot"]).game() == game, "Trace snapshot differs from selected position.")
    job = unit["job"]
    who = "a" if job["kind"] == "probe" or game.turn == job["a_side"] else "b"
    config = dict(job[who])
    if job["kind"] == "game":
        config["seed"] += len(game.moves)
    require(trace["config"] == config, "Trace configuration differs from selected decision.")
    check_choice(trace["choice"], config, game, manifest["player_versions"][config["kind"]], match=False)
    require(
        trace["decision_equal"]
        and digest(comparable_choice(trace["choice"])) == digest(comparable_choice(unit["turns"][index]["choice"])),
        "Trace decision parity failed.",
    )
    recording_data = trace["recording"]
    events = recording_data["events"]
    require(
        len(events) <= recording_data["event_limit"]
        and recording_data["dropped_events"] >= 0
        and recording_data["complete"] == (recording_data["dropped_events"] == 0),
        "Invalid trace completeness.",
    )
    visits = []
    for index, item in enumerate(events):
        require(
            item["id"] == index and (item["parent"] is None or 0 <= item["parent"] < index),
            "Trace is not an ordered tree.",
        )
        if "board" in item:
            require(len(item["board"]) == 90 and set(item["board"]) <= set(".KABNRCPkabnrcp"), "Invalid trace board.")
        if item["kind"] == "work":
            visits.append(item["visit"])
    require(visits == list(range(1, len(visits) + 1)), "Trace work sequence is inconsistent.")
    if recording_data["complete"]:
        require(len(visits) == trace["choice"]["nodes"], "Complete trace omitted charged work.")


def load_traces(directory: Path, run: dict) -> list[dict]:
    units = {unit["job"]["id"]: unit for unit in run["units"]}
    traces = []
    for path in sorted((directory / "traces").glob("*.json")):
        trace = json.loads(path.read_text())
        require(trace["unit_id"] in units, "Trace names an unknown unit.")
        validate_trace(trace, units[trace["unit_id"]], run["manifest"])
        traces.append(trace)
    return traces
