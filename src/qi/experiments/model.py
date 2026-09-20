"""Explicit, bounded search matrices and code identity."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from qi_game.reference import legal_moves, restore

from qi.artifacts import ROOT, digest, provenance
from qi.evaluation import Corpus
from qi.players import PlayerConfig
from qi.players.catalog import PLAYERS
from qi.players.core import config_data

__all__ = ["ROOT", "Plan", "digest", "provenance"]


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=1, max_length=2000)
    corpus: Corpus
    players: list[str] = Field(min_length=1, max_length=16)
    budgets: list[int] = Field(min_length=1, max_length=6)
    seeds: list[int] = Field(default_factory=lambda: [7], min_length=1, max_length=8)
    depth: int = Field(default=3, ge=1, le=8)
    rollout_plies: int = Field(default=8, ge=0, le=64)
    pairs: list[tuple[str, str]] = Field(default_factory=list, max_length=16)
    game_openings: list[str] = Field(default_factory=list, max_length=32)
    winning_moves: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_matrix(self) -> Self:
        for values in (self.players, self.budgets, self.seeds, self.game_openings, self.pairs):
            if len(set(values)) != len(values):
                raise ValueError("Matrix axes must not contain duplicates.")
        if len(self.corpus.openings) > 64 or not all(1 <= value <= 100_000 for value in self.budgets):
            raise ValueError("Use at most 64 positions and budgets of 1-100000 visits.")
        if not all(0 <= value <= 2_147_483_000 for value in self.seeds):
            raise ValueError("Seeds must be nonnegative bounded integers.")
        for player in self.players:
            if player not in PLAYERS or not PLAYERS[player].info.uses_search or player == "pikafish":
                raise ValueError("This experiment format supports search players only.")
        if any(a not in self.players or b not in self.players or a == b for a, b in self.pairs):
            raise ValueError("Pairs must name two distinct matrix players.")
        openings = {entry.id: entry for entry in self.corpus.openings}
        if set(self.game_openings) - openings.keys() or self.winning_moves.keys() - openings.keys():
            raise ValueError("Unknown corpus position.")
        if bool(self.pairs) != bool(self.game_openings):
            raise ValueError("Paired games need both pairs and game openings.")
        for key, expected in self.winning_moves.items():
            game = restore(openings[key].snapshot)
            actual = [
                move
                for move in legal_moves(game.board, game.turn)
                if (outcome := game.apply(move).outcome) and outcome.winner == game.turn
            ]
            if not expected or len(set(expected)) != len(expected) or set(expected) != set(actual):
                raise ValueError("Tactical targets must contain every referee-proven immediate win.")
        if len(self.jobs()) > 20_000:
            raise ValueError("Experiment exceeds 20000 units.")
        return self

    def jobs(self) -> list[dict]:
        jobs = []

        def config(player, seed, nodes):
            return config_data(PlayerConfig(player, seed, self.depth, nodes, rollout_plies=self.rollout_plies))

        for nodes in self.budgets:
            for opening in self.corpus.openings:
                for seed in self.seeds:
                    for player in self.players:
                        jobs.append({"kind": "probe", "opening": opening.id, "a": config(player, seed, nodes)})
        for nodes in self.budgets:
            for seed in self.seeds:
                for opening in self.game_openings:
                    for a, b in self.pairs:
                        for side in ("red", "black"):
                            jobs.append(
                                {
                                    "kind": "game",
                                    "opening": opening,
                                    "a": config(a, seed, nodes),
                                    "b": config(b, seed + 1, nodes),
                                    "a_side": side,
                                }
                            )
        return [{"id": f"unit-{index:05d}", **job} for index, job in enumerate(jobs)]

    def preview(self) -> dict:
        jobs = self.jobs()
        return {
            "name": self.name,
            "question": self.question,
            "plan_sha256": digest(self.model_dump(mode="json")),
            "corpus_sha256": self.corpus.digest,
            "positions": len(self.corpus.openings),
            "probes": sum(job["kind"] == "probe" for job in jobs),
            "games": sum(job["kind"] == "game" for job in jobs),
            "players": self.players,
            "node_budgets": self.budgets,
            "seeds": self.seeds,
            "depth": self.depth,
            "rollout_plies": self.rollout_plies,
            "order": "probes by budget/position/seed/player, then paired games; deadline may leave a partial matrix",
            "timing": "untraced wall time per decision; equal visits are not equal compute",
        }
