"""Pure, versioned scoring of planned color pairs from validated game evidence."""

from collections import defaultdict
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from qi_game.core import Side


class GameScore(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    pair_id: str
    a_side: Side
    status: Literal["pending", "running", "complete", "incomplete", "failed"]
    result: Literal["win", "draw", "loss"] | None = None
    decisions: int = Field(default=0, ge=0)
    elapsed_ms: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def outcome_requires_completion(self) -> Self:
        if (self.status == "complete") != (self.result is not None):
            raise ValueError("Only completed games must have a result.")
        return self


class PairedScore(BaseModel):
    scorer: Literal["game-score-v1"] = "game-score-v1"
    planned_pairs: int
    completed_pairs: int
    completed_games: int
    failed_games: int
    incomplete_games: int
    unpaired_completed_games: int
    wins: int
    draws: int
    losses: int
    score_rate: float | None
    decisions: int
    mean_elapsed_ms: float | None


def score_pairs(games: list[GameScore]) -> PairedScore:
    """Score complete pairs only; callers supply every planned game slot."""
    pairs: dict[str, list[GameScore]] = defaultdict(list)
    for game in games:
        game = GameScore.model_validate(game.model_dump())
        pairs[game.pair_id].append(game)
    scored = []
    for pair in pairs.values():
        if len(pair) != 2 or {game.a_side for game in pair} != {"red", "black"}:
            raise ValueError("Each planned pair must contain exactly both color assignments.")
        if all(game.status == "complete" for game in pair):
            scored.extend(pair)
    wins = sum(game.result == "win" for game in scored)
    draws = sum(game.result == "draw" for game in scored)
    completed = sum(game.status == "complete" for game in games)
    failed = sum(game.status == "failed" for game in games)
    decisions = sum(game.decisions for game in scored)
    return PairedScore(
        planned_pairs=len(pairs),
        completed_pairs=len(scored) // 2,
        completed_games=completed,
        failed_games=failed,
        incomplete_games=len(games) - completed - failed,
        unpaired_completed_games=completed - len(scored),
        wins=wins,
        draws=draws,
        losses=len(scored) - wins - draws,
        score_rate=(wins + 0.5 * draws) / len(scored) if scored else None,
        decisions=decisions,
        mean_elapsed_ms=sum(game.elapsed_ms for game in scored) / decisions if decisions else None,
    )
