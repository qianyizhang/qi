"""Explicit dataset and training commands; ordinary play needs no training import."""

import json
from pathlib import Path
from typing import Annotated

import typer

from qi.evaluation import Corpus
from qi.game import GameError
from qi.learning.data import Dataset, generate
from qi.teacher import TeacherConfig

app = typer.Typer(no_args_is_help=True, help="Bounded local teacher-imitation experiments.")


@app.command("dataset")
def build_dataset(
    corpus: Annotated[Path, typer.Option()],
    engine: Annotated[Path, typer.Option()],
    network: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    seed: int = 7,
    games: int = 16,
    plies: int = 32,
    samples: int = 8,
    nodes: int = 1000,
    depth: int = 3,
    seconds: float = 300,
) -> None:
    """Generate replayable random trajectories and label disjoint, nonreserved inputs."""
    if output.exists():
        raise GameError("dataset_exists", "Choose a new output path; existing datasets are preserved.")
    data = generate(
        Corpus.model_validate_json(corpus.read_text()),
        TeacherConfig(engine, network, nodes, depth),
        seed=seed,
        games=games,
        plies=plies,
        samples=samples,
        seconds=seconds,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(data.model_dump_json(indent=2) + "\n")
    typer.echo(
        json.dumps(
            {
                "dataset": str(output.resolve()),
                "sha256": data.digest,
                "train": len(data.split_labels("train")),
                "validation": len(data.split_labels("validation")),
            }
        )
    )


@app.command("train")
def train_policy(
    data: Annotated[Path, typer.Option()],
    checkpoint: Annotated[Path, typer.Option()],
    seed: int = 7,
    steps: int = 200,
    seconds: float = 60,
    learning_rate: float = 0.01,
    diagnostic_examples: int = 0,
) -> None:
    """Fit a CPU policy, save new weights, and report held-out and reload checks."""
    try:
        from qi.learning.train import train
    except ImportError as exc:
        raise GameError("learning_not_installed", "Install the learning extra: uv sync --extra learning.") from exc
    result = train(
        Dataset.model_validate_json(data.read_text()),
        checkpoint,
        seed=seed,
        steps=steps,
        seconds=seconds,
        learning_rate=learning_rate,
        diagnostic_examples=diagnostic_examples,
    )
    typer.echo(json.dumps(result))
