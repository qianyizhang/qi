"""Local app adapter; referee operations and owned trace jobs have separate lifecycles."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from qi_game.contracts import Position, Snapshot
from qi_game.core import GameError
from qi_game.referee import Referee
from qi_game.reference import PythonReferee, restore
from starlette.exceptions import HTTPException

from qi.benchmark.api import register_benchmarks
from qi.collection_api import register_collections
from qi.experiment_api import register_experiments
from qi.generation_lesson import register_generation_lesson
from qi.lab import TraceJobs
from qi.players import PlayerInfo, choose, list_players, resolve_selection
from qi.protocol import (
    ApplyRequest,
    Controller,
    ErrorResponse,
    GameSession,
    InspectRequest,
    PlayRequest,
    PlayResult,
    SessionResult,
)


def create_app(*, referee: Referee | None = None) -> FastAPI:
    backend = PythonReferee() if referee is None else referee
    jobs = TraceJobs()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        jobs.close()

    app = FastAPI(
        title="Qi local laboratory",
        version="0.2.0",
        lifespan=lifespan,
        responses={code: {"model": ErrorResponse} for code in (404, 405, 409, 422)},
    )
    register_experiments(app, jobs)
    register_collections(app)
    register_generation_lesson(app)
    register_benchmarks(app)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 409: "conflict"}.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={"error": {"code": code, "message": str(exc.detail)}},
        )

    @app.exception_handler(ValueError)
    async def invalid_evidence(request: Request, exc: ValueError) -> JSONResponse:
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
        return backend.inspect(Snapshot())

    @app.post("/api/inspect", response_model=Position)
    def position(request: InspectRequest) -> Position:
        return backend.inspect(request.snapshot)

    @app.post("/api/apply", response_model=Position)
    def apply(request: ApplyRequest) -> Position:
        return backend.apply(request.snapshot, request.move, request.expected_state_hash)

    @app.post("/api/play/controller/inspect", response_model=Controller)
    def controller(request: Controller) -> Controller:
        if request.player != "human":
            resolve_selection(request.player, request.settings, request.binding_sha256, request.checkpoint_sha256)
        return request

    @app.post("/api/play/choose", response_model=PlayResult)
    def play(request: PlayRequest) -> PlayResult:
        game = restore(request.snapshot)
        if game.state_hash != request.expected_state_hash:
            raise GameError("stale_state", "The position changed before the player request.")
        selection = request.controller
        resolved = resolve_selection(
            selection.player,
            selection.settings,
            selection.binding_sha256,
            selection.checkpoint_sha256,
            ply=len(game.moves),
        )
        choice = choose(game, resolved)
        return PlayResult(
            position=backend.apply(request.snapshot, choice.move, choice.state_hash),
            choice=choice,
            config=resolved.config,
        )

    @app.post("/api/play/session/inspect", response_model=SessionResult)
    def session(request: GameSession) -> SessionResult:
        return SessionResult(session=request, position=backend.inspect(request.snapshot))

    static = Path(__file__).parent / "static"
    if static.is_dir():
        if (static / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{page:path}", include_in_schema=False)
        def frontend(page: str) -> Response:
            if page in ("", "play", "experiments", "reference", "data", "learn/generation", "benchmarks") or (
                page.startswith("experiments/") and len(page.split("/")) == 2
            ):
                return FileResponse(static / "index.html")
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Not found."}})

    return app
