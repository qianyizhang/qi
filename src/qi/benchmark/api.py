"""Read-only discovery and results routes; clients cannot select filesystem paths."""

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import Field

from qi.artifacts import digest
from qi.benchmark.models import Record
from qi.benchmark.store import load_manifest, pool_state
from qi.benchmark.summary import BenchmarkSummary, read_snapshot, summarize_benchmark


class BenchmarkEntry(Record):
    id: str
    label: str
    series_id: str
    series_sha256: str
    created_at: str
    mode: str
    book_use: str


class BenchmarkCatalog(Record):
    entries: list[BenchmarkEntry] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class BenchmarkReport(Record):
    summary: BenchmarkSummary
    settings: dict[str, dict]
    book_provenance: str
    book_selection: str
    snapshots: list[str]


def directories() -> dict[str, Path]:
    roots = os.environ.get("QI_BENCHMARK_ROOTS", "artifacts/benchmarks").split(os.pathsep)
    result = {}
    for value in roots:
        if not value:
            continue
        root = Path(value).resolve()
        for path in sorted(root.glob("*/manifest.json")):
            resolved = path.resolve()
            if resolved.is_relative_to(root):
                directory = resolved.parent
                result[digest(str(directory))[:20]] = directory
    return result


def locate(id: str) -> Path:
    path = directories().get(id)
    if path is None:
        raise HTTPException(404, "Unknown benchmark.")
    return path


def catalog() -> BenchmarkCatalog:
    result = BenchmarkCatalog()
    for id, path in directories().items():
        try:
            manifest = load_manifest(path)
            spec = manifest.spec
            result.entries.append(
                BenchmarkEntry(
                    id=id,
                    label=spec.series.label,
                    series_id=spec.series.id,
                    series_sha256=spec.series.sha256,
                    created_at=manifest.created_at,
                    mode=spec.mode,
                    book_use=spec.series.book.use,
                )
            )
        except (ValueError, OSError) as exc:
            result.issues.append(f"{path.name}: {exc}")
    result.entries.sort(key=lambda row: row.created_at, reverse=True)
    return result


def register_benchmarks(app: FastAPI) -> None:
    @app.get("/api/benchmarks", response_model=BenchmarkCatalog)
    def list_benchmarks() -> BenchmarkCatalog:
        return catalog()

    @app.get("/api/benchmarks/{id}", response_model=BenchmarkReport)
    def report(id: str) -> BenchmarkReport:
        path = locate(id)
        summary = summarize_benchmark(path)
        spec = load_manifest(path).spec
        snapshots = [] if summary.results_hidden else sorted(p.stem for p in (path / "reports").glob("*.json"))
        return BenchmarkReport(
            summary=summary,
            settings={
                id: {"player_version": p.player_version, **p.model_dump(mode="json")["config"]}
                for id, p in spec.entrants.items()
            },
            book_provenance=spec.series.book.provenance,
            book_selection=spec.series.book.selection,
            snapshots=snapshots,
        )

    @app.get("/api/benchmarks/{id}/snapshots/{snapshot}", response_model=BenchmarkSummary)
    def saved_snapshot(id: str, snapshot: str) -> BenchmarkSummary:
        path = locate(id)
        if pool_state(load_manifest(path).spec) == "reserved":
            raise HTTPException(409, "Locked-test results have not been revealed.")
        if not re.fullmatch(r"[0-9a-f]{64}", snapshot):
            raise HTTPException(404, "Unknown snapshot.")
        file = path / "reports" / f"{snapshot}.json"
        if not file.resolve().is_relative_to(path.resolve()) or not file.is_file():
            raise HTTPException(404, "Unknown snapshot.")
        return read_snapshot(path, snapshot)
