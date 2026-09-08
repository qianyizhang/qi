"""Local stateless adapter; the referee owns all game behavior."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qi.game import Game, GameError
from qi.players import PlayerConfig, PlayerInfo, choose, list_players
from qi.protocol import ApplyRequest, InspectRequest, OpponentRequest, OpponentResult, Position, inspect


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

    static = Path(__file__).parent / "static"
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="board")
    return app
