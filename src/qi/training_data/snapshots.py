"""Recipe-governed SQL selection and immutable typed Parquet with replay evidence."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from qi.artifacts import write_json
from qi.evaluation import Corpus
from qi.players.policy.encoding import input_key
from qi.protocol import Snapshot
from qi.teacher import digest
from qi.training_data.assembly import Bucket
from qi.training_data.contracts import (
    Contract,
    Example,
    fingerprint,
    observation_fingerprint,
    satisfies_objective,
    state_fingerprint,
)
from qi.training_data.store import DDL, AnalysisPayload, AnalysisSpec, Collection, board_identity
from qi.training_data.v1 import reserved_inputs


class SnapshotBucket(Bucket):
    count: int = Field(ge=1, le=10_000_000)


class SelectionRecipe(Contract):
    version: Literal["sql-selection-v1"] = "sql-selection-v1"
    analysis_spec: str = Field(pattern=r"^[0-9a-f]{64}$")
    reserved_corpus: Corpus
    seed: int = 7
    buckets: list[SnapshotBucket] = Field(min_length=2)
    attempt_policy: Literal["first-committed-success"] = "first-committed-success"
    # Portable occurrence identity -> explicit attempt identity, never local row IDs.
    overrides: dict[str, str] = Field(default_factory=dict)
    completed_games_only: Literal[True] = True
    selected_only: bool = False
    target: Literal["legal-teacher-move-v1"] = "legal-teacher-move-v1"
    overlap_policy: Literal["first-bucket-wins"] = "first-bucket-wins"

    @model_validator(mode="after")
    def quotas(self):
        if len({b.id for b in self.buckets}) != len(self.buckets) or {b.split for b in self.buckets} != {
            "train",
            "validation",
        }:
            raise ValueError("Distinct buckets must declare training and validation quotas.")
        return self


def arrow():
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ValueError("Parquet snapshots require the data extra: uv sync --extra data") from exc
    return pa, pq


def row_schema():
    pa, _ = arrow()
    return pa.schema(
        [
            (name, pa.string())
            for name in (
                "occurrence",
                "analysis",
                "analysis_spec",
                "state",
                "board_hash",
                "observation",
                "input_hash",
                "board",
                "turn",
                "move",
                "split",
                "bucket",
                "phase",
                "phase_method",
            )
        ]
        + [("ply_count", pa.int32()), ("ordinal", pa.int64())]
    )


def select_sql(db, recipe: SelectionRecipe) -> tuple[str, dict]:
    """Materialize only temporary relational indexes; do not collect the dataset in Python."""
    recipe = SelectionRecipe.model_validate(recipe.model_dump())
    db.create_function(
        "selection_rank",
        3,
        lambda seed, bucket, key: fingerprint("sql-order-v1", [seed, bucket, key]),
        deterministic=True,
    )

    def objective_matches(payload, ply, move):
        source = json.loads(payload)
        if source["objective"] is None:
            return True
        snap = Snapshot.model_validate(source["snapshot"])
        snap.moves = snap.moves[:ply]
        return satisfies_objective(snap.game(), move, source["objective"])

    db.create_function("objective_matches", 3, objective_matches, deterministic=True)
    db.executescript("""
        DROP TABLE IF EXISTS temp.excluded;
        DROP TABLE IF EXISTS temp.overrides;
        DROP TABLE IF EXISTS temp.candidates;
        DROP TABLE IF EXISTS temp.selected;
        CREATE TEMP TABLE excluded(input_hash TEXT PRIMARY KEY);
        CREATE TEMP TABLE overrides(occurrence TEXT PRIMARY KEY,attempt TEXT NOT NULL);
    """)
    # Begin after temporary DDL (executescript commits); everything below reads one DB state.
    db.execute("BEGIN")
    db.executemany(
        "INSERT INTO excluded VALUES (?)", ((key,) for key in sorted(reserved_inputs(recipe.reserved_corpus)))
    )
    db.executemany("INSERT INTO overrides VALUES (?,?)", recipe.overrides.items())
    if not db.execute("SELECT 1 FROM analysis_specs WHERE identity=?", (recipe.analysis_spec,)).fetchone():
        raise ValueError("Unknown analysis specification.")
    if db.execute(
        """SELECT 1 FROM overrides x LEFT JOIN position_occurrences o ON o.identity=x.occurrence
        LEFT JOIN analyses a ON a.attempt=x.attempt AND a.occurrence_id=o.id AND a.status='success'
        LEFT JOIN analysis_specs s ON s.id=a.spec_id AND s.identity=? WHERE s.id IS NULL LIMIT 1""",
        (recipe.analysis_spec,),
    ).fetchone():
        raise ValueError("Override must pin a successful attempt of the selected occurrence/specification.")
    for key in ("family", "trajectory"):
        if db.execute(
            f"SELECT 1 FROM games WHERE status='complete' GROUP BY {key} HAVING count(DISTINCT split)>1 LIMIT 1"
        ).fetchone():
            raise ValueError(f"Cross-split {key} leakage.")
    if db.execute("""SELECT 1 FROM position_occurrences o JOIN games g ON g.id=o.game_id
        WHERE g.status='complete' AND NOT EXISTS(SELECT 1 FROM excluded e WHERE e.input_hash=o.input_hash)
        GROUP BY o.input_hash HAVING count(DISTINCT g.split)>1 LIMIT 1""").fetchone():
        raise ValueError("Cross-split observation lineage leakage.")
    candidate_sql = """SELECT o.*, a.id AS analysis_id, a.attempt AS analysis_attempt, a.move, g.split,
        g.payload AS game_payload
        FROM position_occurrences o JOIN games g ON g.id=o.game_id
        JOIN analysis_specs s ON s.identity=:spec
        JOIN analyses a ON a.occurrence_id=o.id AND a.spec_id=s.id AND a.status='success'
        LEFT JOIN overrides x ON x.occurrence=o.identity
        WHERE g.status='complete' AND NOT EXISTS(SELECT 1 FROM excluded e WHERE e.input_hash=o.input_hash)
        AND (:selected_only=0 OR json_extract(o.payload,'$.metadata.selected')=1)
        AND objective_matches(json(g.payload),o.ply_count,a.move)
        AND ((x.attempt IS NOT NULL AND a.attempt=x.attempt) OR (x.attempt IS NULL AND a.id=(
            SELECT a2.id FROM analyses a2 WHERE a2.occurrence_id=o.id AND a2.spec_id=s.id AND a2.status='success'
            ORDER BY a2.success_order LIMIT 1)))"""
    db.execute(
        "CREATE TEMP TABLE candidates AS " + candidate_sql,
        {"spec": recipe.analysis_spec, "selected_only": int(recipe.selected_only)},
    )
    db.execute("CREATE INDEX temp.candidate_inputs ON candidates(input_hash)")
    if db.execute("SELECT 1 FROM candidates GROUP BY input_hash HAVING count(DISTINCT move)>1 LIMIT 1").fetchone():
        raise ValueError("Ambiguous supervision for the same model observation.")
    branches, parameters = [], {"seed": recipe.seed}
    for i, bucket in enumerate(recipe.buckets):
        parameters.update(
            {
                f"split{i}": bucket.split,
                f"modes{i}": json.dumps(bucket.modes),
                f"phases{i}": json.dumps(bucket.phases),
                f"themes{i}": json.dumps(bucket.themes),
                f"objective{i}": bucket.objective,
                f"bucket{i}": bucket.id,
                f"quota{i}": bucket.count,
            }
        )
        branches.append(f"""SELECT c.*, {i} AS priority, :bucket{i} AS bucket, :quota{i} AS quota FROM candidates c
            WHERE split=:split{i} AND json_extract(game_payload,'$.mode') IN (SELECT value FROM json_each(:modes{i}))
            AND phase IN (SELECT value FROM json_each(:phases{i}))
            AND NOT EXISTS(SELECT 1 FROM json_each(:themes{i}) t WHERE t.value NOT IN (
                SELECT value FROM json_each(json_extract(game_payload,'$.themes'))))
            AND (:objective{i} IS NULL OR json_extract(game_payload,'$.objective')=:objective{i})""")
    sql = (
        """WITH eligible AS ("""
        + " UNION ALL ".join(branches)
        + """),
        owned AS (SELECT *,row_number() OVER (PARTITION BY input_hash ORDER BY priority,state_hash,identity) AS owner
        FROM eligible),
        ranked AS (SELECT *,row_number() OVER (PARTITION BY bucket
        ORDER BY selection_rank(:seed,bucket,input_hash),input_hash) AS rank
        FROM owned WHERE owner=1)
        SELECT * FROM ranked WHERE rank<=quota ORDER BY priority,rank,input_hash"""
    )
    db.execute("CREATE TEMP TABLE selected AS " + sql, parameters)
    return candidate_sql + ";\n" + sql, {
        "spec": recipe.analysis_spec,
        "selected_only": int(recipe.selected_only),
        **parameters,
    }


def copy_evidence(source, destination: Path):
    """Frozen five-table evidence subset, including all lineage for selected inputs."""
    target = sqlite3.connect(destination)
    try:
        target.executescript(DDL)
        occurrences = "SELECT id FROM position_occurrences WHERE input_hash IN (SELECT input_hash FROM selected)"
        games = "SELECT game_id FROM position_occurrences WHERE input_hash IN (SELECT input_hash FROM selected)"
        analyses = f"SELECT * FROM analyses WHERE occurrence_id IN ({occurrences})"
        queries = {
            "generation_runs": (
                f"SELECT * FROM generation_runs WHERE id IN (SELECT run_id FROM games WHERE id IN ({games}))"
            ),
            "games": f"SELECT * FROM games WHERE id IN ({games})",
            "position_occurrences": f"SELECT * FROM position_occurrences WHERE id IN ({occurrences})",
            "analysis_specs": (
                "SELECT * FROM analysis_specs WHERE id IN "
                f"(SELECT spec_id FROM analyses WHERE occurrence_id IN ({occurrences}))"
            ),
            "analyses": analyses,
        }
        for table, query in queries.items():
            cursor = source.execute(query + " ORDER BY id")
            count = len(cursor.description)
            target.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in range(count))})", cursor)
        target.commit()
        if target.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Evidence bundle has broken references.")
    finally:
        target.close()


def export_snapshot(store: Collection, recipe: SelectionRecipe, destination: Path, *, shard_rows=4096) -> dict:
    pa, pq = arrow()
    if not 1 <= shard_rows <= 65536:
        raise ValueError("Shard rows must be between 1 and 65536.")
    destination = Path(destination)
    pending = destination.with_name(destination.name + ".pending")
    if destination.exists() or pending.exists():
        raise ValueError("Choose a fresh snapshot destination; pending evidence is retained.")
    pending.mkdir(parents=True)
    manifest = {
        "version": "parquet-training-v1",
        "status": "incomplete",
        "recipe": recipe.model_dump(),
        "files": {},
        "rows": 0,
    }
    try:
        sql, parameters = select_sql(store.db, recipe)
        actual = {
            b.id: store.db.execute("SELECT count(*) FROM selected WHERE bucket=?", (b.id,)).fetchone()[0]
            for b in recipe.buckets
        }
        manifest.update(
            sql=sql, parameters=parameters, actual=actual, requested={b.id: b.count for b in recipe.buckets}
        )
        if any(actual[b.id] != b.count for b in recipe.buckets):
            raise ValueError("Snapshot quotas unavailable; requested/actual counts retained.")
        copy_evidence(store.db, pending / "evidence.sqlite")
        manifest["files"]["evidence.sqlite"] = digest(pending / "evidence.sqlite")
        cursor = store.db.execute(
            (
                "SELECT *,json_extract(payload,'$.phase_method') AS phase_method "
                "FROM selected ORDER BY priority,rank,input_hash"
            )
        )
        shards = []
        ordinal = 0
        while records := cursor.fetchmany(shard_rows):
            rows = []
            for r in records:
                rows.append(
                    dict(
                        occurrence=r["identity"],
                        analysis=r["analysis_attempt"],
                        analysis_spec=recipe.analysis_spec,
                        state=r["state_hash"],
                        board_hash=r["board_hash"],
                        observation=r["observation_hash"],
                        input_hash=r["input_hash"],
                        board=r["board"],
                        turn=r["turn"],
                        move=r["move"],
                        split=r["split"],
                        bucket=r["bucket"],
                        phase=r["phase"],
                        phase_method=r["phase_method"],
                        ply_count=r["ply_count"],
                        ordinal=ordinal,
                    )
                )
                ordinal += 1
            name = f"rows-{len(shards):05d}.parquet"
            pq.write_table(
                pa.Table.from_pylist(rows, schema=row_schema()),
                pending / name,
                compression="zstd",
                row_group_size=shard_rows,
            )
            shards.append(name)
            manifest["files"][name] = digest(pending / name)
        manifest.update(status="complete", rows=ordinal, shards=shards)
        manifest["fingerprint"] = fingerprint("parquet-manifest-v1", manifest)
        write_json(pending / "manifest.json", manifest, indent=2)
        verify_snapshot(pending)
        for path in pending.iterdir():
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
        pending.rename(destination)
        return manifest
    except BaseException as exc:
        manifest.update(status="incomplete", failure=str(exc))
        write_json(pending / "manifest.json", manifest, indent=2)
        raise
    finally:
        store.db.rollback()


class SnapshotReader:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.manifest = json.loads((self.path / "manifest.json").read_text())
        data = dict(self.manifest)
        identity = data.pop("fingerprint", None)
        if (
            data.get("version") != "parquet-training-v1"
            or data.get("status") != "complete"
            or identity != fingerprint("parquet-manifest-v1", data)
        ):
            raise ValueError("Incomplete or invalid snapshot manifest.")
        self.recipe = SelectionRecipe.model_validate(data["recipe"])
        expected_files = {"evidence.sqlite", *data["shards"]}
        if set(data["files"]) != expected_files or len(set(data["shards"])) != len(data["shards"]):
            raise ValueError("Invalid snapshot file inventory.")
        for name, expected in data["files"].items():
            if Path(name).name != name or (self.path / name).is_symlink() or digest(self.path / name) != expected:
                raise ValueError("Snapshot file hash or path mismatch.")

    def batches(self, batch_size=256, *, columns=None):
        if not 1 <= batch_size <= 65536:
            raise ValueError("Batch size must be between 1 and 65536.")
        _, pq = arrow()
        for name in self.manifest["shards"]:
            file = pq.ParquetFile(self.path / name)
            if file.schema_arrow != row_schema():
                raise ValueError("Unexpected training row schema.")
            yield from file.iter_batches(batch_size=batch_size, columns=columns, use_threads=False)

    def label_batches(self, batch_size=256):
        from qi.training_data.v1 import Label

        with Collection(self.path / "evidence.sqlite", readonly=True) as evidence:
            for batch in self.batches(batch_size):
                labels = []
                for row in batch.to_pylist():
                    record = evidence.db.execute(
                        "SELECT json(a.payload),g.logical_key FROM analyses a JOIN position_occurrences o "
                        "ON o.id=a.occurrence_id JOIN games g ON g.id=o.game_id WHERE a.attempt=?",
                        (row["analysis"],),
                    ).fetchone()
                    if record is None:
                        raise ValueError("Missing snapshot label evidence.")
                    answer = AnalysisPayload.model_validate_json(record[0]).answer
                    labels.append(Label(source_id=record[1], input_sha256=row["input_hash"], analysis=answer))
                yield labels


def verify_snapshot(path: Path) -> dict:
    reader = SnapshotReader(path)
    actual = {b.id: 0 for b in reader.recipe.buckets}
    total = 0
    with Collection(Path(path) / "evidence.sqlite", readonly=True) as evidence:
        if (
            evidence.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or evidence.db.execute("PRAGMA foreign_key_check").fetchone()
        ):
            raise ValueError("Corrupt evidence database.")
        for key in ("family", "trajectory"):
            if evidence.db.execute(
                f"SELECT 1 FROM games WHERE status='complete' GROUP BY {key} HAVING count(DISTINCT split)>1 LIMIT 1"
            ).fetchone():
                raise ValueError("Evidence source lineage crosses splits.")
        if evidence.db.execute(
            "SELECT 1 FROM position_occurrences o JOIN games g ON g.id=o.game_id "
            "WHERE g.status='complete' GROUP BY o.input_hash HAVING count(DISTINCT g.split)>1 LIMIT 1"
        ).fetchone():
            raise ValueError("Evidence observation lineage crosses splits.")
        # A compact bundle omits unselected observations, so unrelated overrides
        # cannot be resolved here. All retained lineage is checked by the compiler.
        overrides = {
            identity: attempt
            for identity, attempt in reader.recipe.overrides.items()
            if evidence.db.execute("SELECT 1 FROM position_occurrences WHERE identity=?", (identity,)).fetchone()
        }
        select_sql(evidence.db, reader.recipe.model_copy(update={"overrides": overrides}))
        expected = evidence.db.execute(
            "SELECT identity,analysis_attempt,input_hash,bucket FROM selected ORDER BY priority,rank,input_hash"
        )
        if reader.manifest["requested"] != {b.id: b.count for b in reader.recipe.buckets}:
            raise ValueError("Snapshot requested counts differ from recipe.")
        reserved = reserved_inputs(reader.recipe.reserved_corpus)
        for batch in reader.batches():
            for row in batch.to_pylist():
                selected = expected.fetchone()
                if selected is None or tuple(selected) != (
                    row["occurrence"],
                    row["analysis"],
                    row["input_hash"],
                    row["bucket"],
                ):
                    raise ValueError("Snapshot row violates selection recipe or ordering.")
                record = evidence.db.execute(
                    """SELECT a.*,json(a.payload) AS answer_json,o.id AS occurrence_id,
                    o.identity AS occurrence_identity,s.identity AS spec_identity,
                    json(s.payload) AS spec_json,g.status AS game_status,
                    g.split FROM analyses a JOIN position_occurrences o ON o.id=a.occurrence_id
                    JOIN analysis_specs s ON s.id=a.spec_id JOIN games g ON g.id=o.game_id WHERE a.attempt=?""",
                    (row["analysis"],),
                ).fetchone()
                if record is None or record["status"] != "success" or record["game_status"] != "complete":
                    raise ValueError("Snapshot requires successful analyses of completed games.")
                override = reader.recipe.overrides.get(row["occurrence"])
                if override is not None:
                    if override != row["analysis"]:
                        raise ValueError("Snapshot ignores explicit attempt override.")
                elif evidence.first_success(record["occurrence_id"], record["spec_id"])[0] != record["id"]:
                    raise ValueError("Snapshot does not use first committed success.")
                annotation = evidence.db.execute(
                    "SELECT phase,json_extract(payload,'$.phase_method') FROM position_occurrences WHERE id=?",
                    (record["occurrence_id"],),
                ).fetchone()
                if tuple(annotation) != (row["phase"], row["phase_method"]):
                    raise ValueError("Snapshot annotation differs from frozen evidence.")
                answer = AnalysisPayload.model_validate_json(record["answer_json"]).answer
                Example(analysis=answer, source_ids=["verify"])
                snap = evidence.snapshot(record["occurrence_id"])
                game = snap.game()
                spec = AnalysisSpec.model_validate_json(record["spec_json"])
                if (
                    answer.snapshot != snap
                    or AnalysisSpec.from_analysis(answer) != spec
                    or spec.identity != row["analysis_spec"]
                    or row["analysis_spec"] != reader.recipe.analysis_spec
                    or record["occurrence_identity"] != row["occurrence"]
                    or row["state"] != state_fingerprint(snap)
                    or row["board_hash"] != board_identity(snap)
                    or row["observation"] != observation_fingerprint(game)
                    or row["input_hash"] != input_key(game)
                    or row["board"] != game.board
                    or row["turn"] != game.turn
                    or row["move"] != answer.move
                    or row["ply_count"] != len(snap.moves)
                    or row["split"] != record["split"]
                    or row["ordinal"] != total
                    or row["input_hash"] in reserved
                ):
                    raise ValueError("Snapshot row differs from replay/analysis evidence.")
                if (
                    row["bucket"] not in actual
                    or next(b.split for b in reader.recipe.buckets if b.id == row["bucket"]) != row["split"]
                ):
                    raise ValueError("Snapshot bucket mismatch.")
                actual[row["bucket"]] += 1
                total += 1
        if (
            expected.fetchone() is not None
            or actual != reader.manifest["actual"]
            or any(actual[b.id] != b.count for b in reader.recipe.buckets)
            or total != reader.manifest["rows"]
        ):
            raise ValueError("Snapshot count mismatch.")
    return {"rows": total, "actual": actual, "fingerprint": reader.manifest["fingerprint"]}
