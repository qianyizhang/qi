"""Explicit dataset and training commands; ordinary play needs no training import."""

import json
from pathlib import Path
from typing import Annotated

import typer

from qi.evaluation import Corpus
from qi.game import GameError
from qi.teacher import TeacherConfig
from qi.training_data.v1 import Dataset, generate

app = typer.Typer(no_args_is_help=True, help="Bounded local teacher-imitation experiments.")


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


@app.command("train")
def train_policy(
    data: Annotated[Path, typer.Option()],
    checkpoint: Annotated[Path, typer.Option()],
    seed: int = 7,
    steps: int = 200,
    seconds: float = 60,
    learning_rate: float = 0.01,
    diagnostic_examples: int = 0,
    device: str = "cpu",
    threads: int = 1,
) -> None:
    """Fit a CPU/MPS policy and save a CPU-compatible checkpoint."""
    from qi.learning.config import RunConfig
    from qi.training_data.loading import load_dataset

    resolved = RunConfig.model_validate(
        {
            "data": {
                "dataset": str(data.resolve()),
                "selection": "source-order",
                "train_size": diagnostic_examples or None,
            },
            "optimizer": {"learning_rate": learning_rate},
            "training": {"seed": seed, "updates": steps},
            "execution": {"device": device, "threads": threads, "fit_seconds": seconds},
        }
    )
    try:
        from qi.learning.train import train, validate_device
    except ImportError as exc:
        raise GameError("learning_not_installed", "Install the learning extra: uv sync --extra learning.") from exc
    dataset = load_dataset(data)
    resolved.data.train_size = len(resolved.training_inputs(dataset))
    config_path = checkpoint.with_name(checkpoint.name + ".config.json")
    report_path = checkpoint.with_name(checkpoint.name + ".report.json")
    resolved.origin_config = str(config_path.resolve())
    validate_device(device, threads)
    if checkpoint.exists():
        raise GameError("checkpoint_exists", "Choose a new checkpoint path; training never overwrites weights.")
    if config_path.exists():
        raise GameError("config_exists", "Choose a new checkpoint path; its saved config already exists.")
    if report_path.exists():
        raise GameError("report_exists", "Choose a new checkpoint path; its saved report already exists.")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("x") as stream:
        stream.write(resolved.model_dump_json(indent=2) + "\n")
    result = train(
        dataset,
        checkpoint,
        seed=seed,
        steps=steps,
        seconds=seconds,
        learning_rate=learning_rate,
        diagnostic_examples=diagnostic_examples,
        device=device,
        threads=threads,
    )
    with report_path.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    typer.echo(json.dumps(result))
    if result["status"] != "complete":
        raise GameError(
            "training_incomplete", "Optimization stopped before all requested updates; see the saved report."
        )


@app.command("experiment")
def learning_experiment(
    data: Annotated[Path, typer.Option()],
    corpus: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    sizes: str = "96,192,384,768",
    seeds: str = "7,17,27",
    subset_seed: int = 7,
    device: str = "cpu",
    threads: int = 1,
    steps: int = 200,
    learning_rate: float = 0.01,
    fit_seconds: float = 60,
    total_seconds: float = 600,
    preview_only: Annotated[bool, typer.Option("--preview")] = False,
) -> None:
    """Measure nested training sizes against one fixed held-out split."""
    from qi.learning.experiment import LearningPlan, preview, run_experiment

    plan = LearningPlan(
        sizes=[int(value) for value in sizes.split(",")],
        seeds=[int(value) for value in seeds.split(",")],
        subset_seed=subset_seed,
        device=device,
        threads=threads,
        steps=steps,
        learning_rate=learning_rate,
        fit_seconds=fit_seconds,
        total_seconds=total_seconds,
    )
    dataset = Dataset.model_validate_json(data.read_text())
    reserved = Corpus.model_validate_json(corpus.read_text())
    if preview_only:
        typer.echo(json.dumps(preview(dataset, reserved, plan)))
        return
    try:
        result = run_experiment(dataset, reserved, plan, output)
    except ImportError as exc:
        raise GameError("learning_not_installed", "Install the learning extra: uv sync --extra learning.") from exc
    typer.echo(json.dumps(result))
    if result["status"] != "complete":
        raise GameError(
            "experiment_incomplete", "The requested matrix is incomplete; see summary.json for retained evidence."
        )
