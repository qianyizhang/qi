"""Read-only projections of generated games; collection/referee remain authorities."""

import json
import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from time import monotonic, time

from pydantic import BaseModel
from qi_game.contracts import Position, Snapshot
from qi_game.core import GameError
from qi_game.reference import inspect, restore

from qi.teacher import TeacherScore
from qi.training_data.store import AnalysisPayload, AnalysisSpec, Collection


class CollectionEntry(BaseModel):
    id: str
    name: str
    location: str
    bytes: int
    updated: float


class CollectionCatalog(BaseModel):
    collections: list[CollectionEntry]
    issues: list[str]


class GeneratedRun(BaseModel):
    id: int
    identity: str
    name: str
    status: str
    planned: int
    continued_from: int | None
    created: float


class GeneratedGame(BaseModel):
    id: int
    run_id: int
    attempt: str
    trajectory: str
    source: str
    policy: str
    split: str
    status: str
    disposition: str
    stop_reason: str | None
    outcome: str
    outcome_reason: str | None
    plies: int
    start_ply: int
    selected: int
    actual: dict[str, int]
    requested: dict[str, int]
    shortfall: int
    updated: float


class CollectionStats(BaseModel):
    attempts: int
    accepted: int
    rejected: int
    other: int
    selected: int
    shortfall_games: int
    sampling_games: int
    unique_trajectories: int
    mean_plies: float | None
    policies: dict[str, int]
    splits: dict[str, int]
    outcomes: dict[str, int]
    lengths: dict[str, int]
    actual: dict[str, int]
    requested: dict[str, int]


class CollectionPage(BaseModel):
    collection: CollectionEntry
    as_of: float
    runs: list[GeneratedRun]
    overall: CollectionStats
    run_stats: dict[str, CollectionStats]
    filtered: CollectionStats
    games: list[GeneratedGame]
    total: int
    offset: int
    limit: int


class StoredAnalysis(BaseModel):
    id: int
    spec_id: str
    status: str
    resolved: bool
    move: str | None
    nodes: int
    depth_limit: int | None
    multipv: int
    threads: str
    engine: str
    network: str
    score: TeacherScore | None
    reported_depth: int | None
    reported_nodes: int | None
    failure: str | None


class StoredOccurrence(BaseModel):
    id: int
    identity: str
    ply: int
    phase: str
    selected: bool
    actor_move: str | None
    intervention: bool
    analyses: list[StoredAnalysis]


class GeneratedGameDetail(BaseModel):
    game: GeneratedGame
    snapshot: Snapshot
    initial_ply: int
    family: str
    failure: str | None
    occurrences: list[StoredOccurrence]
    duplicate_games: list[int]


def _paths() -> list[Path]:
    configured = os.environ.get("QI_COLLECTION_PATHS")
    if configured is not None:
        return [Path(p).expanduser().absolute() for p in configured.split(os.pathsep) if p]
    workspace = Path(os.environ.get("QI_WORKSPACE", Path(__file__).resolve().parents[2]))
    root = workspace / "artifacts/learning"
    result = []
    # Pilot spools and frozen execution sources can be enormous. Only discover
    # direct collections and collections up to two directory levels below learning.
    for directory, dirs, files in os.walk(root, followlinks=False):
        current = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (current / d).is_symlink() and d not in {"source", "executions"})
        if len(current.relative_to(root).parts) >= 2:
            dirs[:] = []
        result.extend(current / name for name in sorted(files) if name.endswith(".sqlite"))
    return result


def _entry(path: Path) -> CollectionEntry:
    stat = path.stat()
    return CollectionEntry(
        id=sha256(str(path).encode()).hexdigest()[:24],
        name=path.parent.name,
        location=str(path),
        bytes=stat.st_size,
        updated=stat.st_mtime,
    )


def discover_collections() -> CollectionCatalog:
    entries, issues = [], []
    for path in dict.fromkeys(_paths()):
        if path.is_symlink():
            continue
        try:
            with _read(path) as store:
                store.db.execute("SELECT id FROM generation_runs LIMIT 1").fetchone()
            entries.append(_entry(path))
        except (OSError, ValueError, sqlite3.Error) as exc:
            issues.append(f"{path.name} in {path.parent.name}: {exc}")
    return CollectionCatalog(collections=sorted(entries, key=lambda e: e.updated, reverse=True), issues=issues)


def collection_path(identity: str) -> Path:
    for path in _paths():
        if not path.is_symlink() and sha256(str(path).encode()).hexdigest()[:24] == identity and path.is_file():
            return path
    raise GameError("unknown_collection", "Collection not found in the configured local sources.")


@contextmanager
def _read(path: Path):
    try:
        with Collection(path, readonly=True) as store:
            deadline = monotonic() + 10
            store.db.execute("PRAGMA query_only=ON")
            store.db.set_progress_handler(lambda: int(monotonic() > deadline), 10000)
            store.db.execute("BEGIN")  # Every response observes one WAL snapshot.
            yield store
    except sqlite3.Error as exc:
        raise ValueError(f"Collection read unavailable: {exc}") from exc


GAME_SQL = """
SELECT id,run_id,attempt,trajectory,split,status,stop_reason,outcome,failure,updated,
 coalesce(json_extract(payload,'$.actor.source'), json_extract(payload,'$.source_id')) source,
 coalesce(json_extract(payload,'$.actor.policy.mode'),json_extract(payload,'$.mode')) policy,
 json_array_length(payload,'$.snapshot.moves') plies,
 json_array_length(payload,'$.initial.moves') start_ply,
 json_extract(payload,'$.actor.generation_result.sampling') sampling
FROM games
"""


def _game(row) -> GeneratedGame:
    sampling = json.loads(row["sampling"] or "{}")
    outcome = json.loads(row["outcome"] or "null")
    rejected = row["status"] == "failed" and (
        row["stop_reason"] == "rejected-trajectory"
        or (row["stop_reason"] == "error" and row["failure"] == "Exact trajectory crosses splits.")
    )
    return GeneratedGame(
        **{
            key: row[key]
            for key in (
                "id",
                "run_id",
                "attempt",
                "trajectory",
                "source",
                "policy",
                "split",
                "status",
                "stop_reason",
                "plies",
                "start_ply",
                "updated",
            )
        },
        disposition="accepted" if row["status"] == "complete" else "rejected" if rejected else row["status"],
        outcome=(outcome["winner"] or "draw") if outcome else "unfinished",
        outcome_reason=outcome["reason"] if outcome else None,
        selected=len(sampling.get("selected", [])),
        actual=sampling.get("actual", {}),
        requested=sampling.get("requested", {}),
        shortfall=sum(sampling.get("shortfall", {}).values()),
    )


# Shared projection keeps cohort predicates and aggregate denominators identical.
PAGE_SQL = f"""
WITH base AS ({GAME_SQL}), projected AS (
 SELECT *,
  CASE WHEN status='complete' THEN 'accepted'
       WHEN status='failed' AND (stop_reason='rejected-trajectory' OR
         (stop_reason='error' AND failure='Exact trajectory crosses splits.'))
       THEN 'rejected' ELSE status END disposition,
  CASE WHEN outcome IS NULL OR outcome='null' THEN 'unfinished'
       ELSE coalesce(json_extract(outcome,'$.winner'),'draw') END result,
  json_extract(outcome,'$.reason') reason,
  coalesce(json_array_length(sampling,'$.selected'),0) selected,
  coalesce(json_extract(sampling,'$.actual'),'{{}}') actual,
  coalesce(json_extract(sampling,'$.requested'),'{{}}') requested,
  coalesce((SELECT sum(value) FROM json_each(sampling,'$.shortfall')),0) shortfall,
  plies-start_ply length
 FROM base
), cohort AS (
 SELECT * FROM projected WHERE {{where}}
)
"""


def _cohort_predicate(*, run, policy, split, disposition, outcome, q, lens, phase, attempts):
    predicates, params = [], {}
    for column, value in (("run_id", run), ("policy", policy), ("split", split), ("disposition", disposition)):
        if value:
            predicates.append(f"{column}=:{column}")
            params[column] = value
    if outcome:
        predicates.append("(result=:outcome OR result || ' · ' || coalesce(reason,'None')=:outcome)")
        params["outcome"] = outcome
    if q:
        # SQLite lower() is ASCII-only; preserve the existing Unicode substring search.
        predicates.append("instr(text_lower(id || ' ' || source || ' ' || attempt),:q)>0")
        params["q"] = q.lower()
    if lens == "shortfall":
        predicates.append("disposition='accepted' AND shortfall>0")
    if lens == "long":
        predicates.append("length>=250")
    if phase:
        actual = "coalesce((SELECT value FROM json_each(actual) WHERE key=:phase),0)"
        predicates.append(
            f"coalesce((SELECT value FROM json_each(requested) WHERE key=:phase),0)>{actual}"
            if lens == "shortfall"
            else f"{actual}>0"
        )
        params["phase"] = phase
    if attempts:
        predicates.append("attempt IN (SELECT value FROM json_each(:attempts))")
        params["attempts"] = json.dumps(attempts.split(","))
    return " AND ".join(predicates) or "1", params


def _page_stats(db, cte: str, params: dict, runs: list[GeneratedRun]):
    scopes = """, scopes AS MATERIALIZED (
      SELECT 'overall' scope,* FROM projected
      UNION ALL SELECT 'run:' || run_id,* FROM projected
      UNION ALL SELECT 'filtered',* FROM cohort
    ) """
    counts = """
    SELECT scope,'counts' category,'' key,json_object(
      'attempts',count(*),
      'accepted',sum(disposition='accepted'),
      'rejected',sum(disposition='rejected'),
      'other',sum(disposition NOT IN ('accepted','rejected')),
      'selected',sum(CASE WHEN disposition='accepted' THEN selected ELSE 0 END),
      'sampling_games',sum(disposition='accepted' AND EXISTS(SELECT 1 FROM json_each(requested))),
      'shortfall_games',sum(disposition='accepted' AND shortfall>0),
      'unique_trajectories',count(DISTINCT CASE WHEN disposition='accepted' THEN trajectory END),
      'mean_plies',avg(CASE WHEN disposition='accepted' THEN length END)) value
    FROM scopes GROUP BY scope
    """
    histograms = {
        "policies": "policy",
        "splits": "split",
        "outcomes": "CASE WHEN result='draw' THEN result || ' · ' || reason ELSE result END",
        "lengths": "CASE WHEN length>=300 THEN '300' ELSE printf('%d-%d',(length/50)*50,(length/50)*50+49) END",
    }
    queries = [counts]
    for category, expression in histograms.items():
        queries.append(f"""SELECT scope,'{category}',{expression} key,count(*) FROM scopes
          WHERE disposition='accepted' GROUP BY scope,key""")
    for category in ("actual", "requested"):
        queries.append(f"""SELECT scope,'{category}',j.key,sum(j.value) FROM scopes,json_each({category}) j
          WHERE disposition='accepted' GROUP BY scope,j.key""")
    empty = dict(
        attempts=0,
        accepted=0,
        rejected=0,
        other=0,
        selected=0,
        sampling_games=0,
        shortfall_games=0,
        unique_trajectories=0,
        mean_plies=None,
    )
    values = {
        key: {**empty, **{name: {} for name in (*histograms, "actual", "requested")}}
        for key in ("overall", "filtered", *(f"run:{r.id}" for r in runs))
    }
    for row in db.execute(cte + scopes + " UNION ALL ".join(queries), params):
        if row["category"] == "counts":
            values[row["scope"]].update(json.loads(row["value"]))
        else:
            values[row["scope"]][row["category"]][row["key"]] = row["value"]
    return {key: CollectionStats(**value) for key, value in values.items()}


def collection_page(
    identity: str,
    *,
    run=0,
    policy="",
    split="",
    disposition="",
    outcome="",
    q="",
    lens="all",
    phase="",
    sort="newest",
    offset=0,
    limit=30,
    attempts: str = "",
) -> CollectionPage:
    path = collection_path(identity)
    where, params = _cohort_predicate(
        run=run,
        policy=policy,
        split=split,
        disposition=disposition,
        outcome=outcome,
        q=q,
        lens=lens,
        phase=phase,
        attempts=attempts,
    )
    cte = PAGE_SQL.replace("{where}", where)
    order = {"longest": "length", "shortfall": "shortfall"}.get(sort, "id")
    with _read(path) as store:
        as_of = time()
        store.db.create_function("text_lower", 1, str.lower, deterministic=True)
        runs = [
            GeneratedRun(
                id=r["id"],
                identity=r["identity"],
                name=r["name"] or f"Run {r['id']}",
                status=r["status"],
                planned=r["planned"],
                continued_from=r["continued_from"],
                created=r["created"],
            )
            for r in store.db.execute("""SELECT id,identity,status,created,
              json_extract(payload,'$.config.recipe.name') name, json_extract(payload,'$.planned_games') planned,
              json_extract(payload,'$.config.continued_from_run') continued_from
              FROM generation_runs ORDER BY id DESC""")
        ]
        stats = _page_stats(store.db, cte, params, runs)
        games = [
            _game(row)
            for row in store.db.execute(
                cte + f"SELECT * FROM cohort ORDER BY {order} DESC,id DESC LIMIT :limit OFFSET :offset",
                {**params, "limit": limit, "offset": offset},
            )
        ]
        return CollectionPage(
            collection=_entry(path),
            as_of=as_of,
            runs=runs,
            overall=stats["overall"],
            run_stats={str(r.id): stats[f"run:{r.id}"] for r in runs},
            filtered=stats["filtered"],
            games=games,
            total=stats["filtered"].attempts,
            offset=offset,
            limit=limit,
        )


def game_detail(identity: str, game_id: int) -> GeneratedGameDetail:
    with _read(collection_path(identity)) as store:
        payload = store.game(game_id)
        game = restore(payload.snapshot)  # Python validates the entire saved trajectory.
        row = store.db.execute(GAME_SQL + " WHERE id=?", (game_id,)).fetchone()
        indexed_outcome = json.loads(row["outcome"] or "null")
        if row["status"] == "complete" and (
            (game.outcome is None) != (indexed_outcome is None)
            or (game.outcome and {"winner": game.outcome.winner, "reason": game.outcome.reason} != indexed_outcome)
        ):
            raise ValueError("Indexed outcome differs from referee replay.")
        occurrences = []
        for occurrence in store.db.execute(
            """SELECT id,identity,ply_count,phase,
              json_extract(payload,'$.metadata.selected') selected,
              json_extract(payload,'$.metadata.actor_decision.intervention') intervention
              FROM position_occurrences WHERE game_id=? ORDER BY ply_count""",
            (game_id,),
        ):
            ply = occurrence["ply_count"]
            analyses, seen = [], set()
            for analysis in store.db.execute(
                """SELECT a.id,a.status,a.move,a.spec_id,a.success_order,
                  json_extract(a.payload,'$.answer.score') score,
                  json_extract(a.payload,'$.answer.reported_depth') reported_depth,
                  json_extract(a.payload,'$.answer.reported_nodes') reported_nodes,
                  json_extract(a.payload,'$.failure') failure,
                  s.identity,json(s.payload) spec
                  FROM analyses a JOIN analysis_specs s ON a.spec_id=s.id
                  WHERE a.occurrence_id=? ORDER BY a.success_order IS NULL,a.success_order,a.id""",
                (occurrence["id"],),
            ):
                spec = AnalysisSpec.model_validate_json(analysis["spec"])
                if spec.identity != analysis["identity"]:
                    raise ValueError("Analysis specification identity mismatch.")
                supervision = spec.supervision
                resolved = analysis["status"] == "success" and analysis["spec_id"] not in seen
                if resolved:
                    seen.add(analysis["spec_id"])
                analyses.append(
                    StoredAnalysis(
                        id=analysis["id"],
                        spec_id=spec.identity,
                        status=analysis["status"],
                        resolved=resolved,
                        move=analysis["move"],
                        nodes=supervision["nodes"],
                        depth_limit=supervision["depth"],
                        multipv=int(supervision["settings"].get("MultiPV", "1")),
                        threads=supervision["settings"].get("Threads", "unknown"),
                        engine=supervision["engine_sha256"],
                        network=supervision["network_sha256"],
                        score=json.loads(analysis["score"]) if analysis["score"] else None,
                        reported_depth=analysis["reported_depth"],
                        reported_nodes=analysis["reported_nodes"],
                        failure=analysis["failure"],
                    )
                )
            occurrences.append(
                StoredOccurrence(
                    id=occurrence["id"],
                    identity=occurrence["identity"],
                    ply=ply,
                    phase=occurrence["phase"],
                    selected=bool(occurrence["selected"]),
                    intervention=bool(occurrence["intervention"]),
                    actor_move=payload.snapshot.moves[ply] if ply < len(payload.snapshot.moves) else None,
                    analyses=analyses,
                )
            )
        duplicates = [
            r[0]
            for r in store.db.execute(
                "SELECT id FROM games WHERE trajectory=? AND id!=? AND status='complete' ORDER BY id LIMIT 20",
                (row["trajectory"], game_id),
            )
        ]
        return GeneratedGameDetail(
            game=_game(row),
            snapshot=payload.snapshot,
            initial_ply=len(payload.initial.moves),
            family=payload.family,
            failure=row["failure"],
            occurrences=occurrences,
            duplicate_games=duplicates,
        )


def analysis_evidence(identity: str, game_id: int, analysis_id: int) -> AnalysisPayload:
    with _read(collection_path(identity)) as store:
        row = store.db.execute(
            """SELECT json(a.payload) payload,a.move,a.status,a.occurrence_id,s.identity
          FROM analyses a JOIN position_occurrences o ON a.occurrence_id=o.id
          JOIN analysis_specs s ON a.spec_id=s.id WHERE a.id=? AND o.game_id=?""",
            (analysis_id, game_id),
        ).fetchone()
        if row is None:
            raise ValueError("Analysis not found in this game.")
        payload = AnalysisPayload.model_validate_json(row["payload"])
        if row["status"] == "success":
            snapshot = store.snapshot(row["occurrence_id"])
            answer = payload.answer
            if (
                answer is None
                or answer.snapshot != snapshot
                or answer.state_hash != restore(snapshot).state_hash
                or answer.move != row["move"]
                or answer.move not in inspect(restore(snapshot)).legal_moves
                or AnalysisSpec.from_analysis(answer).identity != row["identity"]
            ):
                raise ValueError("Analysis differs from its recorded position or specification.")
        return payload


def game_position(identity: str, game_id: int, ply: int) -> Position:
    with _read(collection_path(identity)) as store:
        snapshot = store.game(game_id).snapshot
        if ply > len(snapshot.moves):
            raise ValueError("Ply is beyond the recorded game.")
        return inspect(restore(Snapshot(moves=snapshot.moves[:ply])))


class OverlapExample(BaseModel):
    input_hash: str
    train_occurrences: int
    validation_occurrences: int
    train_game: int
    train_ply: int
    validation_game: int
    validation_ply: int


class SpecCoverage(BaseModel):
    identity: str
    nodes: int
    depth: int | None
    multipv: int
    threads: str
    engine: str
    network: str
    occurrences: int


class CollectionQuality(BaseModel):
    as_of: float
    selected_occurrences: int
    unique_inputs: int
    cross_split_inputs: int
    affected_train: int
    affected_validation: int
    phases: dict[str, int]
    single_pv_budget_coverage: dict[str, int]
    specs: list[SpecCoverage]
    overlap_examples: list[OverlapExample]


def collection_quality(identity: str) -> CollectionQuality:
    """Audit selected occurrences only, without scanning verbose analysis bodies."""
    with _read(collection_path(identity)) as store:
        as_of = time()
        grouped, phases = {}, Counter()
        selected = 0
        for row in store.db.execute("""SELECT o.input_hash,o.game_id,o.ply_count,o.phase,g.split
          FROM position_occurrences o JOIN games g ON g.id=o.game_id
          WHERE g.status='complete' AND json_extract(o.payload,'$.metadata.selected')=1 ORDER BY o.id"""):
            selected += 1
            phases[row["phase"]] += 1
            group = grouped.setdefault(row["input_hash"], {})
            entry = group.setdefault(row["split"], [0, row["game_id"], row["ply_count"]])
            entry[0] += 1
        overlaps = [(key, group) for key, group in grouped.items() if len(group) > 1]
        overlaps.sort(key=lambda pair: (-sum(v[0] for v in pair[1].values()), pair[0]))
        specs = []
        for row in store.db.execute("""SELECT s.identity,json(s.payload) payload,count(DISTINCT o.id) n
          FROM position_occurrences o JOIN games g ON g.id=o.game_id
          JOIN analyses a ON a.occurrence_id=o.id AND a.status='success'
          JOIN analysis_specs s ON s.id=a.spec_id
          WHERE g.status='complete' AND json_extract(o.payload,'$.metadata.selected')=1
          GROUP BY s.id ORDER BY s.id"""):
            spec = AnalysisSpec.model_validate_json(row["payload"])
            if spec.identity != row["identity"]:
                raise ValueError("Analysis specification identity mismatch.")
            sup = spec.supervision
            specs.append(
                SpecCoverage(
                    identity=spec.identity,
                    nodes=sup["nodes"],
                    depth=sup["depth"],
                    multipv=int(sup["settings"].get("MultiPV", "1")),
                    threads=sup["settings"].get("Threads", "unknown"),
                    engine=sup["engine_sha256"],
                    network=sup["network_sha256"],
                    occurrences=row["n"],
                )
            )
        budgets = Counter()
        for row in store.db.execute("""SELECT count(DISTINCT json_extract(s.payload,'$.supervision.nodes')) budgets
          FROM position_occurrences o JOIN games g ON g.id=o.game_id
          LEFT JOIN analyses a ON a.occurrence_id=o.id AND a.status='success'
          LEFT JOIN analysis_specs s ON s.id=a.spec_id
            AND coalesce(json_extract(s.payload,'$.supervision.settings.MultiPV'),'1')='1'
          WHERE g.status='complete' AND json_extract(o.payload,'$.metadata.selected')=1 GROUP BY o.id"""):
            budgets[str(min(row[0], 2))] += 1
        return CollectionQuality(
            as_of=as_of,
            selected_occurrences=selected,
            unique_inputs=len(grouped),
            cross_split_inputs=len(overlaps),
            affected_train=sum(group["train"][0] for _, group in overlaps),
            affected_validation=sum(group["validation"][0] for _, group in overlaps),
            phases=dict(phases),
            single_pv_budget_coverage=dict(budgets),
            specs=specs,
            overlap_examples=[
                OverlapExample(
                    input_hash=key,
                    train_occurrences=group["train"][0],
                    validation_occurrences=group["validation"][0],
                    train_game=group["train"][1],
                    train_ply=group["train"][2],
                    validation_game=group["validation"][1],
                    validation_ply=group["validation"][2],
                )
                for key, group in overlaps[:12]
            ],
        )
