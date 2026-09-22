"""Validate and combine owned, inactive generation shards into a fresh collection."""

import json
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

from qi_game.execution import ReplaySession
from qi_game.trajectory import PythonTrajectory

from qi.players.policy.encoding import input_key
from qi.training_data.candidate_evidence import parse_candidates
from qi.training_data.contracts import classify_phase, fingerprint, observation_fingerprint, state_fingerprint
from qi.training_data.generation_runner import source_identity
from qi.training_data.store import AnalysisPayload, AnalysisSpec, Collection, OccurrencePayload, RunPayload


def _insert(db, table, row):
    # All table/column names come from the fixed schema, never user SQL.
    return db.execute(
        f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values())
    ).lastrowid


def _payload(db, value):
    return db.execute("SELECT json(?)", (value,)).fetchone()[0]


def _validate_game(source, row, config):
    expected = config.sources[0]
    game = source.game(row["id"])
    actor = game.actor
    if (
        game.source_id != row["logical_key"]
        or actor.get("source") != expected.id
        or type(actor.get("index")) is not int
        or not 0 <= actor["index"] < expected.games
        or game.initial != expected.start.snapshot
        or game.split != expected.split
        or (expected.start.family_id and game.family != expected.start.family_id)
        or game.parent_digest is not None
        or row["status"] == "running"
    ):
        raise ValueError("Shard game differs from its owned source or remains active.")
    identity, key = source_identity(config, expected, actor["index"])
    if key != game.source_id or any(actor.get(k) != value for k, value in identity.items()):
        raise ValueError("Game actor or source key differs from the frozen plan.")
    if min(game.actor_queries, game.actor_nodes, game.actor_ms) < 0:
        raise ValueError("Game work counters must be nonnegative.")
    state = source.inspect(game.snapshot)
    if game.snapshot.moves[: len(game.initial.moves)] != game.initial.moves:
        raise ValueError("Game does not extend its declared start.")
    if row["status"] == "complete":
        outcome = asdict(state.outcome) if state.outcome else None
        if (json.loads(row["outcome"]) if row["outcome"] else None) != outcome:
            raise ValueError("Game outcome differs from replay.")
        if row["stop_reason"] not in {"terminal", "ply-budget"} or (row["stop_reason"] == "terminal") != bool(outcome):
            raise ValueError("Invalid completed game disposition.")
        if not outcome and len(game.snapshot.moves) - len(game.initial.moves) != expected.additional_plies:
            raise ValueError("Completed game did not exhaust its horizon.")
        result = actor["generation_result"]
        if (result["source"], result["index"]) != (expected.id, actor["index"]):
            raise ValueError("Generation result differs from source ownership.")
        for decision in result["decisions"]:
            if game.snapshot.moves[decision["ply"]] != decision["move"]:
                raise ValueError("Actor decision differs from replay.")
    return game


def _copy_game(source, target, row, run_id, specs, config):
    game = _validate_game(source, row, config)
    db = target.db
    if db.execute("SELECT 1 FROM games WHERE family=? AND split!=?", (game.family, game.split)).fetchone():
        raise ValueError("Cross-shard source family crosses splits.")
    if (
        game.initial.moves
        and db.execute(
            "SELECT 1 FROM games WHERE json_extract(payload,'$.initial')=json(?) AND family!=?",
            (game.initial.model_dump_json(), game.family),
        ).fetchone()
    ):
        raise ValueError("Cross-shard noninitial start has conflicting families.")
    if (
        row["status"] == "complete"
        and db.execute(
            "SELECT 1 FROM games WHERE trajectory=? AND split!=? AND status='complete'",
            (row["trajectory"], game.split),
        ).fetchone()
    ):
        raise ValueError("Cross-shard completed trajectory crosses splits.")
    record = dict(row)
    record.pop("id")
    record["run_id"] = run_id
    new_game = _insert(db, "games", record)
    order = db.execute("SELECT coalesce(max(success_order),0) FROM analyses").fetchone()[0]
    # Preserve success ordering within each occurrence/spec, independently of worker completion order.
    for occurrence in source.db.execute("SELECT * FROM position_occurrences WHERE game_id=? ORDER BY id", (row["id"],)):
        snapshot = source.snapshot(occurrence["id"])
        state = source.inspect(snapshot)
        identity = fingerprint(
            "occurrence-v1",
            {"game_attempt": row["attempt"], "ply": len(snapshot.moves), "state": state_fingerprint(snapshot)},
        )
        if not len(game.initial.moves) <= len(snapshot.moves) <= len(game.snapshot.moves):
            raise ValueError("Occurrence is outside its game's continuation.")
        actual = tuple(
            occurrence[k]
            for k in (
                "identity",
                "board",
                "turn",
                "board_hash",
                "state_hash",
                "observation_hash",
                "input_hash",
                "phase",
            )
        )
        if actual != (
            identity,
            state.board,
            state.turn,
            fingerprint("board-turn-v1", {"ruleset": snapshot.ruleset, "board": state.board, "turn": state.turn}),
            state_fingerprint(snapshot),
            observation_fingerprint(state),
            input_key(state),
            classify_phase(state),
        ):
            raise ValueError("Occurrence differs from replay or portable identity.")
        OccurrencePayload.model_validate_json(_payload(source.db, occurrence["payload"]))
        record = dict(occurrence)
        record.pop("id")
        record["game_id"] = new_game
        new_occurrence = _insert(db, "position_occurrences", record)
        for analysis in source.db.execute(
            "SELECT * FROM analyses WHERE occurrence_id=? ORDER BY success_order IS NOT NULL,success_order,id",
            (occurrence["id"],),
        ):
            payload = AnalysisPayload.model_validate_json(_payload(source.db, analysis["payload"]))
            spec_id, spec = specs[analysis["spec_id"]]
            request = fingerprint("analysis-request-v1", {"state": state_fingerprint(snapshot), "spec": spec.identity})
            if analysis["request"] != request or analysis["status"] == "running":
                raise ValueError("Analysis request differs from its occurrence/spec or remains active.")
            if analysis["status"] == "success":
                answer = payload.answer
                if (
                    answer is None
                    or answer.snapshot != snapshot
                    or AnalysisSpec.from_analysis(answer) != spec
                    or answer.move != analysis["move"]
                ):
                    raise ValueError("Successful analysis differs from its request.")
                source.validate_example(answer)
                if payload.candidates != parse_candidates(answer, execution=source._execution):
                    raise ValueError("Candidate evidence differs from the retained answer.")
            elif payload.answer is not None:
                raise ValueError("Unsuccessful analysis contains a successful answer.")
            record = dict(analysis)
            record.pop("id")
            record.update(occurrence_id=new_occurrence, spec_id=spec_id)
            if analysis["success_order"] is not None:
                order += 1
                record["success_order"] = order
            _insert(db, "analyses", record)


def combine_shards(shards: list[Path], configs, destination: Path, *, check=lambda: None) -> dict:
    """Build a fresh unpublished file in source order, retaining every attempt.

    Callers own shard writer locks. One game (at most 300 plies) is validated and
    committed at a time; failed builds remain evidence and are never published.
    """
    if destination.exists() or len(shards) != len(configs):
        raise ValueError("Combination requires a fresh destination and one config per shard.")
    with Collection(destination) as target:
        for path, config in zip(shards, configs, strict=True):
            check()
            with ExitStack() as stack:
                source = stack.enter_context(Collection(path, readonly=True))
                execution = stack.enter_context(ReplaySession(PythonTrajectory))
                stack.enter_context(source.executing(execution))
                if (
                    source.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                    or source.db.execute("PRAGMA foreign_key_check").fetchone()
                ):
                    raise ValueError("Corrupt shard database.")
                runs = source.db.execute("SELECT * FROM generation_runs").fetchall()
                if len(runs) != 1 or runs[0]["status"] != "complete":
                    raise ValueError("A shard must contain one completed logical run.")
                run = dict(runs[0])
                payload = RunPayload.model_validate_json(_payload(source.db, run["payload"]))
                if (
                    payload.config.get("recipe") != config.model_dump()
                    or payload.planned_games != config.sources[0].games
                ):
                    raise ValueError("Shard run differs from its frozen recipe.")
                if run["identity"] != fingerprint(
                    "collection-run-v1",
                    {"config": payload.config, "seed": payload.seed, "planned_games": payload.planned_games},
                ):
                    raise ValueError("Shard run identity differs from its payload.")
                disposed = source.db.execute(
                    "SELECT count(DISTINCT logical_key) FROM games WHERE status='complete' "
                    "OR (status='failed' AND stop_reason='rejected-trajectory')"
                ).fetchone()[0]
                if disposed != payload.planned_games:
                    raise ValueError("Shard has incomplete source ownership.")
                run.pop("id")
                with target.db:
                    run_id = _insert(target.db, "generation_runs", run)
                specs = {}
                for row in source.db.execute("SELECT * FROM analysis_specs ORDER BY id"):
                    spec = AnalysisSpec.model_validate_json(_payload(source.db, row["payload"]))
                    if spec.identity != row["identity"]:
                        raise ValueError("Invalid analysis specification identity.")
                    specs[row["id"]] = target.spec(spec, json.loads(_payload(source.db, row["locators"]))), spec
                for row in source.db.execute("SELECT * FROM games ORDER BY id"):
                    check()
                    with target.db:
                        _copy_game(source, target, row, run_id, specs, config)
        if target.db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Combined collection contains broken references.")
        counts = target.counts()
        target.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        target.db.execute("PRAGMA journal_mode=DELETE")
    return counts
