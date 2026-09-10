"""Local app adapter; referee operations and owned trace jobs have separate lifecycles."""

from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from qi.experiment_api import register
from qi.game import Game, GameError
from qi.lab import TraceJobs
from qi.players import PlayerConfig, PlayerInfo, bind_config, choose, list_players
from qi.players.bindings import selection_config
from qi.protocol import (
    ApplyRequest,
    Controller,
    GameSession,
    InspectRequest,
    OpponentRequest,
    OpponentResult,
    PlayRequest,
    PlayResult,
    Position,
    SessionResult,
    inspect,
)


def create_app() -> FastAPI:
    jobs = TraceJobs()

    @asynccontextmanager
    async def lifespan(app):
        yield
        jobs.close()

    app = FastAPI(title="Qi local laboratory", version="0.2.0", lifespan=lifespan)
    register(app, jobs)

    @app.exception_handler(ValueError)
    async def invalid_evidence(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_evidence", "message": str(exc)}})

    @app.exception_handler(GameError)
    async def game_error(request: Request, exc: GameError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"error": {"code": exc.code, "message": str(exc)}})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": "Request does not match the game schema."}},
        )

    @app.get("/api/players", response_model=list[PlayerInfo])
    def players() -> list[PlayerInfo]:
        return list_players()

    @app.post("/api/new", response_model=Position)
    def new() -> Position:
        return inspect(Game())

    @app.post("/api/inspect", response_model=Position)
    def position(request: InspectRequest) -> Position:
        return inspect(request.snapshot.game())

    @app.post("/api/apply", response_model=Position)
    def apply(request: ApplyRequest) -> Position:
        return inspect(request.snapshot.game().apply(request.move, request.expected_state_hash))

    @app.post("/api/opponent", response_model=OpponentResult)
    def opponent(request: OpponentRequest) -> OpponentResult:
        game = request.snapshot.game()
        if game.state_hash != request.expected_state_hash:
            raise GameError("stale_state", "The position changed before the opponent request.")
        choice = choose(
            game,
            PlayerConfig(
                request.player,
                request.seed + len(game.moves),
                request.depth,
                request.nodes,
                rollout_plies=request.rollout_plies,
            ),
        )
        return OpponentResult(position=inspect(game.apply(choice.move, choice.state_hash)), choice=choice)

    @app.post("/api/play/controller/inspect", response_model=Controller)
    def controller(request: Controller):
        if request.player != "human":
            selection_config(request.player, request.settings, request.binding_sha256, request.checkpoint_sha256)
        return request

    @app.post("/api/play/choose", response_model=PlayResult)
    def play(request: PlayRequest):
        game = request.snapshot.game()
        if game.state_hash != request.expected_state_hash:
            raise GameError("stale_state", "The position changed before the player request.")
        selection = request.controller
        config = selection_config(
            selection.player, selection.settings, selection.binding_sha256, selection.checkpoint_sha256
        )
        config = bind_config(replace(config, seed=config.seed + len(game.moves)))
        choice = choose(game, config)
        return PlayResult(position=inspect(game.apply(choice.move, choice.state_hash)), choice=choice, config=config)

    @app.post("/api/play/session/inspect", response_model=SessionResult)
    def session(request: GameSession):
        return SessionResult(session=request, position=inspect(request.snapshot.game()))

    static = Path(__file__).parent / "static"
    if static.is_dir():
        if (static / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{page:path}", include_in_schema=False)
        def frontend(page: str):
            if page in ("", "play", "experiments", "reference") or (
                page.startswith("experiments/") and len(page.split("/")) == 2
            ):
                return FileResponse(static / "index.html")
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Not found."}})

    return app
