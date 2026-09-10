"""Explicit collection operations; JSON commands and production training remain compatible."""

import json
from pathlib import Path
from typing import Annotated

import typer

from qi.training_data.collection_generation import analyze_occurrence, generate_collection
from qi.training_data.compatibility import export_legacy, import_json
from qi.training_data.config import SupervisionSettings, load_preparation
from qi.training_data.generation import teacher_spec
from qi.training_data.snapshots import SelectionRecipe, export_snapshot, verify_snapshot
from qi.training_data.store import AnalysisSpec, Collection

app = typer.Typer(no_args_is_help=True, help="Incremental SQLite collections and frozen Parquet snapshots.")


@app.command("generate")
def generate(config: Annotated[Path, typer.Option()], store: Annotated[Path, typer.Option()]):
    """Generate or resume a pinned configuration, preserving prior committed games."""
    with Collection(store) as collection:
        typer.echo(json.dumps(generate_collection(collection, load_preparation(config))))


@app.command("inspect")
def inspect(store: Annotated[Path, typer.Option()]):
    """Query collection counts directly without materializing its records."""
    with Collection(store, readonly=True) as collection:
        typer.echo(json.dumps(collection.counts()))


@app.command("import-json")
def import_command(source: Annotated[Path, typer.Option()], store: Annotated[Path, typer.Option()]):
    with Collection(store) as collection:
        typer.echo(json.dumps(import_json(collection, source)))


@app.command("export")
def export(
    store: Annotated[Path, typer.Option()],
    recipe: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
):
    with Collection(store, readonly=True) as collection:
        typer.echo(
            json.dumps(export_snapshot(collection, SelectionRecipe.model_validate_json(recipe.read_text()), output))
        )


@app.command("verify")
def verify(snapshot: Annotated[Path, typer.Option()]):
    typer.echo(json.dumps(verify_snapshot(snapshot)))


@app.command("export-json")
def export_json(snapshot: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]):
    typer.echo(json.dumps(export_legacy(snapshot, output)))


@app.command("reanalyze")
def reanalyze(
    store: Annotated[Path, typer.Option()],
    occurrence: Annotated[int, typer.Option()],
    supervision: Annotated[Path, typer.Option()],
    force: bool = False,
):
    """Reuse first success or explicitly append another attempt; never generate a game."""
    settings = SupervisionSettings.model_validate_json(supervision.read_text())
    settings.engine = str((supervision.parent / settings.engine).resolve())
    settings.network = str((supervision.parent / settings.network).resolve())
    config = settings.teacher()
    spec = AnalysisSpec(supervision=teacher_spec(config), timeout_seconds=float(config.timeout_seconds))
    with Collection(store) as collection:
        answer = analyze_occurrence(collection, occurrence, config, spec, force=force)
        typer.echo(json.dumps({"analysis_spec": spec.identity, "move": answer.move}))


@app.command("positions")
def positions(store: Annotated[Path, typer.Option()], after: int = 0, limit: int = 100, board_hash: str | None = None):
    """Page indexed occurrences without loading the collection."""
    with Collection(store, readonly=True) as collection:
        typer.echo(json.dumps(collection.positions(after=after, limit=limit, board_hash=board_hash)))


@app.command("specs")
def specs(store: Annotated[Path, typer.Option()], after: int = 0, limit: int = 100):
    """List immutable supervision identities for selection recipes."""
    if after < 0 or not 1 <= limit <= 1000:
        raise ValueError("Use a nonnegative cursor and limit 1-1000.")
    with Collection(store, readonly=True) as collection:
        rows = collection.db.execute(
            "SELECT id,identity,json(payload) AS payload FROM analysis_specs WHERE id>? ORDER BY id LIMIT ?",
            (after, limit),
        )
        typer.echo(json.dumps([{**dict(row), "payload": json.loads(row["payload"])} for row in rows]))
