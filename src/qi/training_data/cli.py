"""File-based generation, frozen assembly and optional trainer adapters."""

import json
from pathlib import Path
from typing import Annotated

import typer
from qi_game.core import GameError

from qi.evaluation import Corpus
from qi.teacher import TeacherConfig
from qi.training_data.assembly import MixtureRecipe, assemble
from qi.training_data.config import load_preparation, prepare_dataset
from qi.training_data.contracts import GenerationRecipe, Library
from qi.training_data.generation import generate_library
from qi.training_data.store_cli import app as collection_app

app = typer.Typer(no_args_is_help=True, help="Replay-backed training examples and frozen mixtures.")
app.add_typer(collection_app, name="collection")


@app.command("prepare")
def prepare_command(
    config: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Generate and assemble from one pinned preparation config, without training."""
    result = prepare_dataset(load_preparation(config), output)
    typer.echo(json.dumps(result))
    if result["status"] != "complete":
        raise GameError("preparation_incomplete", "Preparation incomplete; inspect the saved library and summary.")


def fresh_output(path: Path) -> None:
    if path.exists():
        raise GameError("output_exists", "Choose a new output path; existing artifacts are never overwritten.")
    path.parent.mkdir(parents=True, exist_ok=True)


@app.command("generate")
def generate_command(
    recipe: Annotated[Path, typer.Option()],
    corpus: Annotated[Path, typer.Option()],
    engine: Annotated[Path, typer.Option()],
    network: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    nodes: int = 1000,
    depth: int = 3,
) -> None:
    """Save reusable examples after each source; report bounded partial work explicitly."""
    settings = GenerationRecipe.model_validate_json(recipe.read_text())
    settings.require_current()
    reserved = Corpus.model_validate_json(corpus.read_text())
    teacher = TeacherConfig(engine, network, nodes=nodes, depth=depth)
    fresh_output(output)
    # Claim this new file before generation; later replacements checkpoint only this run.
    with output.open("x") as stream:
        stream.write(Library(recipe=settings, reserved_corpus=reserved).model_dump_json(indent=2))

    def save(library: Library) -> None:
        pending = output.with_name(output.name + ".pending")
        with pending.open("x") as stream:
            stream.write(library.model_dump_json(indent=2))
        pending.replace(output)

    library = generate_library(settings, reserved, teacher, checkpoint=save)
    save(library)
    typer.echo(json.dumps({"status": library.status, "examples": len(library.examples), "output": str(output)}))
    if library.status != "complete":
        raise GameError("generation_incomplete", library.failure or "Generation is incomplete; partial examples saved.")


@app.command("assemble")
def assemble_command(
    library: Annotated[Path, typer.Option()],
    recipe: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Freeze a quota-accounted mixture; incomplete manifests are saved but cannot train."""
    dataset = assemble(
        Library.model_validate_json(library.read_text()), MixtureRecipe.model_validate_json(recipe.read_text())
    )
    fresh_output(output)
    with output.open("x") as stream:
        stream.write(dataset.model_dump_json(indent=2))
    typer.echo(dataset.manifest.model_dump_json())
    if dataset.manifest.status != "complete":
        raise GameError("mixture_incomplete", "Requested quotas were not met; inspect the saved manifest.")
