"""HTTP routes for generated collection inspection; no collection mutations."""

from typing import Literal

from fastapi import FastAPI, Query
from qi_game.contracts import Position

from qi.collection_view import (
    CollectionCatalog,
    CollectionPage,
    CollectionQuality,
    GeneratedGameDetail,
    analysis_evidence,
    collection_page,
    collection_quality,
    discover_collections,
    game_detail,
    game_position,
)
from qi.training_data.store import AnalysisPayload


def register_collections(app: FastAPI) -> None:
    @app.get("/api/collections", response_model=CollectionCatalog)
    def collections() -> CollectionCatalog:
        return discover_collections()

    @app.get("/api/collections/{collection_id}", response_model=CollectionPage)
    def view(
        collection_id: str,
        run: int = Query(default=0, ge=0),
        policy: str = "",
        split: str = "",
        disposition: str = "",
        outcome: str = "",
        q: str = Query(default="", max_length=100),
        phase: Literal["", "opening", "middlegame", "endgame", "unknown"] = "",
        lens: Literal["all", "shortfall", "long"] = "all",
        sort: Literal["newest", "longest", "shortfall"] = "newest",
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=30, ge=1, le=100),
        attempts: str = Query(default="", max_length=40000),
    ) -> CollectionPage:
        return collection_page(
            collection_id,
            run=run,
            policy=policy,
            split=split,
            disposition=disposition,
            outcome=outcome,
            q=q,
            lens=lens,
            phase=phase,
            sort=sort,
            offset=offset,
            limit=limit,
            attempts=attempts,
        )

    @app.get("/api/collections/{collection_id}/quality", response_model=CollectionQuality)
    def quality(collection_id: str) -> CollectionQuality:
        return collection_quality(collection_id)

    @app.get("/api/collections/{collection_id}/games/{game_id}", response_model=GeneratedGameDetail)
    def game(collection_id: str, game_id: int) -> GeneratedGameDetail:
        return game_detail(collection_id, game_id)

    @app.get("/api/collections/{collection_id}/games/{game_id}/position", response_model=Position)
    def position(collection_id: str, game_id: int, ply: int = Query(default=0, ge=0, le=300)) -> Position:
        return game_position(collection_id, game_id, ply)

    @app.get("/api/collections/{collection_id}/games/{game_id}/analyses/{analysis_id}", response_model=AnalysisPayload)
    def evidence(collection_id: str, game_id: int, analysis_id: int) -> AnalysisPayload:
        return analysis_evidence(collection_id, game_id, analysis_id)
