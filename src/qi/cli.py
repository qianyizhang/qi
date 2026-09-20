"""Structured command adapter for the Xiangqi referee."""

import json
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.referee import Referee
from qi_game.reference import Game, PythonReferee, restore
from typer.exceptions import TyperException

from qi.arena import play_match
from qi.benchmark.cli import app as benchmark_app
from qi.evaluation import Corpus, evaluate_batch
from qi.evaluation_cli import app as evaluation_app
from qi.experiments.cli import app as experiments_app
from qi.learning.cli import app as learning_app
from qi.players import PlayerConfig, choose, list_players
from qi.teacher import TeacherConfig, analyze
from qi.training_data.cli import app as training_data_app

app = typer.Typer(no_args_is_help=True, help="Qi: local Xiangqi play and deterministic replay.")
app.add_typer(learning_app, name="learn")
app.add_typer(training_data_app, name="data")
app.add_typer(experiments_app, name="experiment")
app.add_typer(evaluation_app, name="eval")
app.add_typer(benchmark_app, name="bench")

referee: Referee = PythonReferee()


def show_version(value: bool) -> None:
    if value:
        typer.echo(version("qi"))
        raise typer.Exit()


@app.callback()
def options(
    version_flag: Annotated[bool, typer.Option("--version", callback=show_version, is_eager=True)] = False,
) -> None:
    pass


def load(path: Path) -> Game:
    return restore(load_snapshot(path))


def load_snapshot(path: Path) -> Snapshot:
    return Snapshot.model_validate_json(path.read_text())


@app.command("new")
def new_game() -> None:
    """Emit a new game snapshot; redirect stdout to save it."""
    typer.echo(Snapshot().model_dump_json())


@app.command("inspect")
def inspect_game(state: Annotated[Path, typer.Option("--state")]) -> None:
    """Inspect a saved game's reconstructed position."""
    typer.echo(referee.inspect(load_snapshot(state)).model_dump_json())


@app.command()
def legal(state: Annotated[Path, typer.Option("--state")]) -> None:
    """Emit the current legal moves."""
    position = referee.inspect(load_snapshot(state))
    typer.echo(json.dumps({"state_hash": position.state_hash, "legal_moves": position.legal_moves}))


@app.command()
def apply(
    state: Annotated[Path, typer.Option("--state")],
    move: Annotated[str, typer.Option("--move")],
    expected_state_hash: Annotated[str, typer.Option("--expected-state-hash")],
) -> None:
    """Apply one guarded move and emit a new snapshot."""
    position = referee.apply(load_snapshot(state), move, expected_state_hash)
    typer.echo(position.snapshot.model_dump_json())


@app.command()
def replay(
    state: Annotated[Path, typer.Option("--state")],
    ply: Annotated[int | None, typer.Option("--ply", min=0)] = None,
) -> None:
    """Validate a saved game, then inspect an optional historical ply."""
    snapshot = load_snapshot(state)
    position = referee.inspect(snapshot)
    if ply is not None:
        if ply > len(snapshot.moves):
            raise GameError("invalid_ply", "Requested ply is beyond this game's history.")
        position = referee.inspect(Snapshot(moves=snapshot.moves[:ply]))
    typer.echo(position.model_dump_json())


@app.command()
def play(port: Annotated[int, typer.Option(min=1024, max=65535)] = 8000) -> None:
    """Serve the built browser board on localhost."""
    import uvicorn

    if not (Path(__file__).parent / "static/index.html").exists():
        raise GameError("ui_not_built", "Run make web-build first.")
    typer.echo(f"Open http://127.0.0.1:{port}", err=True)
    uvicorn.run("qi.api:create_app", factory=True, host="127.0.0.1", port=port)


@app.command("players")
def players() -> None:
    """List registered players and their versions and browser defaults."""
    typer.echo(json.dumps([asdict(player) for player in list_players()]))


@app.command("choose")
def choose_move(
    state: Annotated[Path, typer.Option("--state")],
    player: Annotated[str, typer.Option()] = "alphabeta",
    seed: Annotated[int, typer.Option()] = 0,
    depth: Annotated[int, typer.Option(min=1, max=8)] = 2,
    nodes: Annotated[int, typer.Option(min=1)] = 128,
    rollout_plies: Annotated[
        int, typer.Option(min=0, max=64, help="MCTS rollout length; ignored by other players.")
    ] = 8,
) -> None:
    """Select a move without changing the saved game."""
    typer.echo(
        json.dumps(asdict(choose(load(state), PlayerConfig(player, seed, depth, nodes, rollout_plies=rollout_plies))))
    )


@app.command("match")
def match(
    red: Annotated[str, typer.Option()] = "alphabeta",
    black: Annotated[str, typer.Option()] = "random",
    seed: Annotated[int, typer.Option()] = 0,
    depth: Annotated[int, typer.Option(min=1, max=8)] = 2,
    nodes: Annotated[int, typer.Option(min=1)] = 128,
    opening: Annotated[Path | None, typer.Option()] = None,
    rollout_plies: Annotated[int, typer.Option(min=0, max=64)] = 8,
) -> None:
    """Run one complete game and emit a match record with a replayable snapshot."""
    record = play_match(
        PlayerConfig(red, seed, depth, nodes, rollout_plies=rollout_plies),
        PlayerConfig(black, seed + 1, depth, nodes, rollout_plies=rollout_plies),
        load(opening) if opening else None,
    )
    data = asdict(record)
    data["opening"] = record.opening.model_dump()
    data["snapshot"] = record.snapshot.model_dump()
    typer.echo(json.dumps(data))


@app.command("evaluate")
def evaluate_players(
    corpus: Annotated[Path, typer.Option()],
    player_a: Annotated[str, typer.Option()] = "alphabeta",
    player_b: Annotated[str, typer.Option()] = "random",
    seed: Annotated[int, typer.Option()] = 0,
    depth: Annotated[int, typer.Option(min=1, max=8)] = 2,
    nodes: Annotated[int, typer.Option(min=1)] = 128,
    rollout_plies: Annotated[int, typer.Option(min=0, max=64)] = 8,
) -> None:
    """Run each evaluation opening twice, swapping player colors."""
    record = evaluate_batch(
        Corpus.model_validate_json(corpus.read_text()),
        PlayerConfig(player_a, seed, depth, nodes, rollout_plies=rollout_plies),
        PlayerConfig(player_b, seed + 1, depth, nodes, rollout_plies=rollout_plies),
    )
    typer.echo(record.model_dump_json())


@app.command("teach")
def teacher_move(
    state: Annotated[Path, typer.Option("--state")],
    engine: Annotated[Path, typer.Option()],
    network: Annotated[Path, typer.Option()],
    nodes: Annotated[int, typer.Option(min=1)] = 10_000,
    depth: Annotated[int, typer.Option(min=1, max=64)] = 6,
    timeout: Annotated[float, typer.Option(min=0.01, max=120)] = 10,
) -> None:
    """Query a local UCI teacher; emit a legal proposal and engine-native analysis."""
    result = analyze(load(state), TeacherConfig(engine, network, nodes, depth, timeout))
    typer.echo(result.model_dump_json())


def main() -> None:
    try:
        app(standalone_mode=False)
    except TyperException as exc:
        typer.echo(json.dumps({"error": {"code": "invalid_arguments", "message": exc.format_message()}}), err=True)
        raise SystemExit(exc.exit_code) from exc
    except (GameError, ValidationError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, GameError) else "invalid_state"
        typer.echo(json.dumps({"error": {"code": code, "message": str(exc)}}), err=True)
        raise SystemExit(1) from exc
