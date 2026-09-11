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

from qi.game import GameError
from qi.protocol import Position, Snapshot, inspect
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


def _stats(games: list[GeneratedGame]) -> CollectionStats:
    accepted = [g for g in games if g.disposition == "accepted"]
    rejected = sum(g.disposition == "rejected" for g in games)
    actual, requested = Counter(), Counter()
    for game in accepted:
        actual.update(game.actual)
        requested.update(game.requested)
    return CollectionStats(
        attempts=len(games),
        accepted=len(accepted),
        rejected=rejected,
        other=len(games) - len(accepted) - rejected,
        selected=sum(g.selected for g in accepted),
        sampling_games=sum(bool(g.requested) for g in accepted),
        shortfall_games=sum(g.shortfall > 0 for g in accepted),
        unique_trajectories=len({g.trajectory for g in accepted}),
        mean_plies=sum(g.plies - g.start_ply for g in accepted) / len(accepted) if accepted else None,
        policies=dict(Counter(g.policy for g in accepted)),
        splits=dict(Counter(g.split for g in accepted)),
        outcomes=dict(Counter(g.outcome if g.outcome != "draw" else f"draw · {g.outcome_reason}" for g in accepted)),
        lengths=dict(
            Counter(
                f"{min((g.plies - g.start_ply) // 50, 5) * 50}-{min((g.plies - g.start_ply) // 50, 5) * 50 + 49}"
                if g.plies - g.start_ply < 300
                else "300"
                for g in accepted
            )
        ),
        actual=dict(actual),
        requested=dict(requested),
    )


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
    with _read(path) as store:
        as_of = time()
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
         json_extract(payload,'$.config.continued_from_run') continued_from FROM generation_runs ORDER BY id DESC""")
        ]
        games = [_game(r) for r in store.db.execute(GAME_SQL)]
    wanted = set(attempts.split(",")) if attempts else None
    filtered = [
        g
        for g in games
        if (not run or g.run_id == run)
        and (not policy or g.policy == policy)
        and (not split or g.split == split)
        and (not disposition or g.disposition == disposition)
        and (not outcome or g.outcome == outcome or f"{g.outcome} · {g.outcome_reason}" == outcome)
        and (not q or q.lower() in f"{g.id} {g.source} {g.attempt}".lower())
        and (lens != "shortfall" or (g.disposition == "accepted" and g.shortfall > 0))
        and (
            not phase
            or (
                g.requested.get(phase, 0) > g.actual.get(phase, 0)
                if lens == "shortfall"
                else g.actual.get(phase, 0) > 0
            )
        )
        and (lens != "long" or g.plies - g.start_ply >= 250)
        and (wanted is None or g.attempt in wanted)
    ]
    filtered.sort(
        key=lambda g: (
            g.plies - g.start_ply if sort == "longest" else g.shortfall if sort == "shortfall" else g.id,
            g.id,
        ),
        reverse=True,
    )
    return CollectionPage(
        collection=_entry(path),
        as_of=as_of,
        runs=runs,
        overall=_stats(games),
        run_stats={str(r.id): _stats([g for g in games if g.run_id == r.id]) for r in runs},
        filtered=_stats(filtered),
        games=filtered[offset : offset + limit],
        total=len(filtered),
        offset=offset,
        limit=limit,
    )


def game_detail(identity: str, game_id: int) -> GeneratedGameDetail:
    with _read(collection_path(identity)) as store:
        payload = store.game(game_id)
        game = payload.snapshot.game()  # Python validates the entire saved trajectory.
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
                or answer.state_hash != snapshot.game().state_hash
                or answer.move != row["move"]
                or answer.move not in inspect(snapshot.game()).legal_moves
                or AnalysisSpec.from_analysis(answer).identity != row["identity"]
            ):
                raise ValueError("Analysis differs from its recorded position or specification.")
        return payload


def game_position(identity: str, game_id: int, ply: int) -> Position:
    with _read(collection_path(identity)) as store:
        snapshot = store.game(game_id).snapshot
        if ply > len(snapshot.moves):
            raise ValueError("Ply is beyond the recorded game.")
        return inspect(Snapshot(moves=snapshot.moves[:ply]).game())


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
