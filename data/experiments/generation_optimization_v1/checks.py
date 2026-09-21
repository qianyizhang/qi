"""Independent comparison using portable identities, excluding failed attempts."""

import json
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path

from qi_game.contracts import Snapshot
from qi_game.reference import restore

from qi.artifacts import digest
from qi.players.policy.encoding import input_key
from qi.training_data.contracts import Example, classify_phase, state_fingerprint
from qi.training_data.store import GamePayload


def canonical(path: Path):
    games, occurrences, analyses = [], [], []
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        identities, snapshots, occurrence_keys = {}, {}, {}
        for game_id, payload, stop, outcome in db.execute(
            "SELECT id,json(payload),stop_reason,outcome FROM games WHERE status='complete' ORDER BY id"
        ):
            game = GamePayload.model_validate_json(payload)
            checked = restore(game.snapshot)
            expected = asdict(checked.outcome) if checked.outcome else None
            if (json.loads(outcome) if outcome else None) != expected:
                raise ValueError("Stored outcome differs from independent replay.")
            for decision in game.actor["generation_result"]["decisions"]:
                if decision["move"] != game.snapshot.moves[decision["ply"]]:
                    raise ValueError("Actor decision differs from history.")
            identities[game_id] = game.source_id
            snapshots[game_id] = game.snapshot
            games.append({"game": game.model_dump(exclude={"actor_ms"}), "stop": stop, "outcome": expected})
        if len(set(identities.values())) != len(identities):
            raise ValueError("Duplicate complete logical sources.")
        for oid, gid, ply, board, turn, state_hash, ihash, phase, payload in db.execute(
            "SELECT id,game_id,ply_count,board,turn,state_hash,input_hash,phase,json(payload) FROM position_occurrences"
        ):
            if gid not in identities:
                continue
            snapshot = Snapshot(moves=snapshots[gid].moves[:ply])
            checked = restore(snapshot)
            if (board, turn, state_hash, ihash, phase) != (
                checked.board,
                checked.turn,
                state_fingerprint(snapshot),
                input_key(checked),
                classify_phase(checked),
            ):
                raise ValueError("Occurrence differs from independent replay.")
            key = identities[gid], ply
            occurrence_keys[oid] = key
            occurrences.append([*key, board, turn, state_hash, ihash, phase, json.loads(payload)])
        for oid, status, raw in db.execute("SELECT occurrence_id,status,json(payload) FROM analyses"):
            if oid not in occurrence_keys:
                continue
            payload = json.loads(raw)
            answer = payload.get("answer")
            if answer:
                Example.model_validate({"analysis": answer, "source_ids": ["independent-verification"]})
                answer.pop("elapsed_ms", None)
                answer["settings"].pop("EvalFile", None)
                answer["search_info"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", s) for s in answer["search_info"]]
                payload["raw"] = [re.sub(r"\b(?:time|nps) \d+\s*", "", s) for s in payload["raw"]]
            analyses.append([*occurrence_keys[oid], status, payload])
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("SQLite integrity check failed.")
    return {"games": games, "occurrences": occurrences, "analyses": analyses}


def combined(paths):
    merged = {"games": [], "occurrences": [], "analyses": []}
    for path in paths:
        for name, rows in canonical(path).items():
            merged[name].extend(rows)
    ids = [g["game"]["source_id"] for g in merged["games"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Source ownership overlaps across collections.")
    merged = {name: sorted(rows, key=lambda value: json.dumps(value, sort_keys=True)) for name, rows in merged.items()}
    return {
        "sha256": digest(merged),
        "games": len(ids),
        "plies": sum(len(g["game"]["snapshot"]["moves"]) - len(g["game"]["initial"]["moves"]) for g in merged["games"]),
        "selected": sum(bool(row[-1]["metadata"].get("selected")) for row in merged["occurrences"]),
        "analyses": len(merged["analyses"]),
    }
