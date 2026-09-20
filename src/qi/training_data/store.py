"""Incremental local collection. One process owns writes; every operation commits a bounded unit."""

import fcntl
import json
import sqlite3
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time
from typing import Literal
from uuid import uuid4

from pydantic import ConfigDict, Field, JsonValue, model_validator
from qi_game.contracts import Snapshot
from qi_game.core import RULESET, START_FEN
from qi_game.execution import ReplaySession
from qi_game.reference import restore

from qi.players.policy.encoding import input_key
from qi.teacher import TeacherAnalysis
from qi.training_data.candidate_evidence import CandidateEvidence, parse_candidates
from qi.training_data.contracts import (
    PHASE_POLICY,
    Contract,
    Example,
    SourcePlan,
    classify_phase,
    fingerprint,
    observation_fingerprint,
    state_fingerprint,
    supervision_spec,
)


class TrajectorySplitConflict(ValueError):
    """A completed trajectory already belongs to the other split."""


class RunPayload(Contract):
    version: Literal[1] = 1
    config: dict[str, JsonValue]
    provenance: dict[str, JsonValue]
    seed: int
    planned_games: int = Field(ge=0)
    executions: list[dict[str, JsonValue]] = Field(default_factory=list)


class GamePayload(Contract):
    version: Literal[1] = 1
    source_id: str
    family: str
    split: Literal["train", "validation"]
    mode: Literal["random", "teacher-guided"]
    initial: Snapshot
    snapshot: Snapshot
    actor: dict[str, JsonValue]
    plan: SourcePlan | None = None
    themes: list[str] = Field(default_factory=list)
    objective: Literal["win-in-one"] | None = None
    actor_queries: int = 0
    actor_nodes: int = 0
    actor_ms: float = 0.0
    parent_digest: str | None = None


class _ActorWork(Contract):
    model_config = ConfigDict(frozen=True)
    actor_queries: int
    actor_nodes: int
    actor_ms: float


@dataclass(frozen=True, slots=True)
class _AppendState:
    # Exact persisted bytes prove validation reuse, not semantic identity.
    record: tuple[int, bytes, str, str, str]
    moves: tuple[str, ...]
    work: _ActorWork
    normalized: str | None = None


class OccurrencePayload(Contract):
    version: Literal[1] = 1
    phase_method: str = PHASE_POLICY
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class SupervisionIdentity(Contract):
    target: Literal["legal-teacher-move-v1"]
    authority: Literal["teacher-preference"]
    adapter: Literal["uci-teacher-v1", "uci-teacher-v2"]
    engine_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    network_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    settings: dict[str, str]
    nodes: int = Field(ge=1)
    depth: int | None = Field(ge=1, le=64)


class AnalysisSpec(Contract):
    version: Literal[1] = 1
    supervision: dict[str, JsonValue]
    timeout_seconds: float = Field(gt=0, le=120)
    output_contract: Literal["teacher-analysis-v1-v2"] = "teacher-analysis-v1-v2"

    @model_validator(mode="after")
    def validate_supervision(self):
        SupervisionIdentity.model_validate(self.supervision)
        return self

    @property
    def identity(self) -> str:
        return fingerprint("collection-analysis-spec-v1", self.model_dump())

    @classmethod
    def from_analysis(cls, analysis: TeacherAnalysis):
        return cls(supervision=supervision_spec(analysis), timeout_seconds=float(analysis.timeout_seconds))


class AnalysisPayload(Contract):
    version: Literal[1] = 1
    answer: TeacherAnalysis | None = None
    failure: str | None = None
    raw: list[str] = Field(default_factory=list)
    candidates: list[CandidateEvidence] = Field(default_factory=list)
    coverage: Literal["unknown"] = "unknown"


def board_identity(snapshot: Snapshot) -> str:
    game = restore(snapshot)
    return fingerprint("board-turn-v1", {"ruleset": snapshot.ruleset, "board": game.board, "turn": game.turn})


# Version 0 -> 1 is the initial migration. Future versions append migrations;
# unknown/newer schemas fail closed. JSONB validity is enforced even for direct SQL.
DDL = """
CREATE TABLE generation_runs (
 id INTEGER PRIMARY KEY, identity TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL CHECK(status IN ('running','complete','failed','interrupted')),
 created REAL NOT NULL, updated REAL NOT NULL, failure TEXT,
 payload BLOB NOT NULL CHECK(json_valid(payload,8))
) STRICT;
CREATE TABLE games (
 id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES generation_runs(id),
 logical_key TEXT NOT NULL, attempt TEXT NOT NULL UNIQUE,
 family TEXT NOT NULL, split TEXT NOT NULL CHECK(split IN ('train','validation')),
 status TEXT NOT NULL CHECK(status IN ('running','complete','failed','interrupted')),
 stop_reason TEXT, outcome TEXT, trajectory TEXT NOT NULL,
 created REAL NOT NULL, updated REAL NOT NULL, failure TEXT,
 payload BLOB NOT NULL CHECK(json_valid(payload,8))
) STRICT;
CREATE UNIQUE INDEX completed_source ON games(run_id,logical_key) WHERE status='complete';
CREATE UNIQUE INDEX running_source ON games(run_id,logical_key) WHERE status='running';
CREATE INDEX source_attempts ON games(run_id,logical_key,status);
CREATE INDEX families ON games(family,split);
CREATE INDEX starts ON games(json_extract(payload,'$.initial'));
CREATE INDEX trajectories ON games(trajectory,split);
CREATE TABLE position_occurrences (
 id INTEGER PRIMARY KEY, game_id INTEGER NOT NULL REFERENCES games(id), identity TEXT NOT NULL UNIQUE,
 ply_count INTEGER NOT NULL CHECK(ply_count BETWEEN 0 AND 300),
 board TEXT NOT NULL CHECK(length(board)=90), turn TEXT NOT NULL CHECK(turn IN ('red','black')),
 board_hash TEXT NOT NULL, state_hash TEXT NOT NULL, observation_hash TEXT NOT NULL, input_hash TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase IN ('opening','middlegame','endgame','unknown')),
 payload BLOB NOT NULL CHECK(json_valid(payload,8)), UNIQUE(game_id,ply_count)
) STRICT;
CREATE INDEX boards ON position_occurrences(board_hash);
CREATE INDEX inputs ON position_occurrences(input_hash);
CREATE TABLE analysis_specs (
 id INTEGER PRIMARY KEY, identity TEXT NOT NULL UNIQUE,
 payload BLOB NOT NULL CHECK(json_valid(payload,8)),
 locators BLOB NOT NULL CHECK(json_valid(locators,8))
) STRICT;
CREATE TABLE analyses (
 id INTEGER PRIMARY KEY, occurrence_id INTEGER NOT NULL REFERENCES position_occurrences(id),
 spec_id INTEGER NOT NULL REFERENCES analysis_specs(id), attempt TEXT NOT NULL UNIQUE,
 request TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('running','success','failed','interrupted')),
 created REAL NOT NULL, finished REAL, success_order INTEGER UNIQUE,
 move TEXT, payload BLOB NOT NULL CHECK(json_valid(payload,8)),
 CHECK((status='success')=(success_order IS NOT NULL)),
 CHECK((status='success')=(move IS NOT NULL))
) STRICT;
CREATE INDEX analysis_resolution ON analyses(occurrence_id,spec_id,status,success_order);
CREATE TRIGGER occurrence_identity BEFORE UPDATE OF game_id,identity,ply_count,board,turn,board_hash,state_hash,
 observation_hash,input_hash ON position_occurrences BEGIN SELECT RAISE(ABORT,'immutable occurrence'); END;
CREATE TRIGGER immutable_spec BEFORE UPDATE ON analysis_specs BEGIN SELECT RAISE(ABORT,'immutable spec'); END;
CREATE TRIGGER finalized_analysis BEFORE UPDATE ON analyses WHEN OLD.status!='running'
 BEGIN SELECT RAISE(ABORT,'immutable finalized analysis'); END;
PRAGMA user_version=1;
"""


class Collection(AbstractContextManager):
    """A writer holds an advisory process lock; readers never perform recovery."""

    def __init__(self, path: Path, *, readonly: bool = False):
        self.path, self.readonly = Path(path).resolve(), readonly
        self._execution: ReplaySession | None = None
        self._append_cache: _AppendState | None = None
        self.lock = None
        self.db = None
        if not readonly:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.lock = self.path.with_suffix(self.path.suffix + ".writer.lock").open("a")
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.lock.close()
                raise ValueError("Collection already has a writer.") from None
        try:
            self.db = sqlite3.connect(self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rwc"), uri=True)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA cache_size=-8192")
            self.db.execute("PRAGMA temp_store=FILE")
            try:
                self.db.execute("SELECT json(jsonb('{}')),json_valid(jsonb('{}'),8)").fetchone()
            except sqlite3.Error as exc:
                raise ValueError("Collection requires SQLite JSONB and json_valid flags (SQLite 3.45+).") from exc
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0 and not readonly:
                if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
                    raise ValueError("Unversioned nonempty database is not a collection.")
                self.db.executescript("BEGIN IMMEDIATE;\n" + DDL + "\nCOMMIT;")
            elif version != 1:
                raise ValueError(f"Unsupported collection schema {version}; expected 1.")
            if not readonly:
                self.db.execute("PRAGMA journal_mode=WAL")
                self.db.execute("PRAGMA synchronous=FULL")
                self.recover()
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        self._append_cache = None
        if self.db is not None:
            self.db.close()
        if self.lock is not None and not self.lock.closed:
            self.lock.close()

    @contextmanager
    def executing(self, execution: ReplaySession | None):
        """Temporarily use one caller-owned referee session; never bypass SQL checks."""
        if self._execution is not None:
            raise RuntimeError("Collection already has an execution session.")
        self._execution = execution
        try:
            yield
        finally:
            self._execution = None

    def inspect(self, snapshot: Snapshot):
        return self._execution.inspect(snapshot) if self._execution is not None else restore(snapshot)

    def validate_example(self, answer: TeacherAnalysis):
        return Example.model_validate(
            {"analysis": answer, "source_ids": ["validation"]}, context={"execution": self._execution}
        )

    def recover(self):
        for row in self.db.execute("SELECT id FROM games WHERE status='running'"):
            self.inspect(self.game(row[0]).snapshot)
            for occurrence in self.db.execute("SELECT id FROM position_occurrences WHERE game_id=?", (row[0],)):
                self.snapshot(occurrence[0])
        with self.db:
            self.db.execute(
                "UPDATE analyses SET status='interrupted',finished=?,payload=jsonb(?) WHERE status='running'",
                (time(), AnalysisPayload(failure="Writer interrupted before finalization").model_dump_json()),
            )
            for table in ("games", "generation_runs"):
                self.db.execute(
                    f"UPDATE {table} SET status='interrupted',updated=?,failure=? WHERE status='running'",
                    (time(), "Writer interrupted before completion"),
                )

    def run(self, payload: RunPayload) -> int:
        payload = RunPayload.model_validate(payload.model_dump())
        identity = fingerprint(
            "collection-run-v1",
            {"config": payload.config, "seed": payload.seed, "planned_games": payload.planned_games},
        )
        existing = self.db.execute(
            "SELECT id,json(payload) FROM generation_runs WHERE identity=?", (identity,)
        ).fetchone()
        event = {"started": time(), "provenance": payload.provenance}
        if existing:
            previous = RunPayload.model_validate_json(existing[1])
            previous.executions.append(event)
            with self.db:
                self.db.execute(
                    "UPDATE generation_runs SET payload=jsonb(?) WHERE id=?", (previous.model_dump_json(), existing[0])
                )
            return existing[0]
        payload.executions.append(event)
        with self.db:
            return self.db.execute(
                "INSERT INTO generation_runs(identity,status,created,updated,payload) "
                "VALUES (?,'running',?,?,jsonb(?))",
                (identity, time(), time(), payload.model_dump_json()),
            ).lastrowid

    def run_status(self, run: int, status: str, failure: str | None = None):
        payload = RunPayload.model_validate_json(
            self.db.execute("SELECT json(payload) FROM generation_runs WHERE id=?", (run,)).fetchone()[0]
        )
        if payload.executions:
            payload.executions[-1].update(status=status, updated=time(), failure=failure)
        if status == "complete":
            planned = RunPayload.model_validate_json(
                self.db.execute("SELECT json(payload) FROM generation_runs WHERE id=?", (run,)).fetchone()[0]
            ).planned_games
            count = self.db.execute(
                "SELECT count(DISTINCT logical_key) FROM games WHERE run_id=? "
                "AND (status='complete' OR (status='failed' AND stop_reason='rejected-trajectory'))",
                (run,),
            ).fetchone()[0]
            if count != planned:
                raise ValueError("Completed source count differs from run plan.")
        with self.db:
            self.db.execute(
                "UPDATE generation_runs SET status=?,failure=?,updated=?,payload=jsonb(?) WHERE id=?",
                (status, failure, time(), payload.model_dump_json(), run),
            )

    def begin_game(self, run: int, key: str, payload: GamePayload) -> int | None:
        payload = GamePayload.model_validate(payload.model_dump())
        if payload.snapshot != payload.initial:
            raise ValueError("New game must start at its declared initial prefix.")
        self.inspect(payload.initial)
        if self.db.execute(
            "SELECT 1 FROM games WHERE run_id=? AND logical_key=? AND status='complete'", (run, key)
        ).fetchone():
            return None
        if self.db.execute(
            "SELECT 1 FROM games WHERE family=? AND split!=?", (payload.family, payload.split)
        ).fetchone():
            raise ValueError("Source family crosses splits.")
        if (
            payload.initial.moves
            and self.db.execute(
                "SELECT 1 FROM games WHERE json_extract(payload,'$.initial')=json(?) AND family!=?",
                (payload.initial.model_dump_json(), payload.family),
            ).fetchone()
        ):
            raise ValueError("An exact noninitial start cannot mint another source family.")
        with self.db:
            return self.db.execute(
                "INSERT INTO games(run_id,logical_key,attempt,family,split,status,trajectory,created,updated,payload) "
                "VALUES (?,?,?,?,?,'running',?,?,?,jsonb(?))",
                (
                    run,
                    key,
                    uuid4().hex,
                    payload.family,
                    payload.split,
                    state_fingerprint(payload.snapshot),
                    time(),
                    time(),
                    payload.model_dump_json(),
                ),
            ).lastrowid

    @staticmethod
    def _validate_game(data, identity) -> GamePayload:
        payload = GamePayload.model_validate_json(data)
        if (payload.family, payload.split, state_fingerprint(payload.snapshot)) != identity:
            raise ValueError("Game payload differs from indexed identity.")
        return payload

    def game(self, game_id: int) -> GamePayload:
        row = self.db.execute(
            "SELECT json(payload),family,split,trajectory FROM games WHERE id=?", (game_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown game.")
        return self._validate_game(row[0], tuple(row[1:]))

    def _append_state(self, game_id: int) -> _AppendState:
        row = self.db.execute("SELECT id,payload,family,split,trajectory FROM games WHERE id=?", (game_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown game.")
        record = tuple(row)
        if self._append_cache is not None and self._append_cache.record == record:
            return self._append_cache
        # Decode the exact observed bytes, including changes made by direct SQL.
        data = self.db.execute("SELECT json(?)", (row[1],)).fetchone()[0]
        payload = self._validate_game(data, record[2:])
        return _AppendState(
            record,
            tuple(payload.snapshot.moves),
            _ActorWork(actor_queries=payload.actor_queries, actor_nodes=payload.actor_nodes, actor_ms=payload.actor_ms),
            payload.model_dump_json(),
        )

    def append(self, game_id: int, snapshot: Snapshot, *, actor_nodes=0, actor_ms=0.0, actor_queries=0):
        if (
            type(snapshot.schema_version) is not int
            or snapshot.schema_version != 1
            or snapshot.ruleset != RULESET
            or snapshot.initial_fen != START_FEN
        ):
            raise ValueError("Unsupported replay identity.")
        previous = self._append_state(game_id)
        before, after = previous.moves, tuple(snapshot.moves)
        if after[: len(before)] != before or len(after) > len(before) + 1 or len(after) < len(before):
            raise ValueError("Prefix mutation or nonincremental append rejected.")
        self.inspect(snapshot)
        work = _ActorWork(
            actor_nodes=previous.work.actor_nodes + actor_nodes,
            actor_ms=previous.work.actor_ms + actor_ms,
            actor_queries=previous.work.actor_queries + actor_queries,
        )
        trajectory = state_fingerprint(snapshot)
        # Normalize defaults on a validation miss; the warm path serializes only counters.
        payload = "jsonb(?)" if previous.normalized is not None else "payload"
        parameters = [previous.normalized] if previous.normalized is not None else []
        if len(after) > len(before):
            payload = f"jsonb_insert({payload},'$.snapshot.moves[#]',?)"
            parameters.append(after[-1])
        with self.db:
            rows = self.db.execute(
                f"UPDATE games SET payload=jsonb_patch({payload},jsonb(?)),trajectory=?,updated=? "
                "WHERE id=? AND payload=? AND family=? AND split=? AND trajectory=? AND status='running' "
                "RETURNING payload",
                [*parameters, work.model_dump_json(), trajectory, time(), *previous.record],
            ).fetchall()
            if len(rows) != 1:
                raise ValueError("Only an unchanged running game may append.")
        # A failed UPDATE or COMMIT must never advance the cached persisted state.
        self._append_cache = _AppendState(
            (game_id, rows[0][0], previous.record[2], previous.record[3], trajectory), after, work
        )

    def finish_game(self, game_id: int, reason: str, failure: str | None = None):
        payload = self.game(game_id)
        game = self.inspect(payload.snapshot)
        if reason not in {"terminal", "ply-budget", "error", "deadline", "interrupted", "rejected-trajectory"}:
            raise ValueError("Unknown stop reason.")
        if reason in {"terminal", "ply-budget"}:
            if (reason == "terminal") != bool(game.outcome):
                raise ValueError("Only referee outcomes are terminal.")
            if (
                reason == "ply-budget"
                and payload.plan
                and len(game.moves) - len(payload.initial.moves) != payload.plan.additional_plies
            ):
                raise ValueError("Ply budget not exhausted.")
        if (
            reason == "rejected-trajectory"
            and not self.db.execute(
                "SELECT 1 FROM games WHERE trajectory=? AND split!=? AND status='complete'",
                (state_fingerprint(payload.snapshot), payload.split),
            ).fetchone()
        ):
            raise ValueError("Trajectory rejection requires a completed opposite-split duplicate.")
        status = (
            "complete"
            if reason in {"terminal", "ply-budget"}
            else "interrupted"
            if reason == "interrupted"
            else "failed"
        )
        if (
            status == "complete"
            and self.db.execute(
                "SELECT 1 FROM games WHERE trajectory=? AND split!=? AND status='complete'",
                (state_fingerprint(payload.snapshot), payload.split),
            ).fetchone()
        ):
            raise TrajectorySplitConflict("Exact trajectory crosses splits.")
        with self.db:
            result = self.db.execute(
                "UPDATE games SET status=?,stop_reason=?,outcome=?,failure=?,updated=? WHERE id=? AND status='running'",
                (
                    status,
                    reason,
                    json.dumps(asdict(game.outcome)) if game.outcome else None,
                    failure,
                    time(),
                    game_id,
                ),
            )
            if result.rowcount != 1:
                raise ValueError("Game already finalized.")

    def occurrence(self, game_id: int, snapshot: Snapshot, *, phase=None, metadata=None) -> int:
        payload = self.game(game_id)
        ply = len(snapshot.moves)
        if (
            not len(payload.initial.moves) <= ply <= len(payload.snapshot.moves)
            or payload.snapshot.moves[:ply] != snapshot.moves
        ):
            raise ValueError("Occurrence must be an exact persisted prefix.")
        game = self.inspect(snapshot)
        attempt = self.db.execute("SELECT attempt FROM games WHERE id=?", (game_id,)).fetchone()[0]
        identity = fingerprint(
            "occurrence-v1", {"game_attempt": attempt, "ply": ply, "state": state_fingerprint(snapshot)}
        )
        method = PHASE_POLICY
        if phase is not None and payload.plan and snapshot == payload.plan.start.snapshot:
            method = (
                "curated:" + payload.plan.start.phase_authority if payload.plan.start.phase_authority else PHASE_POLICY
            )
        annotation = OccurrencePayload(phase_method=method, metadata=metadata or {})
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO position_occurrences(game_id,identity,ply_count,board,turn,"
                "board_hash,state_hash,"
                "observation_hash,input_hash,phase,payload) VALUES (?,?,?,?,?,?,?,?,?,?,jsonb(?))",
                (
                    game_id,
                    identity,
                    ply,
                    game.board,
                    game.turn,
                    fingerprint("board-turn-v1", {"ruleset": snapshot.ruleset, "board": game.board, "turn": game.turn}),
                    state_fingerprint(snapshot),
                    observation_fingerprint(game),
                    input_key(game),
                    phase or classify_phase(game),
                    annotation.model_dump_json(),
                ),
            )
        row = self.db.execute(
            "SELECT id,state_hash FROM position_occurrences WHERE game_id=? AND ply_count=?", (game_id, ply)
        ).fetchone()
        if row[1] != state_fingerprint(snapshot):
            raise ValueError("Immutable prefix identity mismatch.")
        return row[0]

    def snapshot(self, occurrence: int) -> Snapshot:
        row = self.db.execute(
            "SELECT game_id,ply_count,state_hash FROM position_occurrences WHERE id=?", (occurrence,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown occurrence.")
        payload = self.game(row[0])
        snapshot = payload.snapshot.model_copy(update={"moves": payload.snapshot.moves[: row[1]]})
        if state_fingerprint(snapshot) != row[2]:
            raise ValueError("Persisted replay prefix differs from occurrence identity.")
        return snapshot

    def spec(self, spec: AnalysisSpec, locators: dict[str, str] | None = None) -> int:
        spec = AnalysisSpec.model_validate(spec.model_dump())
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO analysis_specs(identity,payload,locators) VALUES (?,jsonb(?),jsonb(?))",
                (spec.identity, spec.model_dump_json(), json.dumps(locators or {})),
            )
        return self.db.execute("SELECT id FROM analysis_specs WHERE identity=?", (spec.identity,)).fetchone()[0]

    def first_success(self, occurrence: int, spec: int):
        return self.db.execute(
            "SELECT id FROM analyses WHERE occurrence_id=? AND spec_id=? AND status='success' "
            "ORDER BY success_order LIMIT 1",
            (occurrence, spec),
        ).fetchone()

    def begin_analysis(self, occurrence: int, spec: int) -> int:
        snapshot = self.snapshot(occurrence)
        spec_hash = self.db.execute("SELECT identity FROM analysis_specs WHERE id=?", (spec,)).fetchone()[0]
        request = fingerprint("analysis-request-v1", {"state": state_fingerprint(snapshot), "spec": spec_hash})
        with self.db:
            return self.db.execute(
                "INSERT INTO analyses(occurrence_id,spec_id,attempt,request,status,created,payload) "
                "VALUES (?,?,?,?,'running',?,jsonb(?))",
                (occurrence, spec, uuid4().hex, request, time(), AnalysisPayload().model_dump_json()),
            ).lastrowid

    def finish_analysis(
        self,
        attempt: int,
        answer: TeacherAnalysis | None = None,
        *,
        failure: str | None = None,
        raw: list[str] | None = None,
    ):
        row = self.db.execute("SELECT occurrence_id,spec_id FROM analyses WHERE id=?", (attempt,)).fetchone()
        if row is None or (answer is None) == (failure is None):
            raise ValueError("Supply exactly one successful answer or failure.")
        if answer is not None:
            answer = TeacherAnalysis.model_validate_json(answer.model_dump_json())
            if answer.elapsed_ms < 0 or any(
                value is not None and value < 0
                for value in (answer.reported_nodes, answer.reported_depth, answer.invalid_actions, answer.retries)
            ):
                raise ValueError("Analysis work counters must be nonnegative.")
            self.validate_example(answer)
            spec = AnalysisSpec.model_validate_json(
                self.db.execute("SELECT json(payload) FROM analysis_specs WHERE id=?", (row[1],)).fetchone()[0]
            )
            if answer.snapshot != self.snapshot(row[0]) or AnalysisSpec.from_analysis(answer) != spec:
                raise ValueError("Answer differs from requested exact state/specification.")
        payload = AnalysisPayload(
            answer=answer,
            failure=failure,
            raw=answer.search_info if answer else raw or [],
            candidates=parse_candidates(answer, execution=self._execution) if answer else [],
        )
        with self.db:
            order = (
                self.db.execute("SELECT coalesce(max(success_order),0)+1 FROM analyses").fetchone()[0]
                if answer
                else None
            )
            result = self.db.execute(
                (
                    "UPDATE analyses SET status=?,finished=?,success_order=?,move=?,pa"
                    "yload=jsonb(?) WHERE id=? AND status='running'"
                ),
                (
                    "success" if answer else "failed",
                    time(),
                    order,
                    answer.move if answer else None,
                    payload.model_dump_json(),
                    attempt,
                ),
            )
            if result.rowcount != 1:
                raise ValueError("Analysis already finalized.")

    def positions(self, *, after=0, limit=100, board_hash=None) -> list[dict]:
        if not 1 <= limit <= 1000 or after < 0:
            raise ValueError("Use a nonnegative cursor and limit 1-1000.")
        query = (
            "SELECT id,identity,game_id,ply_count,board,turn,board_hash,state_hash,phase "
            "FROM position_occurrences WHERE id>?"
        )
        parameters = [after]
        if board_hash is not None:
            query += " AND board_hash=?"
            parameters.append(board_hash)
        return [dict(row) for row in self.db.execute(query + " ORDER BY id LIMIT ?", [*parameters, limit])]

    def counts(self) -> dict:
        return {
            table: self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("generation_runs", "games", "position_occurrences", "analysis_specs", "analyses")
        } | {
            "distinct_boards": self.db.execute(
                "SELECT count(DISTINCT board_hash) FROM position_occurrences"
            ).fetchone()[0],
            "distinct_trajectories": self.db.execute(
                "SELECT count(DISTINCT trajectory) FROM games WHERE status='complete'"
            ).fetchone()[0],
        }
