"""Replay-backed teaching projections; no collection writes or teacher execution."""

from functools import lru_cache
from pathlib import Path
from random import Random

from fastapi import FastAPI, Query
from pydantic import BaseModel
from qi_game.contracts import Position, Snapshot
from qi_game.core import START_BOARD
from qi_game.reference import Game, inspect, restore

from qi.teacher import TeacherScore
from qi.training_data.contracts import PHASE_POLICY, Phase, classify_phase
from qi.training_data.generation_policies import ActorPolicy, SamplingPolicy, SamplingResult, sample_positions


class LessonAnalysis(BaseModel):
    ply: int
    analysis_id: int
    nodes: int
    move: str
    score: TeacherScore
    spec_id: str


class LessonBatch(BaseModel):
    attempts: int
    accepted: int
    rejected: int
    endgame_shortfall_games: int
    shared_inputs: int
    observed_at: float


class LessonExample(BaseModel):
    collection: str
    captured: str
    game_id: int
    attempt: str
    trajectory: str
    snapshot: Snapshot
    actor: ActorPolicy
    intervention_ply: int
    sampling_policy: SamplingPolicy
    sampling: SamplingResult
    analyses: list[LessonAnalysis]
    duplicate_games: list[int]
    batch: LessonBatch


class LessonFrame(BaseModel):
    position: Position
    phase: Phase
    mobile: int
    developed: int


class GenerationLesson(BaseModel):
    example: LessonExample
    phase_policy: str
    frames: list[LessonFrame]


@lru_cache(maxsize=1)
def generation_lesson() -> GenerationLesson:
    example = LessonExample.model_validate_json(Path(__file__).with_name("generation_lesson_example.json").read_text())
    frames = []
    game = Game()
    for ply in range(len(example.snapshot.moves) + 1):
        if ply:
            game = game.apply(example.snapshot.moves[ply - 1], game.state_hash)
        frames.append(
            LessonFrame(
                position=inspect(game),
                phase=classify_phase(game),
                mobile=sum(p.upper() in "RNC" for p in game.board),
                developed=sum(p.upper() in "RNC" and p != START_BOARD[i] for i, p in enumerate(game.board)),
            )
        )
    return GenerationLesson(example=example, phase_policy=PHASE_POLICY, frames=frames)


@lru_cache(maxsize=64)
def practice_sampling(spacing: int, seed: int) -> SamplingResult:
    lesson = generation_lesson()
    policy = lesson.example.sampling_policy.model_copy(update={"min_spacing": spacing})
    # Use the same Python sampler as generation, on this fixed replay only.
    games = [restore(frame.position.snapshot) for frame in lesson.frames]
    return sample_positions(games, policy, Random(seed))


def register_generation_lesson(app: FastAPI) -> None:
    @app.get("/api/learn/generation", response_model=GenerationLesson)
    def lesson() -> GenerationLesson:
        return generation_lesson()

    @app.get("/api/learn/generation/sampling", response_model=SamplingResult)
    def sampling(
        spacing: int = Query(default=4, ge=1, le=8), seed: int = Query(default=7, ge=0, le=31)
    ) -> SamplingResult:
        return practice_sampling(spacing, seed)
