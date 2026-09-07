"""Local stateless adapter; the referee owns all game behavior."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qi.game import Game, GameError
from qi.protocol import ApplyRequest, InspectRequest, Position, inspect


def create_app() -> FastAPI:
    app = FastAPI(title="Qi local referee", version="0.1.0")

    @app.exception_handler(GameError)
    async def game_error(request: Request, exc: GameError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"error": {"code": exc.code, "message": str(exc)}})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_request", "message": "Request does not match the game schema."}},
        )

    @app.post("/api/new", response_model=Position)
    def new() -> Position:
        return inspect(Game())

    @app.post("/api/inspect", response_model=Position)
    def position(request: InspectRequest) -> Position:
        return inspect(request.snapshot.game())

    @app.post("/api/apply", response_model=Position)
    def apply(request: ApplyRequest) -> Position:
        return inspect(request.snapshot.game().apply(request.move, request.expected_state_hash))

    static = Path(__file__).parent / "static"
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="board")
    return app
