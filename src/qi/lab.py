"""Local experiment discovery and the single bounded trace-job owner."""

import fcntl
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from qi_game.core import GameError

from qi.artifacts import ROOT, digest
from qi.experiments.evidence import load_run, require
from qi.experiments.inspect import validate_trace
from qi.experiments.model import Plan
from qi.experiments.presentation import check_files, contained, trace_compatibility
from qi.experiments.runner import write_json

EXCLUDED = {".git", ".venv", "node_modules", "source", "sources", "snapshot", "snapshots", "traces", "units", "lab"}


class RunEntry(BaseModel):
    id: str
    name: str
    location: str
    kind: str
    status: str
    error: str | None = None


def roots() -> list[Path]:
    return [
        Path(value).expanduser().resolve()
        for value in os.environ.get("QI_EXPERIMENT_ROOTS", str(ROOT / "artifacts/experiments")).split(os.pathsep)
        if value
    ]


def discover() -> dict[str, tuple[RunEntry, Path]]:
    result = {}
    modified = {}
    for root_index, root in enumerate(roots()):
        for base, dirs, files in os.walk(root, followlinks=False):
            path = Path(base)
            dirs[:] = sorted(
                name
                for name in dirs
                if name not in EXCLUDED and not name.startswith(".") and not (path / name).is_symlink()
            )
            if len(path.relative_to(root).parts) >= 6:
                dirs[:] = []
            if "manifest.json" not in files:
                continue
            dirs[:] = []
            key = digest([str(root), str(path.relative_to(root))])[:24]
            entry = RunEntry(
                id=key,
                name=path.name,
                location=f"root {root_index + 1}/{path.relative_to(root)}",
                kind="unknown",
                status="invalid",
            )
            try:
                source = contained(root, path / "manifest.json")
                require(source.stat().st_size <= 4 * 1024 * 1024, "Manifest exceeds 4 MiB.")
                manifest = json.loads(source.read_text())
                require(isinstance(manifest, dict), "Manifest must be a JSON object.")
                if "plan" not in manifest or "players" not in manifest["plan"]:
                    entry.kind = str(manifest.get("kind", manifest.get("format", "unknown")))[:100]
                    entry.status = "unsupported"
                    entry.error = "This run format has no registered reader yet."
                else:
                    entry.kind = "search"
                    plan = Plan.model_validate(manifest["plan"])
                    require(manifest["schema_version"] == 1, "Unsupported search schema version.")
                    require(manifest["plan_sha256"] == digest(manifest["plan"]), "Manifest identity mismatch.")
                    entry.name = plan.name
                    status = contained(path, path / "status.json")
                    entry.status = "incomplete"
                    if status.exists():
                        require(status.stat().st_size <= 4 * 1024 * 1024, "Status exceeds 4 MiB.")
                        value = json.loads(status.read_text())
                        require(isinstance(value, dict), "Run status must be a JSON object.")
                        require(
                            value.get("status") in ("running", "complete", "deadline", "failed", "interrupted"),
                            "Invalid run status.",
                        )
                        entry.status = value["status"]
            except (ValueError, KeyError, TypeError, OSError, GameError) as exc:
                entry.status = "invalid"
                entry.error = str(exc)
            try:
                modified[key] = path.stat().st_mtime_ns
            except OSError:
                modified[key] = 0
                entry.status, entry.error = "invalid", "Run directory is no longer readable."
            result[key] = (entry, path)
            if len(result) >= 500:
                return dict(sorted(result.items(), key=lambda item: modified[item[0]], reverse=True))
    return dict(sorted(result.items(), key=lambda item: modified[item[0]], reverse=True))


def run_path(run_id: str) -> Path:
    entry = discover().get(run_id)
    if entry is None:
        raise GameError("unknown_run", "Run is not in the configured experiment roots.")
    if entry[0].error:
        raise GameError("unreadable_run", entry[0].error)
    check_files(entry[1])
    return entry[1]


class TraceRequest(BaseModel):
    run_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    unit_id: str = Field(pattern=r"^unit-[0-9]{5}$")
    unit_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    turn_index: int = Field(ge=0, le=299)
    limit: int = Field(default=100_000, ge=1, le=1_000_000)
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class TraceJob(BaseModel):
    id: str
    request: TraceRequest
    status: Literal["running", "succeeded", "failed", "cancelled", "timed-out", "interrupted"]
    started: float
    finished: float | None = None
    message: str
    trace_id: str | None = None
    events: int | None = None
    recording_complete: bool | None = None
    deadline_seconds: float


class TraceJobs:
    def __init__(self, state: Path | None = None, deadline: float | None = None):
        self.state = state or Path(os.environ.get("QI_LAB_STATE", str(ROOT / "artifacts/lab")))
        self.deadline = deadline if deadline is not None else float(os.environ.get("QI_TRACE_SECONDS", "120"))
        require(0 < self.deadline <= 3600, "QI_TRACE_SECONDS must be in (0, 3600].")
        self.lock = threading.RLock()
        self.process: subprocess.Popen | None = None
        self.lease = None
        self.jobs: list[TraceJob] | None = None
        self.revision: str | None = None
        self.worker_thread: threading.Thread | None = None

    def _acquire(self):
        self.state.mkdir(parents=True, exist_ok=True)
        handle = (self.state / "owner.lock").open("a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            raise GameError("trace_busy", "Another server owns the trace job state.") from None
        return handle

    def _load(self, lease=None):
        if self.process is not None:
            return
        acquired = lease is None
        lease = lease or self._acquire()
        try:
            path = self.state / "jobs.json"
            require(not path.exists() or path.stat().st_size <= 1024 * 1024, "Job metadata exceeds 1 MiB.")
            rows = json.loads(path.read_text()) if path.exists() else []
            revision = digest(rows)
            if self.jobs is not None and revision == self.revision:
                return
            self.jobs = [TraceJob.model_validate(row) for row in rows]
            self.revision = revision
            interrupted = False
            for job in self.jobs:
                if job.status == "running":
                    interrupted = True
                    job.status, job.finished, job.message = (
                        "interrupted",
                        time.time(),
                        "Server stopped; job was not resumed.",
                    )
            if interrupted:
                self._save()
        finally:
            if acquired:
                lease.close()

    def _save(self):
        rows = [job.model_dump() for job in self.jobs[-32:]]
        write_json(self.state / "jobs.json", rows)
        self.revision = digest(rows)

    def list(self) -> list[TraceJob]:
        with self.lock:
            self._load()
            return [job.model_copy(deep=True) for job in reversed(self.jobs)]

    def start(self, request: TraceRequest) -> TraceJob:
        with self.lock:
            if self.process is not None:
                duplicate = next((job for job in self.jobs if job.request.request_id == request.request_id), None)
                if duplicate:
                    if duplicate.request != request:
                        raise GameError("request_conflict", "Request ID already belongs to a different trace request.")
                    return duplicate.model_copy(deep=True)
                raise GameError("trace_busy", "A trace is already running; cancel it or wait for completion.")
            self.lease = self._acquire()
            try:
                return self._start(request)
            finally:
                if self.process is None and self.lease is not None:
                    self.lease.close()
                    self.lease = None

    def _start(self, request: TraceRequest) -> TraceJob:
        self._load(self.lease)
        duplicate = next((job for job in self.jobs if job.request.request_id == request.request_id), None)
        if duplicate:
            if duplicate.request != request:
                raise GameError("request_conflict", "Request ID already belongs to a different trace request.")
            return duplicate.model_copy(deep=True)
        directory = run_path(request.run_id)
        run = load_run(directory)
        reason = trace_compatibility(run)
        if reason:
            raise GameError("trace_incompatible", reason)
        unit = next((unit for unit in run["units"] if unit["job"]["id"] == request.unit_id), None)
        if unit is None or unit["sha256"] != request.unit_sha256 or request.turn_index >= len(unit["turns"]):
            raise GameError("stale_evidence", "Selected decision or unit identity changed.")
        job = TraceJob(
            id=uuid4().hex,
            request=request,
            status="running",
            started=time.time(),
            message="Computing and recording the selected decision.",
            deadline_seconds=self.deadline,
        )
        pending = self.state / f"{job.id}.pending.json"
        self.jobs = [*self.jobs[-31:], job]
        try:
            self._save()
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "qi.trace_worker",
                    str(directory),
                    request.unit_id,
                    str(request.turn_index),
                    str(pending.resolve()),
                    str(request.limit),
                    str(self.deadline + 5),
                    str(os.getpid()),
                ],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.worker_thread = threading.Thread(
                target=self._finish, args=(job, directory, pending, self.process), daemon=True
            )
            self.worker_thread.start()
        except (OSError, RuntimeError) as exc:
            self.worker_thread = None
            if self.process is not None:
                self.process.kill()
                self.process.wait(timeout=5)
                self.process = None
            job.status, job.finished, job.message = "failed", time.time(), f"Cannot start trace: {exc}"
            # Persist under the same lease; start() releases ownership after this write.
            try:
                self._save()
            except OSError:
                pass
            raise GameError("trace_start_failed", job.message) from exc
        return job.model_copy(deep=True)

    def _finish(self, job, directory, pending, process):
        try:
            process.wait(timeout=self.deadline)
        except subprocess.TimeoutExpired:
            with self.lock:
                if job.status == "running":
                    self._stop(job, "timed-out", "Server deadline reached; no trace published.")
        with self.lock:
            if job.status == "running":
                try:
                    require(
                        process.returncode == 0 and pending.exists(), "Trace computation failed; no trace published."
                    )
                    trace = json.loads(pending.read_text())
                    check_files(directory)
                    run = load_run(directory)
                    unit = next(unit for unit in run["units"] if unit["job"]["id"] == job.request.unit_id)
                    require(unit["sha256"] == job.request.unit_sha256, "Source evidence changed during tracing.")
                    validate_trace(trace, unit, run["manifest"])
                    target = contained(directory, directory / "traces" / f"ui-{job.id}.json")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    require(not target.exists(), "Trace destination already exists.")
                    # Write in destination filesystem; link publishes without overwriting an existing file.
                    staging = target.with_suffix(".pending")
                    write_json(staging, trace)
                    try:
                        os.link(staging, target)
                    finally:
                        staging.unlink(missing_ok=True)
                    job.status, job.trace_id = "succeeded", target.stem
                    job.events = len(trace["recording"]["events"])
                    job.recording_complete = trace["recording"]["complete"]
                    job.message = "Decision parity verified; trace published."
                except Exception as exc:
                    job.status, job.message = "failed", str(exc)[:2000]
                job.finished = time.time()
            try:
                pending.unlink(missing_ok=True)
                self._save()
            finally:
                self.process = None
                self.lease.close()
                self.lease = None

    def _stop(self, job, status, message):
        job.status, job.message, job.finished = status, message, time.time()
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)

    def cancel(self, job_id: str) -> TraceJob:
        with self.lock:
            self._load()
            job = next((job for job in self.jobs if job.id == job_id), None)
            if job is None:
                raise GameError("unknown_job", "Trace job not found.")
            if job.status == "running":
                self._stop(job, "cancelled", "Cancelled; no trace published.")
                self._save()
            return job.model_copy(deep=True)

    def close(self):
        with self.lock:
            for job in self.jobs or []:
                if job.status == "running":
                    self._stop(job, "interrupted", "Server stopped; no trace published.")
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
