"""Replayable teacher labels, source-game splits, and observation-level exclusions."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from random import Random
from time import monotonic
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qi.evaluation import Corpus
from qi.game import Game, GameError, legal_moves
from qi.players.policy.encoding import ENCODING, input_key
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig, analyze

MAX_SOURCES = 2048
MAX_LABELS = MAX_SOURCES * 16


class SourceGame(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    split: Literal["train", "validation"]
    snapshot: Snapshot


class Label(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_id: str
    input_sha256: str
    analysis: TeacherAnalysis


def reserved_inputs(corpus: Corpus) -> set[str]:
    keys = set()
    for opening in corpus.openings:
        game = Game()
        keys.add(input_key(game))
        for move in opening.snapshot.moves:
            game = game.apply(move)
            keys.add(input_key(game))
    return keys


def teacher_identity(analysis: TeacherAnalysis) -> tuple:
    return (
        analysis.adapter_version,
        analysis.engine_name,
        analysis.engine_sha256,
        analysis.network_sha256,
        tuple(sorted(analysis.settings.items())),
        analysis.requested_nodes,
        analysis.requested_depth,
    )


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    encoding: Literal[ENCODING] = ENCODING
    generator: Literal["seeded-random-trajectories-v1"] = "seeded-random-trajectories-v1"
    seed: int
    reserved_corpus: Corpus
    sources: list[SourceGame] = Field(min_length=2, max_length=MAX_SOURCES)
    labels: list[Label] = Field(min_length=2, max_length=MAX_LABELS)

    @model_validator(mode="after")
    def validate_data(self) -> Self:
        sources = {source.id: source for source in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Source IDs must be unique.")
        histories = set()
        for source in self.sources:
            game = source.snapshot.game()
            if game.state_hash in histories:
                raise ValueError("Source trajectories must be distinct.")
            histories.add(game.state_hash)
        seen = reserved_inputs(self.reserved_corpus)
        splits = set()
        identity = None
        for label in self.labels:
            source = sources.get(label.source_id)
            if source is None:
                raise ValueError("Label references an unknown source game.")
            analysis = label.analysis
            moves = analysis.snapshot.moves
            if source.snapshot.moves[: len(moves)] != moves or len(moves) > len(source.snapshot.moves):
                raise ValueError("Label history must be a prefix of its source game.")
            game = analysis.snapshot.game()
            if game.outcome or analysis.move not in legal_moves(game.board, game.turn):
                raise ValueError("Teacher label must be legal in a nonterminal position.")
            key = input_key(game)
            if analysis.state_hash != game.state_hash or label.input_sha256 != key:
                raise ValueError("Label identity does not agree with replay.")
            if key in seen:
                raise ValueError("Duplicate or reserved model input.")
            seen.add(key)
            current = teacher_identity(analysis)
            if identity is not None and identity != current:
                raise ValueError("A dataset must use one teacher identity and search configuration.")
            identity = current
            splits.add(source.split)
        if splits != {"train", "validation"}:
            raise ValueError("Both source-game splits need labels.")
        return self

    @property
    def digest(self) -> str:
        return sha256(self.model_dump_json().encode()).hexdigest()

    def split_labels(self, split: Literal["train", "validation"]) -> list[Label]:
        ids = {source.id for source in self.sources if source.split == split}
        return [label for label in self.labels if label.source_id in ids]


def generate(
    corpus: Corpus,
    teacher: TeacherConfig,
    *,
    seed: int = 7,
    games: int = 16,
    plies: int = 32,
    samples: int = 8,
    seconds: float = 300,
    workers: int = 1,
    labeler: Callable[[Game, TeacherConfig], TeacherAnalysis] = analyze,
) -> Dataset:
    if (
        not 4 <= games <= MAX_SOURCES
        or not 2 <= plies <= 100
        or not 1 <= samples <= 16
        or not 0 < seconds <= 7200
        or not 1 <= workers <= 4
    ):
        raise GameError(
            "invalid_budget", "Use 4-2048 games, 2-100 plies, 1-16 samples/game, 1-4 workers, and at most 7200 seconds."
        )
    rng = Random(seed)
    validation_ids = set(rng.sample(range(games), max(1, games // 4)))
    seen = reserved_inputs(corpus)
    sources, labels = [], []
    deadline = monotonic() + seconds

    def query(candidate: Game) -> TeacherAnalysis:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GameError("dataset_timeout", "Dataset generation exceeded its deadline; no dataset emitted.")
        return labeler(candidate, replace(teacher, timeout_seconds=min(teacher.timeout_seconds, remaining)))

    # Executor.map preserves seeded selection order regardless of engine completion order.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for index in range(games):
            game = Game()
            candidates = []
            for _ in range(plies):
                if monotonic() >= deadline:
                    raise GameError("dataset_timeout", "Dataset generation exceeded its deadline; no dataset emitted.")
                if game.outcome:
                    break
                if input_key(game) not in seen:
                    candidates.append(game)
                game = game.apply(rng.choice(sorted(legal_moves(game.board, game.turn))))
            source_id = f"game-{index:03d}"
            sources.append(
                SourceGame(
                    id=source_id,
                    split="validation" if index in validation_ids else "train",
                    snapshot=Snapshot(moves=list(game.moves)),
                )
            )
            rng.shuffle(candidates)
            selected = []
            for candidate in candidates:
                key = input_key(candidate)
                if key in seen:
                    continue
                selected.append(candidate)
                seen.add(key)
                if len(selected) == samples:
                    break
            for candidate, result in zip(selected, executor.map(query, selected), strict=True):
                labels.append(Label(source_id=source_id, input_sha256=input_key(candidate), analysis=result))
            if monotonic() >= deadline:
                raise GameError("dataset_timeout", "Dataset generation exceeded its deadline; no dataset emitted.")
    return Dataset(seed=seed, reserved_corpus=corpus, sources=sources, labels=labels)
