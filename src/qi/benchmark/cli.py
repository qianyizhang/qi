"""Structured benchmark setup, execution, evidence verification and reveal."""

from pathlib import Path
from typing import Annotated

import typer

from qi.artifacts import write_json
from qi.benchmark.books import SourceGame, build_books
from qi.benchmark.models import BenchmarkSeries, BenchmarkSpec, Book, Entrant
from qi.benchmark.runner import run_benchmark
from qi.benchmark.store import load_manifest
from qi.benchmark.summary import summarize_benchmark
from qi.game import GameError
from qi.players import PlayerConfig

app = typer.Typer(no_args_is_help=True, help="Local Elo benchmarks with frozen players and replayable paired games.")


def save_new(path: Path, model) -> None:
    if path.exists():
        raise ValueError(f"Refusing to overwrite {path}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, model.model_dump(mode="json"), indent=2)


@app.command("template")
def template(
    book: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    pikafish_binding: Annotated[str, typer.Option()] = "pikafish-local",
    starts: Annotated[int, typer.Option(min=1)] = 16,
):
    """Write an editable six-player reference spec; no engines execute."""
    corpus = Book.model_validate_json(book.read_text())
    if starts > len(corpus.starts):
        raise ValueError("Requested more starts than the book contains.")
    references = [
        Entrant(id="random", label="Random", config=PlayerConfig("random", seed=7, nodes=1, depth=1)),
        Entrant(
            id="alphabeta",
            label="Alpha-beta · 128 visits",
            config=PlayerConfig("alphabeta", seed=7, nodes=128, depth=2),
        ),
        Entrant(
            id="alphabeta-enhanced",
            label="Enhanced alpha-beta · 128 visits",
            config=PlayerConfig("alphabeta-enhanced", seed=7, nodes=128, depth=2),
        ),
        Entrant(id="mcts", label="MCTS · 128 visits", config=PlayerConfig("mcts", seed=7, nodes=128, depth=2)),
        Entrant(
            id="pikafish-small",
            label="Pikafish · 1k nodes / depth 3",
            config=PlayerConfig(pikafish_binding, seed=7, nodes=1000, depth=3),
        ),
        Entrant(
            id="pikafish-large",
            label="Pikafish · 100k nodes / depth 8",
            config=PlayerConfig(pikafish_binding, seed=7, nodes=100000, depth=8),
        ),
    ]
    series = BenchmarkSeries(
        id="qi-local-v1", label="Qi local player benchmark", book=corpus, references=references, anchor="alphabeta"
    )
    save_new(output, BenchmarkSpec(series=series, starts=[s.id for s in corpus.starts[:starts]]))
    typer.echo(f"Wrote {output}; presets are explicit engineering defaults, not equal-compute settings.")


@app.command("freeze")
def freeze(spec: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]):
    """Resolve resource digests and player versions without playing games."""
    frozen = BenchmarkSpec.model_validate_json(spec.read_text()).freeze()
    save_new(output, frozen)
    typer.echo(frozen.model_dump_json())


@app.command("preview")
def preview(spec: Annotated[Path, typer.Option()]):
    """Show planned counts and identities without loading optional resources."""
    import json

    plan = BenchmarkSpec.model_validate_json(spec.read_text())
    typer.echo(
        json.dumps(
            {
                "spec_sha256": plan.sha256,
                "series_sha256": plan.series.sha256,
                "mode": plan.mode,
                "entrants": list(plan.entrants),
                "matchups": plan.matchups(),
                "paired_starts": len(plan.starts),
                "games": len(plan.slots()),
                "standard_start_diagnostics": plan.standard_start,
                "pinned": all(p.player_version for p in plan.entrants.values()),
                "book_use": plan.series.book.use,
            }
        )
    )


@app.command("candidate")
def candidate(
    baseline: Annotated[Path, typer.Option()],
    entrants: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    book: Annotated[Path | None, typer.Option()] = None,
):
    """Freeze a candidate/predecessor gauntlet using a saved reference run's conditions.

    Entrants is a JSON list of Entrant records; include the predecessor alongside
    the new checkpoint. Pass the baseline directory to run --reuse.
    """
    import json

    base = load_manifest(baseline).spec
    series, starts = base.series, base.starts
    if book is not None:
        corpus = Book.model_validate_json(book.read_text())
        if len(corpus.starts) < len(starts):
            raise ValueError("The replacement book has fewer starts than the frozen baseline selection.")
        series = series.model_copy(update={"book": corpus})
        starts = [s.id for s in corpus.starts[: len(starts)]]
    additions = [Entrant.model_validate(p) for p in json.loads(entrants.read_text())]
    plan = BenchmarkSpec(
        series=series,
        mode="gauntlet",
        candidates=additions,
        starts=starts,
        standard_start=base.standard_start,
    )
    save_new(output, plan.freeze())
    typer.echo(str(output))


@app.command("run")
def run(
    spec: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    reuse: Annotated[list[Path] | None, typer.Option()] = None,
):
    """Run a frozen batch and persist results; failures retain resumable evidence."""
    plan = BenchmarkSpec.model_validate_json(spec.read_text())
    run_benchmark(plan, output, reuse=reuse or [])
    result = summarize_benchmark(output, persist=True)
    typer.echo(result.model_dump_json())
    if result.status != "complete":
        raise GameError("benchmark_incomplete", f"Benchmark {result.status}; evidence retained at {output}.")


@app.command("resume")
def resume(
    run: Annotated[Path, typer.Option()],
    reuse: Annotated[list[Path] | None, typer.Option()] = None,
):
    """Continue unfinished games, retaining completed games and all failed attempts."""
    run_benchmark(load_manifest(run).spec, run, resume=True, reuse=reuse or [])
    result = summarize_benchmark(run, persist=True)
    typer.echo(result.model_dump_json())
    if result.status != "complete":
        raise GameError("benchmark_incomplete", f"Benchmark {result.status}; evidence retained at {run}.")


@app.command("summarize")
def summarize(run: Annotated[Path, typer.Option()], reveal: Annotated[bool, typer.Option()] = False):
    """Replay-validate and create a rating snapshot; --reveal retires a complete locked pool."""
    typer.echo(summarize_benchmark(run, reveal=reveal, persist=True).model_dump_json())


@app.command("book")
def book(
    sources: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    id: Annotated[str, typer.Option()],
):
    """Build family-separated books from source-attributed coordinate move records."""
    import json

    data = json.loads(sources.read_text())
    games = [SourceGame.model_validate(g) for g in data["games"]]
    dev, test, audit = build_books(games, id=id, provenance=data["provenance"])
    output.mkdir(parents=True, exist_ok=False)
    save_new(output / "development.json", dev)
    save_new(output / "locked-test.json", test)
    write_json(output / "audit.json", audit, indent=2)
    typer.echo(json.dumps(audit))
