"""The experiment CLI keeps execution, inspection, and reporting separate."""

import json
from pathlib import Path
from typing import Annotated

import typer

from qi.experiments.evidence import load_run
from qi.experiments.inspect import inspect_decision, load_traces
from qi.experiments.model import Plan
from qi.experiments.report import report
from qi.experiments.runner import run

app = typer.Typer(no_args_is_help=True, help="Recall and record experiments; execute and inspect bounded search runs.")


@app.command("preview")
def preview(plan: Annotated[Path, typer.Option()]):
    """Validate and show the comparison matrix without running searches."""
    typer.echo(json.dumps(Plan.model_validate_json(plan.read_text()).preview()))


@app.command("run")
def run_plan(
    plan: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    seconds: Annotated[float, typer.Option(min=0.001, max=3600)] = 600,
):
    """Execute into a fresh directory; persist partial work between decisions."""
    result = run(Plan.model_validate_json(plan.read_text()), output, seconds)
    typer.echo(json.dumps(result))
    if result["status"] in ("failed", "interrupted"):
        raise typer.Exit(1)


@app.command("verify")
def verify(directory: Annotated[Path, typer.Option("--run")]):
    """Validate raw records and recompute completion from saved units."""
    result = load_run(directory)
    typer.echo(
        json.dumps(
            {
                "traces": len(load_traces(directory, result)),
                **{key: result[key] for key in ("completed", "planned", "validation")},
            }
        )
    )


@app.command("report")
def render(directory: Annotated[Path, typer.Option("--run")], output: Annotated[Path, typer.Option()]):
    """Generate an interactive HTML file with no network or service dependency."""
    typer.echo(json.dumps(report(directory, output)))


@app.command("present")
def present_report(
    owner: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    view: Annotated[Path | None, typer.Option()] = None,
):
    """Present authored Markdown, optionally with pinned JSON comparisons, as offline HTML."""
    from qi.experiments.research import present

    typer.echo(json.dumps(present(owner, output, view)))


@app.command("inspect")
def inspect_saved(
    directory: Annotated[Path, typer.Option("--run")],
    unit: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
    turn: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1_000_000)] = 100_000,
):
    """Trace a saved decision; require original code and deterministic parity."""
    typer.echo(json.dumps(inspect_decision(directory, unit, turn, output, limit)))


@app.command("search")
def search_catalog(query: Annotated[str, typer.Argument()] = ""):
    """Recall prior experiments across teacher, learning and search work."""
    from qi.experiments.catalog import catalog

    typer.echo(catalog(query).model_dump_json())


@app.command("show")
def show_experiment(id: str):
    """Read an experiment's findings, limits, owner and evidence availability."""
    from qi.experiments.catalog import get_entry

    typer.echo(get_entry(id).model_dump_json())


@app.command("check-catalog")
def check_experiments(verify_evidence: bool = False, summary: bool = False):
    """Check registered entries and prior-work links; optionally verify available evidence hashes."""
    from qi.experiments.catalog import check_catalog

    result = check_catalog(verify_evidence=verify_evidence)
    typer.echo(
        json.dumps(
            {
                "entries": len(result.entries),
                "issues": [issue.model_dump() for issue in result.issues],
                "scope": result.scope,
            }
        )
        if summary
        else result.model_dump_json()
    )
    if result.issues:
        raise typer.Exit(1)


@app.command("owner")
def inspect_owner(path: str):
    """Read an owning record and its current hash before appending a revision."""
    from qi.experiments.catalog import read_owner

    typer.echo(json.dumps(read_owner(path)))


@app.command("template")
def experiment_template(id: str, title: str, question: str):
    """Emit a planned-entry JSON scaffold; fill conditions and the prior-work comparison before recording."""
    typer.echo(
        json.dumps(
            {
                "schema_version": 1,
                "id": id,
                "title": title,
                "question": question,
                "kind": "other",
                "topics": [],
                "execution": "planned",
                "conclusion": "unassessed",
                "conditions": "",
                "finding": "",
                "limitations": "",
                "decision": "",
                "revisit": "",
                "evidence": [],
                "prior_work": [],
                "novelty": "",
            },
            indent=2,
        )
    )


@app.command("record")
def record_experiment(
    owner: Annotated[str, typer.Option()],
    entry: Annotated[Path, typer.Option()],
    expected_sha256: Annotated[str, typer.Option()],
):
    """Append a validated entry/revision to an existing owning work item or report."""
    from qi.experiments.catalog import ExperimentEntry, record_entry

    typer.echo(
        record_entry(owner, ExperimentEntry.model_validate_json(entry.read_text()), expected_sha256).model_dump_json()
    )
