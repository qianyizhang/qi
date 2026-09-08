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

app = typer.Typer(no_args_is_help=True, help="Bounded local search experiments and offline inspection.")


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
