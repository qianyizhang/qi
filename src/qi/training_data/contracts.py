"""Versioned identities, source provenance and reusable teacher-move examples."""

import json
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from qi_game.contracts import Snapshot
from qi_game.core import START_BOARD, GameError
from qi_game.reference import Game, legal_moves, restore

from qi.evaluation import Corpus
from qi.players.policy.encoding import ENCODING, input_key
from qi.teacher import TeacherAnalysis

Phase = Literal["opening", "middlegame", "endgame", "unknown"]
Split = Literal["train", "validation"]
Mode = Literal["random", "teacher-guided"]
PHASE_POLICY = "mobile-material-development-v1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


def fingerprint(kind: str, payload: object) -> str:
    raw = json.dumps({"scheme": kind, "payload": payload}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode()).hexdigest()


def state_fingerprint(snapshot: Snapshot) -> str:
    return fingerprint("replay-state-v1", snapshot.model_dump())


def observation_fingerprint(game: Game) -> str:
    return fingerprint("observation-v1", {"encoding": ENCODING, "board": game.board, "turn": game.turn})


def supervision_spec(analysis: TeacherAnalysis) -> dict:
    # EvalFile is a local locator; the network content hash carries its identity.
    return {
        "target": "legal-teacher-move-v1",
        "authority": "teacher-preference",
        "adapter": analysis.adapter_version,
        "engine_sha256": analysis.engine_sha256,
        "network_sha256": analysis.network_sha256,
        "settings": {k: v for k, v in analysis.settings.items() if k != "EvalFile"},
        "nodes": analysis.requested_nodes,
        "depth": analysis.requested_depth,
    }


def classify_phase(game: Game) -> Phase:
    if game.board.count("K") != 1 or game.board.count("k") != 1:
        return "unknown"
    mobile = sum(piece.upper() in "RNC" for piece in game.board)
    if mobile <= 4:
        return "endgame"
    developed = sum(piece.upper() in "RNC" and piece != START_BOARD[i] for i, piece in enumerate(game.board))
    return "opening" if mobile >= 10 and developed <= 2 else "middlegame"


class StartingPosition(Contract):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    snapshot: Snapshot = Field(default_factory=Snapshot)
    family_id: str | None = None
    themes: list[str] = Field(default_factory=list)
    objective: Literal["win-in-one"] | None = None
    curated_phase: Phase | None = None
    phase_authority: str | None = None

    @model_validator(mode="after")
    def validate_start(self) -> Self:
        if len(set(self.themes)) != len(self.themes) or any(not theme.strip() for theme in self.themes):
            raise ValueError("Starting-position themes must be distinct and nonblank.")
        if restore(self.snapshot).outcome:
            raise ValueError("Starting positions must be replay-backed and nonterminal.")
        if self.snapshot.moves and not self.family_id:
            raise ValueError("A noninitial starting position requires its source family.")
        if (self.curated_phase is None) != (self.phase_authority is None):
            raise ValueError("A curated phase requires an explicit authority, and vice versa.")
        return self


class SamplingWindow(Contract):
    min_ply: int = Field(default=0, ge=0, le=299)
    max_ply: int = Field(default=299, ge=0, le=299)
    stride: int = Field(default=1, ge=1, le=300)
    phases: list[Phase] = Field(default_factory=lambda: ["opening", "middlegame", "endgame", "unknown"])

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.max_ply < self.min_ply or not self.phases:
            raise ValueError("Sampling window must be nonempty.")
        return self

    def matches(self, game: Game, phase: Phase) -> bool:
        ply = len(game.moves)
        return self.min_ply <= ply <= self.max_ply and (ply - self.min_ply) % self.stride == 0 and phase in self.phases


class SourcePlan(Contract):
    id: str = Field(min_length=1)
    mode: Mode
    split: Split
    start: StartingPosition
    games: int = Field(default=1, ge=1, le=2048)
    additional_plies: int = Field(default=32, ge=1, le=300)
    samples: int = Field(default=8, ge=1, le=16)
    window: SamplingWindow = Field(default_factory=SamplingWindow)


class GenerationRecipe(Contract):
    id: str = Field(min_length=1)
    version: Literal["continuations-v1", "continuations-v2"] = "continuations-v2"
    phase_policy: Literal[PHASE_POLICY] = PHASE_POLICY
    seed: int = 7
    seconds: float = Field(default=300, gt=0, le=7200)
    sources: list[SourcePlan] = Field(min_length=1)

    def require_current(self) -> None:
        if self.version != "continuations-v2":
            raise GameError(
                "obsolete_recipe", "Use continuations-v2 for generation; v1 remains readable in saved libraries."
            )

    @model_validator(mode="after")
    def validate_recipe(self) -> Self:
        if len({s.id for s in self.sources}) != len(self.sources) or sum(s.games for s in self.sources) > 2048:
            raise ValueError("Source plan IDs must be unique; at most 2048 games.")
        families, starts = {}, {}
        for source in self.sources:
            family = source.start.family_id
            if family and families.setdefault(family, source.split) != source.split:
                raise ValueError("A source family cannot cross splits.")
            if source.start.snapshot.moves:
                key = state_fingerprint(source.start.snapshot)
                if starts.setdefault(key, family) != family:
                    raise ValueError("Reusing a noninitial starting position cannot mint another family.")
        return self


class Source(Contract):
    id: str
    family_id: str
    plan_id: str
    snapshot: Snapshot
    actor_spec: dict
    stop_reason: Literal["terminal", "ply-budget", "deadline", "error"]


class Example(Contract):
    analysis: TeacherAnalysis
    source_ids: list[str] = Field(min_length=1)

    @property
    def state_fingerprint(self) -> str:
        return state_fingerprint(self.analysis.snapshot)

    @property
    def observation_fingerprint(self) -> str:
        return observation_fingerprint(restore(self.analysis.snapshot))

    @property
    def supervision_fingerprint(self) -> str:
        return fingerprint("supervision-v1", supervision_spec(self.analysis))

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            "example-v1",
            {
                "state": self.state_fingerprint,
                "supervision": supervision_spec(self.analysis),
                "target": self.analysis.move,
            },
        )

    @model_validator(mode="after")
    def validate_example(self) -> Self:
        game = restore(self.analysis.snapshot)
        if game.outcome or self.analysis.move not in legal_moves(game.board, game.turn):
            raise ValueError("Example requires a legal teacher move in a nonterminal state.")
        if self.analysis.state_hash != game.state_hash or len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Example state or source identity is invalid.")
        return self


def example_phase(example: Example, plan: SourcePlan) -> Phase:
    if example.analysis.snapshot == plan.start.snapshot and plan.start.curated_phase is not None:
        return plan.start.curated_phase
    return classify_phase(restore(example.analysis.snapshot))


def satisfies_objective(game: Game, move: str, objective: str | None) -> bool:
    if objective is None:
        return True
    outcome = game.apply(move).outcome
    return outcome is not None and outcome.winner == game.turn


class Library(Contract):
    schema_version: Literal["example-library-v1"] = "example-library-v1"
    recipe: GenerationRecipe
    reserved_corpus: Corpus
    sources: list[Source] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)
    status: Literal["complete", "incomplete"] = "incomplete"
    failure: str | None = None

    @model_validator(mode="after")
    def validate_library(self) -> Self:
        sources = {s.id: s for s in self.sources}
        plans = {p.id: p for p in self.recipe.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Source IDs must be unique.")
        families = {}
        starts = {}
        source_counts = {plan.id: 0 for plan in self.recipe.sources}
        sample_states = {sid: set() for sid in sources}
        for source in self.sources:
            if source.plan_id not in plans:
                raise ValueError("Unknown source plan.")
            plan = plans[source.plan_id]
            source_counts[plan.id] += 1
            if source_counts[plan.id] > plan.games:
                raise ValueError("Source count exceeds its generation plan.")
            moves = source.snapshot.moves
            if moves[: len(plan.start.snapshot.moves)] != plan.start.snapshot.moves:
                raise ValueError("Source must continue its declared starting position.")
            game = restore(source.snapshot)
            if len(moves) - len(plan.start.snapshot.moves) > plan.additional_plies:
                raise ValueError("Source exceeds its additional-ply budget.")
            if source.family_id != (plan.start.family_id or source.id):
                raise ValueError("Source family differs from its declared lineage.")
            if families.setdefault(source.family_id, plan.split) != plan.split:
                raise ValueError("A source family cannot cross splits.")
            if plan.start.snapshot.moves:
                key = state_fingerprint(plan.start.snapshot)
                if starts.setdefault(key, source.family_id) != source.family_id:
                    raise ValueError("Reusing a noninitial starting position cannot mint another family.")
            if (
                source.stop_reason == "ply-budget"
                and len(moves) - len(plan.start.snapshot.moves) != plan.additional_plies
            ):
                raise ValueError("A ply-budget cutoff must exhaust its additional-ply allowance.")
            if (source.stop_reason == "terminal") != bool(game.outcome):
                raise ValueError("Only a referee terminal result terminates a game.")
        seen = set()
        for example in self.examples:
            if example.fingerprint in seen:
                raise ValueError("Identical examples must merge contributing source IDs.")
            seen.add(example.fingerprint)
            for source_id in example.source_ids:
                if source_id not in sources:
                    raise ValueError("Unknown example source.")
                source = sources[source_id]
                plan = plans[source.plan_id]
                sample_states[source_id].add(example.state_fingerprint)
                if len(sample_states[source_id]) > plan.samples:
                    raise ValueError("Example count exceeds its source sample budget.")
                moves = example.analysis.snapshot.moves
                if (
                    len(moves) < len(plan.start.snapshot.moves)
                    or len(moves) > len(source.snapshot.moves)
                    or source.snapshot.moves[: len(moves)] != moves
                ):
                    raise ValueError("Example is outside its source continuation.")
                game = restore(example.analysis.snapshot)
                if not plan.window.matches(game, example_phase(example, plan)):
                    raise ValueError("Example does not satisfy its sampling window.")
                if not satisfies_objective(game, example.analysis.move, plan.start.objective):
                    raise ValueError("Teacher move does not satisfy the declared immediate-win objective.")
        if self.status == "complete" and (
            self.failure
            or len(self.sources) != sum(p.games for p in self.recipe.sources)
            or any(s.stop_reason in {"deadline", "error"} for s in self.sources)
        ):
            raise ValueError("Incomplete generation cannot claim completion.")
        return self

    @property
    def example_index(self) -> dict[str, Example]:
        return {example.fingerprint: example for example in self.examples}

    def identities(self) -> list[dict]:
        return [
            {
                "example": e.fingerprint,
                "state": e.state_fingerprint,
                "observation": e.observation_fingerprint,
                "supervision": e.supervision_fingerprint,
                "input_sha256": input_key(restore(e.analysis.snapshot)),
            }
            for e in self.examples
        ]
