"""Execute and recover planned matchups without changing the referee or players."""

from pathlib import Path
from time import perf_counter

from qi.arena import play_match
from qi.artifacts import provenance, write_json
from qi.benchmark.models import BenchmarkSpec
from qi.benchmark.store import (
    Attempt,
    Manifest,
    evidence_digest,
    load_manifest,
    now,
    pool_state,
    read_attempts,
    save_attempt,
    validate_attempt,
    writer_lock,
)


def run_benchmark(spec: BenchmarkSpec, directory: Path, *, resume: bool = False, reuse: list[Path] = ()) -> Manifest:
    directory = directory.resolve()
    with writer_lock(directory.parent / f".{directory.name}.lock"):
        if resume:
            manifest = load_manifest(directory)
            if spec.sha256 != manifest.spec.sha256:
                raise ValueError("Resume requires the exact saved resolved spec.")
            if spec.freeze().sha256 != spec.sha256:
                raise ValueError("Pinned players changed; create a new benchmark spec.")
            if spec.series.book.use == "locked-test" and pool_state(spec) == "retired":
                raise ValueError("A revealed benchmark cannot resume.")
        else:
            spec = spec.freeze()
            if directory.exists():
                raise ValueError("A fresh benchmark requires a new output directory.")
            # Validate sources before creating or reserving the destination.
            for source in reuse:
                source_manifest = load_manifest(source)
                if source_manifest.spec.series.sha256 != spec.series.sha256:
                    raise ValueError("Reuse requires identical frozen benchmark series.")
                if source_manifest.spec.series.book.use == "locked-test":
                    raise ValueError("Locked-test attempts cannot be reused into another run.")
                read_attempts(source, source_manifest)
            manifest = Manifest(spec=spec, spec_sha256=spec.sha256, created_at=now())
            pool_state(spec, action="reserve", owner=str(directory))
            directory.mkdir(parents=True)
            write_json(directory / "manifest.json", manifest.model_dump(mode="json"), indent=2)
        attempts = read_attempts(directory, manifest)
        slots = spec.slots()
        source_provenance = provenance()
        for entries in attempts.values():
            for attempt in entries:
                if attempt.status == "running":
                    attempt.status, attempt.finished_at = "interrupted", now()
                    attempt.error = "Previous writer stopped before a terminal attempt was saved."
                    save_attempt(directory, attempt)
        for source in reuse:
            old_manifest = load_manifest(source)
            if (
                old_manifest.spec.series.sha256 != spec.series.sha256
                or old_manifest.spec.series.book.use == "locked-test"
            ):
                raise ValueError("Reuse requires the same development series.")
            old_attempts = read_attempts(source, old_manifest)
            source_digest = evidence_digest(old_manifest, old_attempts)
            for slot in slots:
                if any(a.status == "complete" for a in attempts[slot.id]):
                    continue
                complete = [a for a in old_attempts.get(slot.id, []) if a.status == "complete"]
                if not complete:
                    continue
                # Identity includes series, both entrant configurations, start and color.
                original = complete[0]
                copied = original.model_copy(
                    update={
                        "number": len(attempts[slot.id]) + 1,
                        "reused_from": {
                            "directory": str(source.resolve()),
                            "evidence_sha256": source_digest,
                            "attempt_sha256": original.sha256,
                        },
                    }
                )
                validate_attempt(copied, slot, spec)
                save_attempt(directory, copied)
                attempts[slot.id].append(copied)
        paused: set[tuple[str, str]] = set()
        refs = {p.id for p in spec.series.references}
        if (
            spec.mode == "gauntlet"
            and spec.series.book.use != "locked-test"
            and any({s.a, s.b} <= refs and not any(a.status == "complete" for a in attempts[s.id]) for s in slots)
        ):
            raise ValueError(
                "Gauntlet needs completed reference pairs for every selected start; supply --reuse bootstrap."
            )
        for slot in slots:
            entries = attempts[slot.id]
            if any(a.status == "complete" for a in entries) or (slot.a, slot.b) in paused:
                continue
            attempt = Attempt(
                slot_id=slot.id,
                number=len(entries) + 1,
                status="running",
                started_at=now(),
                provenance=source_provenance,
            )
            save_attempt(directory, attempt)
            started = perf_counter()
            interrupted = False
            try:
                red, black = (slot.config_a, slot.config_b) if slot.a_side == "red" else (slot.config_b, slot.config_a)
                match = play_match(red, black, slot.start.snapshot.game())
                attempt.match, attempt.status, attempt.finished_at = match, "complete", now()
                validate_attempt(attempt, slot, spec)
            except (Exception, KeyboardInterrupt) as exc:
                interrupted = isinstance(exc, KeyboardInterrupt)
                attempt.status = "interrupted" if interrupted else "failed"
                attempt.error = f"{type(exc).__name__}: {exc}"
                attempt.match = None
                attempt.finished_at = now()
                paused.add((slot.a, slot.b))
            attempt.elapsed_seconds = perf_counter() - started
            save_attempt(directory, attempt)
            entries.append(attempt)
            if interrupted:
                break
        return manifest
