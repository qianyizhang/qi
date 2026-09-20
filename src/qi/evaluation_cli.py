"""Save reproducible paired evaluation evidence and summarize it independently."""

from pathlib import Path
from typing import Annotated

import typer
from qi_game.core import GameError

from qi.artifacts import write_json
from qi.evaluation import EvalRun, EvalSpec, run_evaluation, summarize_evaluation

app = typer.Typer(no_args_is_help=True, help="Versioned evaluation specs, evidence, and scores.")


@app.command("run")
def run_spec(spec: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]):
    """Run a spec into a fresh directory, preserving completion and failures."""
    specification = EvalSpec.model_validate_json(spec.read_text())
    output.mkdir(parents=True, exist_ok=False)
    run = run_evaluation(
        specification, save=lambda evidence: write_json(output / "run.json", evidence.model_dump(mode="json"))
    )
    summary = summarize_evaluation(run)
    typer.echo(summary.model_dump_json())
    if summary.status != "complete":
        raise GameError("evaluation_failed", f"Evaluation is {summary.status}; saved evidence: {output / 'run.json'}")


@app.command("summarize")
def summarize_run(run: Annotated[Path, typer.Option()]):
    """Validate and score saved run.json without executing searches."""
    evidence = EvalRun.model_validate_json(run.read_text())
    typer.echo(summarize_evaluation(evidence).model_dump_json())
