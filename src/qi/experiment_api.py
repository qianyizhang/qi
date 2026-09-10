"""HTTP adapter for registered experiment readers and bounded trace jobs."""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, Response

from qi.experiments.glossary import load_glossary
from qi.experiments.presentation import (
    Glossary,
    ReportBundle,
    ReportData,
    TracePage,
    UnitDetail,
    contained,
    read_bundle,
)
from qi.experiments.report import render_export
from qi.game import GameError
from qi.lab import RunEntry, TraceJob, TraceJobs, TraceRequest, discover, run_path


def register(app: FastAPI, jobs: TraceJobs) -> None:
    @app.get("/api/reference", response_model=Glossary)
    def reference():
        return load_glossary()

    @app.get("/api/experiments", response_model=list[RunEntry])
    def experiments():
        return [entry for entry, _ in discover().values()]

    @app.get("/api/experiments/{run_id}", response_model=ReportData)
    def detail(run_id: str):
        return read_bundle(run_path(run_id)).data

    @app.get("/api/experiments/{run_id}/bundle", response_model=ReportBundle)
    def bundle(run_id: str):
        return read_bundle(run_path(run_id))

    @app.get("/api/experiments/{run_id}/units/{unit_id}", response_model=UnitDetail)
    def unit(run_id: str, unit_id: str):
        selected = next((unit for unit in read_bundle(run_path(run_id)).units if unit.job.id == unit_id), None)
        if selected is None:
            raise GameError("unknown_unit", "Recorded unit not found.")
        return selected

    @app.get("/api/experiments/{run_id}/traces/{trace_id}", response_model=TracePage)
    def trace(
        run_id: str,
        trace_id: str,
        parent: int | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        view: Literal["all", "mcts-tree"] = "all",
        show_work: bool = False,
    ):
        selected = next((trace for trace in read_bundle(run_path(run_id)).traces if trace.summary.id == trace_id), None)
        if selected is None:
            raise GameError("unknown_trace", "Verified trace not found.")
        events = [
            event
            for event in selected.events
            if event.parent == parent
            and (show_work or event.kind != "work")
            and (view == "all" or parent is not None or event.kind == "mcts-tree")
        ]
        return TracePage(events=events[offset : offset + limit], total=len(events), offset=offset)

    @app.get("/api/experiments/{run_id}/export")
    def export(run_id: str, format: Literal["html", "md"] = "html"):
        body = render_export(read_bundle(run_path(run_id)), format)
        return Response(
            body,
            media_type="text/html" if format == "html" else "text/markdown",
            headers={"Content-Disposition": f'attachment; filename="qi-report.{format}"'},
        )

    @app.get("/api/experiments/{run_id}/evidence/{reference:path}")
    def evidence(run_id: str, reference: str):
        directory = run_path(run_id)
        path = contained(directory, directory / reference)
        if not path.is_file() or path.suffix not in (".json", ".md") or path.stat().st_size > 64 * 1024 * 1024:
            raise GameError("unknown_evidence", "Unsupported evidence reference.")
        return FileResponse(path, filename=Path(reference).name, media_type="text/plain")

    @app.get("/api/trace-jobs", response_model=list[TraceJob])
    def statuses():
        return jobs.list()

    @app.post("/api/trace-jobs", response_model=TraceJob)
    def start(request: TraceRequest):
        return jobs.start(request)

    @app.post("/api/trace-jobs/{job_id}/cancel", response_model=TraceJob)
    def cancel(job_id: str):
        return jobs.cancel(job_id)
