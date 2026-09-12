"""Replay-validated matchups, costs and immutable local rating projections."""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import Field

from qi.artifacts import write_json
from qi.benchmark.models import Record
from qi.benchmark.ratings import Observation, RatingFit, fit_ratings
from qi.benchmark.store import (
    Attempt,
    Manifest,
    evidence_digest,
    load_manifest,
    now,
    pool_state,
    read_attempts,
    validate_attempts,
    validate_manifest,
    writer_lock,
)


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


class SnapshotVerification(Record):
    status: Literal["verified", "unverified"] = "unverified"
    source: Literal["live-evidence", "frozen-evidence", "reconstructed-evidence", "unavailable"] = "unavailable"
    reason: str = "Original historical inputs have not been verified."


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
    verification: SnapshotVerification = Field(default_factory=SnapshotVerification)


class SnapshotEvidence(Record):
    schema_version: Literal[1]
    manifest: Manifest
    attempts: dict[str, list[Attempt]]


class RatingSnapshot(Record):
    schema_version: Literal[2]
    summary: BenchmarkSummary
    evidence: SnapshotEvidence


def project_summary(manifest: Manifest, attempts: dict[str, list[Attempt]], pool: str) -> BenchmarkSummary:
    """Derive a projection from validated inputs without consulting mutable run files."""
    spec = manifest.spec
    slots = spec.slots()
    counts = Counter(a.status for entries in attempts.values() for a in entries)
    complete = {id: next((a for a in entries if a.status == "complete"), None) for id, entries in attempts.items()}
    finished = sum(a is not None for a in complete.values())
    status = "complete" if finished == len(slots) else "failed" if counts["failed"] else "incomplete"
    hidden = pool == "reserved"
    sha = evidence_digest(manifest, attempts)
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
        verification=SnapshotVerification(
            status="verified", source="live-evidence", reason="Replayed and rescored current run evidence."
        ),
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

    return summary


def snapshot_path(directory: Path, sha: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("Invalid rating snapshot identity.")
    path = directory / "reports" / f"{sha}.json"
    if not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Rating snapshot path escapes the benchmark directory.")
    return path


def verify_projection(saved: BenchmarkSummary, expected: BenchmarkSummary) -> None:
    # Timestamp and verification describe the saved artifact/read operation, not scoring.
    excluded = {"created_at", "verification"}
    if saved.model_dump(exclude=excluded) != expected.model_dump(exclude=excluded):
        raise ValueError("Saved rating snapshot differs from replayed and rescored evidence.")


def read_snapshot(directory: Path, sha: str) -> BenchmarkSummary:
    """Verify immutable inputs when retained, or identify unverifiable legacy projections."""
    manifest = load_manifest(directory)
    current_pool = pool_state(manifest.spec)
    if current_pool == "reserved":
        raise ValueError("Locked-test results have not been revealed.")
    data = json.loads(snapshot_path(directory, sha).read_text())
    frozen = None
    if isinstance(data, dict) and data.get("schema_version") == 1:
        saved = BenchmarkSummary.model_validate(data)
    else:
        snapshot = RatingSnapshot.model_validate(data)
        saved, frozen = snapshot.summary, snapshot.evidence
    if (
        saved.evidence_sha256 != sha
        or saved.spec_sha256 != manifest.spec_sha256
        or saved.series_sha256 != manifest.spec.series.sha256
        or saved.series_id != manifest.spec.series.id
    ):
        raise ValueError("Rating snapshot identity mismatch.")
    if saved.results_hidden:
        raise ValueError("A saved rating snapshot must contain revealed results.")
    allowed_pools = {
        "smoke": {"smoke"},
        "development": {"development", "development-from-retired-test"},
        "locked-test": {"retired"},
    }
    if saved.pool_status not in allowed_pools[manifest.spec.series.book.use]:
        raise ValueError("Rating snapshot pool status disagrees with its book use.")
    if frozen is not None:
        validate_manifest(frozen.manifest)
        if frozen.manifest.sha256 != manifest.sha256:
            raise ValueError("Frozen snapshot manifest differs from its run.")
        validate_attempts(frozen.manifest, frozen.attempts)
        if evidence_digest(frozen.manifest, frozen.attempts) != sha:
            raise ValueError("Frozen snapshot evidence digest mismatch.")
        attempts = frozen.attempts
        verification = SnapshotVerification(
            status="verified", source="frozen-evidence", reason="Replayed and rescored the snapshot's frozen inputs."
        )
    else:
        attempts = read_attempts(directory, manifest)
        if evidence_digest(manifest, attempts) != sha:
            return saved.model_copy(
                update={
                    "verification": SnapshotVerification(
                        reason=(
                            "Legacy snapshot has no frozen inputs and current evidence differs; ratings are unverified."
                        ),
                    )
                }
            )
        verification = SnapshotVerification(
            status="verified",
            source="reconstructed-evidence",
            reason="Original snapshot inputs reconstructed from matching current evidence.",
        )
    verify_projection(saved, project_summary(manifest, attempts, saved.pool_status))
    return saved.model_copy(update={"verification": verification})


def summarize_benchmark(directory: Path, *, reveal: bool = False, persist: bool = False) -> BenchmarkSummary:
    manifest = load_manifest(directory)
    attempts = read_attempts(directory, manifest)
    if reveal:
        if manifest.spec.series.book.use != "locked-test":
            raise ValueError("Only a locked-test benchmark has a reveal step.")
        if not all(any(a.status == "complete" for a in entries) for entries in attempts.values()):
            raise ValueError("A locked-test report can be revealed only after every planned game completes.")
    pool = pool_state(manifest.spec, action="reveal" if reveal else "read")
    summary = project_summary(manifest, attempts, pool)
    if summary.results_hidden:
        return summary
    path = snapshot_path(directory, summary.evidence_sha256)

    def existing_snapshot():
        if path.exists():
            saved = read_snapshot(directory, summary.evidence_sha256)
            verify_projection(saved, summary)
            return saved
        return None

    if not persist:
        return existing_snapshot() or summary
    with writer_lock(directory / ".reports.lock"):
        if saved := existing_snapshot():
            return saved
        summary.verification = SnapshotVerification(
            status="verified", source="frozen-evidence", reason="Replayed and rescored the snapshot's frozen inputs."
        )
        snapshot = RatingSnapshot(
            schema_version=2,
            summary=summary,
            evidence=SnapshotEvidence(schema_version=1, manifest=manifest, attempts=attempts),
        )
        path.parent.mkdir(exist_ok=True)
        write_json(path, snapshot.model_dump(mode="json"), indent=2)
    return summary
