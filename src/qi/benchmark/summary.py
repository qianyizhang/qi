"""Replay-validated matchups, costs and immutable local rating projections."""

from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import Field

from qi.artifacts import write_json
from qi.benchmark.models import Record
from qi.benchmark.ratings import Observation, RatingFit, fit_ratings
from qi.benchmark.store import evidence_digest, load_manifest, now, pool_state, read_attempts, writer_lock


class Cost(Record):
    decisions: int = 0
    elapsed_ms: float = 0
    mean_move_ms: float | None = None
    qi_visits: int = 0
    model_calls: int = 0
    engine_nodes: int = 0
    engine_decisions: int = 0
    engine_nodes_unknown: int = 0


class Matchup(Record):
    a: str
    b: str
    diagnostic: bool
    planned_pairs: int = 0
    completed_pairs: int = 0
    completed_games: int = 0
    failed_attempts: int = 0
    interrupted_attempts: int = 0
    reused_games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    score_rate: float | None = None
    termination_reasons: dict[str, int] = Field(default_factory=dict)


class BenchmarkSummary(Record):
    schema_version: Literal[1] = 1
    series_id: str
    series_sha256: str
    label: str
    spec_sha256: str
    evidence_sha256: str
    created_at: str
    status: Literal["complete", "incomplete", "failed"]
    pool_status: str
    results_hidden: bool
    planned_games: int
    completed_games: int
    failed_attempts: int
    interrupted_attempts: int
    running_games: int
    reused_games: int
    anchor: str
    entrants: dict[str, str]
    fit: RatingFit | None = None
    matchups: list[Matchup] = Field(default_factory=list)
    costs: dict[str, Cost] = Field(default_factory=dict)
    heldout_evidence: str
    notes: list[str] = Field(default_factory=list)


def summarize_benchmark(directory: Path, *, reveal: bool = False, persist: bool = False) -> BenchmarkSummary:
    manifest = load_manifest(directory)
    spec = manifest.spec
    attempts = read_attempts(directory, manifest)
    slots = spec.slots()
    counts = Counter(a.status for entries in attempts.values() for a in entries)
    complete = {id: next((a for a in entries if a.status == "complete"), None) for id, entries in attempts.items()}
    finished = sum(a is not None for a in complete.values())
    status = "complete" if finished == len(slots) else "failed" if counts["failed"] else "incomplete"
    if reveal and spec.series.book.use != "locked-test":
        raise ValueError("Only a locked-test benchmark has a reveal step.")
    if reveal and status != "complete":
        raise ValueError("A locked-test report can be revealed only after every planned game completes.")
    pool = pool_state(spec, action="reveal" if reveal else "read")
    hidden = pool == "reserved"
    sha = evidence_digest(manifest, attempts)
    snapshot = directory / "reports" / f"{sha}.json"
    summary = BenchmarkSummary(
        series_id=spec.series.id,
        series_sha256=spec.series.sha256,
        label=spec.series.label,
        spec_sha256=spec.sha256,
        evidence_sha256=sha,
        created_at=now(),
        status=status,
        pool_status=pool,
        results_hidden=hidden,
        planned_games=len(slots),
        completed_games=finished,
        failed_attempts=counts["failed"],
        interrupted_attempts=counts["interrupted"],
        running_games=counts["running"],
        reused_games=sum(a is not None and a.reused_from is not None for a in complete.values()),
        anchor=spec.series.anchor,
        entrants={id: p.label for id, p in spec.entrants.items()},
        heldout_evidence=spec.heldout_evidence,
        notes=[
            "Local ratings under this book, ruleset and configured players; resources are not equalized.",
            "Only complete color pairs score. Standard-start diagnostics are excluded from ratings.",
            "Intervals resample source families and retain both colors and all associated matchups.",
            "Approximate regularized estimates; inspect matchup outcomes and unavailable-interval reasons.",
        ],
    )
    if hidden:
        summary.notes = [
            "Locked-test results are hidden until completion and explicit reveal; reveal retires the pool."
        ]
        return summary
    costs = {id: Cost() for id in spec.entrants}
    groups: dict[tuple, list] = {}
    observations = []
    for slot in slots:
        groups.setdefault((slot.a, slot.b, slot.diagnostic), []).append(slot)
    for (a, b, diagnostic), entries in groups.items():
        row = Matchup(a=a, b=b, diagnostic=diagnostic, planned_pairs=len(entries) // 2)
        for slot in entries:
            history = attempts[slot.id]
            row.failed_attempts += sum(x.status == "failed" for x in history)
            row.interrupted_attempts += sum(x.status == "interrupted" for x in history)
            row.completed_games += complete[slot.id] is not None
            row.reused_games += complete[slot.id] is not None and complete[slot.id].reused_from is not None
        for first, second in zip(entries[::2], entries[1::2], strict=True):
            if complete[first.id] is None or complete[second.id] is None:
                continue
            row.completed_pairs += 1
            for slot in (first, second):
                match = complete[slot.id].match
                value = 0.5 if match.winner is None else 1.0 if match.winner == slot.a_side else 0.0
                row.wins += value == 1
                row.draws += value == 0.5
                row.losses += value == 0
                row.termination_reasons[match.reason] = row.termination_reasons.get(match.reason, 0) + 1
                if not diagnostic:
                    observations.append(Observation(a, b, slot.a_side == "red", value, slot.start.family))
                    for turn in match.turns:
                        cost = costs[a if turn.side == slot.a_side else b]
                        choice = turn.choice
                        cost.decisions += 1
                        cost.elapsed_ms += choice.elapsed_ms
                        cost.qi_visits += choice.nodes
                        cost.model_calls += choice.model_calls
                        if choice.engine is not None:
                            cost.engine_decisions += 1
                            cost.engine_nodes_unknown += choice.engine.reported_nodes is None
                            cost.engine_nodes += choice.engine.reported_nodes or 0
        if row.completed_pairs:
            row.score_rate = (row.wins + 0.5 * row.draws) / (2 * row.completed_pairs)
        summary.matchups.append(row)
    for cost in costs.values():
        cost.mean_move_ms = cost.elapsed_ms / cost.decisions if cost.decisions else None
    summary.costs = costs
    summary.fit = fit_ratings(list(spec.entrants), observations, spec.series.anchor, spec.series.rating)
    if spec.series.book.use == "smoke":
        summary.notes.insert(
            0, "Engineering smoke book: these ratings do not establish representative playing strength."
        )

    def existing_snapshot():
        if snapshot.exists():
            saved = BenchmarkSummary.model_validate_json(snapshot.read_text())
            if saved.model_dump(exclude={"created_at"}) != summary.model_dump(exclude={"created_at"}):
                raise ValueError("Saved rating snapshot differs from replayed and rescored evidence.")
            return saved
        return None

    if persist:
        with writer_lock(directory / ".reports.lock"):
            if saved := existing_snapshot():
                return saved
            snapshot.parent.mkdir(exist_ok=True)
            write_json(snapshot, summary.model_dump(mode="json"), indent=2)
        return summary
    return existing_snapshot() or summary
