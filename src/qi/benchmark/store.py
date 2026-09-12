"""Durable plans and attempts; raw games remain the scoring authority."""

import fcntl
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from qi.arena import MatchRecord
from qi.artifacts import Provenance, digest, write_json
from qi.benchmark.models import BenchmarkSpec, GameSlot, Record
from qi.evaluation import EvalGame, EvalRun


def now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def writer_lock(path: Path) -> Iterator[None]:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f"Another writer owns {path}.") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class Manifest(Record):
    schema_version: Literal[1] = 1
    spec: BenchmarkSpec
    spec_sha256: str
    created_at: str


class Attempt(Record):
    schema_version: Literal[1] = 1
    slot_id: str
    number: int = Field(ge=1)
    status: Literal["running", "complete", "failed", "interrupted"]
    started_at: str
    finished_at: str | None = None
    elapsed_seconds: float | None = Field(default=None, ge=0)
    provenance: Provenance
    match: MatchRecord | None = None
    error: str | None = None
    reused_from: dict[str, str] | None = None


def validate_attempt(attempt: Attempt, slot: GameSlot, spec: BenchmarkSpec) -> None:
    if attempt.slot_id != slot.id:
        raise ValueError("Attempt belongs to a different game slot.")
    if (attempt.status == "complete") != (attempt.match is not None):
        raise ValueError("Only a completed attempt may contain a match.")
    if (attempt.status in ("failed", "interrupted")) != (attempt.error is not None):
        raise ValueError("Failed/interrupted attempts must retain their error.")
    if (attempt.status == "running") != (attempt.finished_at is None):
        raise ValueError("Attempt completion timestamp disagrees with status.")
    if attempt.match is not None:
        evaluation = slot.evaluation_spec()
        entries = [EvalGame(opening_id=slot.start.id, a_side=side) for side in ("red", "black")]
        entries[0 if slot.a_side == "red" else 1] = EvalGame(
            opening_id=slot.start.id,
            a_side=slot.a_side,
            status="complete",
            match=attempt.match,
        )
        EvalRun(
            schema_version=evaluation.schema_version,
            spec=evaluation,
            spec_sha256=evaluation.digest,
            provenance=attempt.provenance,
            player_versions={"a": spec.entrants[slot.a].player_version, "b": spec.entrants[slot.b].player_version},
            games=entries,
        )


def load_manifest(directory: Path) -> Manifest:
    manifest = Manifest.model_validate_json((directory / "manifest.json").read_text())
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Manifest) -> None:
    if manifest.spec_sha256 != manifest.spec.sha256:
        raise ValueError("Benchmark spec digest mismatch.")
    if any(not p.player_version for p in manifest.spec.entrants.values()):
        raise ValueError("The saved benchmark has unpinned entrant versions.")


def validate_attempts(manifest: Manifest, attempts: dict[str, list[Attempt]]) -> None:
    slots = {s.id: s for s in manifest.spec.slots()}
    if attempts.keys() != slots.keys():
        raise ValueError("Attempt inventory must contain exactly every planned game slot.")
    for id, entries in attempts.items():
        for number, attempt in enumerate(entries, start=1):
            validate_attempt(attempt, slots[id], manifest.spec)
            if attempt.number != number or (attempt.status == "complete" and number != len(entries)):
                raise ValueError("Attempt sequence contains a gap or retries a completed game.")


def read_attempts(directory: Path, manifest: Manifest) -> dict[str, list[Attempt]]:
    slots = {s.id: s for s in manifest.spec.slots()}
    result: dict[str, list[Attempt]] = {id: [] for id in slots}
    root = (directory / "attempts").resolve()
    if not root.is_relative_to(directory.resolve()):
        raise ValueError("Attempt directory escapes the benchmark directory.")
    for path in sorted(root.glob("*/*.json")):
        if not path.resolve().is_relative_to(root):
            raise ValueError("Attempt path escapes its evidence directory.")
        attempt = Attempt.model_validate_json(path.read_text())
        if attempt.slot_id not in slots or path.parent.name != attempt.slot_id or path.stem != f"{attempt.number:06d}":
            raise ValueError("Attempt filename does not match a planned game slot.")
        result[attempt.slot_id].append(attempt)
    validate_attempts(manifest, result)
    return result


def save_attempt(directory: Path, attempt: Attempt) -> None:
    path = directory / "attempts" / attempt.slot_id / f"{attempt.number:06d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, attempt.model_dump(mode="json"))


def evidence_digest(manifest: Manifest, attempts: dict[str, list[Attempt]]) -> str:
    return digest(
        {
            "manifest": manifest.sha256,
            "attempts": {id: [a.sha256 for a in entries] for id, entries in sorted(attempts.items())},
        }
    )


def state_root() -> Path:
    return Path(os.environ.get("QI_BENCHMARK_STATE", "artifacts/benchmark-state")).resolve()


def pool_keys(spec: BenchmarkSpec) -> list[str]:
    # Content keys survive cosmetic book renaming and subset selection.
    keys = set()
    for start in spec.series.book.starts:
        keys.add(digest({"family": start.family}))
        keys.add(digest({"source_game": start.source_game}))
        game = start.snapshot.game()
        keys.add(digest({"board": game.board, "turn": game.turn}))
    return sorted(keys)


def pool_state(spec: BenchmarkSpec, *, action: Literal["read", "reserve", "reveal"] = "read", owner: str = "") -> str:
    use = spec.series.book.use
    if use == "smoke":
        return use
    root = state_root()
    with writer_lock(root / ".lock"):
        path = root / "pools.json"
        pools = json.loads(path.read_text()) if path.exists() else {}
        records = [pools.get(key) for key in pool_keys(spec)]
        if use == "development":
            if any(r and r["state"] == "reserved" for r in records):
                raise ValueError("Development book overlaps a reserved locked-test pool.")
            retired = any(r and r["state"] == "retired" for r in records)
            if action == "reserve":
                for key in pool_keys(spec):
                    if key not in pools:
                        pools[key] = {"spec": spec.sha256, "state": "development", "owner": owner}
                write_json(path, pools)
            return "development-from-retired-test" if retired else "development"
        if action == "reserve":
            for record in records:
                if record and (
                    record["spec"] != spec.sha256 or record["state"] != "reserved" or record["owner"] != owner
                ):
                    raise ValueError(
                        "Locked pool overlaps a development, reserved or retired family/start; use a fresh pool."
                    )
            for key in pool_keys(spec):
                pools[key] = {"spec": spec.sha256, "state": "reserved", "owner": owner}
            write_json(path, pools)
            return "reserved"
        if not records or any(r is None or r["spec"] != spec.sha256 for r in records):
            raise ValueError("Locked pool reservation is missing or belongs to another spec.")
        state = "retired" if all(r["state"] == "retired" for r in records) else "reserved"
        if action == "reveal":
            for key in pool_keys(spec):
                pools[key]["state"] = "retired"
            write_json(path, pools)
            state = "retired"
        return state
