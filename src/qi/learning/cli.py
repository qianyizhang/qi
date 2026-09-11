"""Explicit dataset and training commands; ordinary play needs no training import."""

import json
from pathlib import Path
from typing import Annotated

import typer

from qi.evaluation import Corpus
from qi.game import GameError
from qi.teacher import TeacherConfig
from qi.training_data.v1 import generate

app = typer.Typer(no_args_is_help=True, help="Bounded local teacher-imitation experiments.")


@app.command("snapshot")
def snapshot_run(
    config: Annotated[Path, typer.Option()],
    output: Annotated[Path | None, typer.Option()] = None,
    preview_only: Annotated[bool, typer.Option("--preview")] = False,
) -> None:
    """Prepare and train a verified Parquet snapshot using bounded full-batch updates."""
    from qi.learning.snapshot import SnapshotConfig, SnapshotTensors, prepare_snapshot, train_snapshot
    from qi.training_data.snapshots import SnapshotReader

    settings = SnapshotConfig.model_validate_json(config.read_text())
    snapshot = Path(settings.data.snapshot)
    if not snapshot.is_absolute():
        snapshot = (config.parent / snapshot).resolve()
    settings.data.snapshot = str(snapshot)
    reader = SnapshotReader(snapshot)
    if preview_only:
        typer.echo(
            json.dumps(
                {
                    "config": settings.model_dump(),
                    "rows": reader.manifest["rows"],
                    "snapshot_fingerprint": reader.manifest["fingerprint"],
                }
            )
        )
        return
    if output is None:
        raise GameError("missing_output", "Provide --output for execution, or use --preview.")
    if output.exists():
        raise GameError("experiment_exists", "Choose a fresh output directory.")
    output.mkdir(parents=True)
    prepare_snapshot(snapshot, output / "tensors", chunk_size=settings.training.chunk_size)
    report = train_snapshot(SnapshotTensors(output / "tensors"), settings, output / "fit")
    typer.echo(json.dumps(report))
    if report["status"] != "complete":
        raise GameError("experiment_incomplete", "Snapshot fit did not complete all requested updates.")


@app.command("reference")
def reference_run(
    output: Annotated[Path | None, typer.Option()] = None,
    preview_only: Annotated[bool, typer.Option("--preview")] = False,
) -> None:
    """Run and verify the bundled tiny CPU experiment without a teacher or checkout."""
    from qi.learning.reference import run_reference

    try:
        result = run_reference(output, preview_only=preview_only)
    except ImportError as exc:
        raise GameError(
            "learning_not_installed",
            "Install this qi distribution with its learning extra; in a checkout: uv sync --locked --extra learning.",
        ) from exc
    typer.echo(json.dumps(result))
    if result.get("status") == "failed":
        raise GameError("reference_failed", "Reference checks failed; see verification.json.")


@app.command("run")
def configured_run(
    config: Annotated[Path, typer.Option()],
    output: Annotated[Path | None, typer.Option()] = None,
    preview_only: Annotated[bool, typer.Option("--preview")] = False,
) -> None:
    """Run a JSON recipe or a saved trial config; scientific settings belong to the file."""
    from qi.learning.config import load_recipe
    from qi.learning.runs import preview_recipe, run_recipe
    from qi.training_data.loading import load_dataset

    recipe = load_recipe(config)
    dataset = load_dataset(Path(recipe.data.dataset))
    if preview_only:
        typer.echo(json.dumps(preview_recipe(recipe, dataset)))
        return
    if output is None:
        raise GameError("missing_output", "Provide --output for execution, or use --preview.")
    try:
        result = run_recipe(recipe, dataset, output, source_config=config)
    except ImportError as exc:
        raise GameError("learning_not_installed", "Install the learning extra: uv sync --extra learning.") from exc
    typer.echo(json.dumps(result))
    if result["status"] != "complete":
        raise GameError("experiment_incomplete", "The requested cases are incomplete; see summary.json.")


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
    workers: int = 1,
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
        workers=workers,
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
