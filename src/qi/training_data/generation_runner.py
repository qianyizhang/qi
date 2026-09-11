"""Incremental, reproducible actor-policy generation with independent supervision."""

from collections import Counter
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from pathlib import Path
from random import Random
from tempfile import TemporaryFile
from time import monotonic
from typing import Literal, Self

from pydantic import Field, model_validator

from qi.artifacts import provenance
from qi.evaluation import Corpus
from qi.game import Game, GameError, legal_moves
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity, TeacherSession
from qi.training_data.candidate_evidence import parse_candidates
from qi.training_data.contracts import Contract, Example, StartingPosition, fingerprint, state_fingerprint
from qi.training_data.generation_io import CollectionIO, analysis_spec
from qi.training_data.generation_policies import (
    ActorDecision,
    ActorPolicy,
    SamplingPolicy,
    choose_plausible,
    sample_positions,
)
from qi.training_data.store import AnalysisSpec, Collection, GamePayload, RunPayload, TrajectorySplitConflict
from qi.training_data.v1 import reserved_inputs


class GenerationTeacher(Contract):
    engine: str
    network: str
    engine_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    network_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    threads: int = Field(default=1, ge=1, le=16, strict=True)
    nodes: int = Field(ge=1)
    depth: int | None = Field(default=None, ge=1, le=64)
    timeout_seconds: float = Field(default=10.0, gt=0, le=120)

    def config(self) -> TeacherConfig:
        return TeacherConfig(
            Path(self.engine), Path(self.network), self.nodes, self.depth, self.timeout_seconds, threads=self.threads
        )


class GenerationSource(Contract):
    id: str = Field(min_length=1)
    games: int = Field(ge=1, le=1_000_000)
    split: Literal["train", "validation"]
    start: StartingPosition = Field(default_factory=lambda: StartingPosition(id="standard", version="1"))
    parent_trajectory: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    actor: ActorPolicy = Field(default_factory=ActorPolicy)
    additional_plies: int = Field(ge=1, le=300)
    sampling: SamplingPolicy = Field(default_factory=SamplingPolicy)

    @model_validator(mode="after")
    def horizon(self) -> Self:
        if len(self.start.snapshot.moves) + self.additional_plies > 300:
            raise ValueError("Absolute continuation horizon must not exceed the referee's 300-ply ceiling.")
        if self.parent_trajectory is not None and not self.start.snapshot.moves:
            raise ValueError("A generated child must start at a noninitial parent prefix.")
        if self.start.curated_phase is not None or self.start.objective is not None:
            raise ValueError("Policy generation currently uses computed phase and unrestricted teacher-move targets.")
        if self.actor.mode == "intervention":
            lo = max(len(self.start.snapshot.moves), self.actor.intervention_min_ply)
            hi = min(len(self.start.snapshot.moves) + self.additional_plies - 1, self.actor.intervention_max_ply)
            if lo > hi:
                raise ValueError("Intervention window does not intersect this continuation.")
        return self


class PolicyGenerationConfig(Contract):
    schema_version: Literal["generation-policy-run-v1"] = "generation-policy-run-v1"
    name: str = Field(min_length=1)
    seed: int = 7
    seconds: float = Field(gt=0, le=43_200)
    corpus: Corpus
    teachers: dict[str, GenerationTeacher]
    actor_teacher: str
    supervision: list[str] = Field(min_length=1)
    actor_audit_every: int = Field(default=16, ge=1, le=300)
    sources: list[GenerationSource] = Field(min_length=1)

    @model_validator(mode="after")
    def references(self) -> Self:
        if self.actor_teacher not in self.teachers or not set(self.supervision) <= self.teachers.keys():
            raise ValueError("Actor and supervision names must reference configured teachers.")
        if len(set(self.supervision)) != len(self.supervision) or len({s.id for s in self.sources}) != len(
            self.sources
        ):
            raise ValueError("Supervision and source names must be distinct.")
        families, starts = {}, {}
        for source in self.sources:
            if source.start.family_id:
                family = source.start.family_id
                if families.setdefault(family, source.split) != source.split:
                    raise ValueError("A source family cannot cross splits.")
            if source.start.snapshot.moves:
                state = state_fingerprint(source.start.snapshot)
                if starts.setdefault(state, source.start.family_id) != source.start.family_id:
                    raise ValueError("The same noninitial start cannot mint a different family.")
        return self

    def resolve(self, base: Path) -> "PolicyGenerationConfig":
        resolved = self.model_copy(deep=True)
        for teacher in resolved.teachers.values():
            teacher.engine = str((base / teacher.engine).resolve())
            teacher.network = str((base / teacher.network).resolve())
        return resolved


class SessionProvider(AbstractContextManager):
    """Reuse pinned engines; a failed session is replaced before the explicit retry."""

    def __init__(self, identities: dict[tuple[str, str], TeacherIdentity]):
        self.identities, self.sessions = identities, {}

    def __call__(self, game: Game, config: TeacherConfig) -> TeacherAnalysis:
        key = (str(config.engine.resolve()), str(config.network.resolve()))
        if key not in self.sessions:
            self.sessions[key] = TeacherSession(config, identity=self.identities[key])
        try:
            return self.sessions[key].analyze(game, config)
        except BaseException:
            self.sessions.pop(key).close()
            raise

    def __exit__(self, *args):
        for session in self.sessions.values():
            session.close()
        self.sessions.clear()


def pin_teachers(config: PolicyGenerationConfig) -> dict[tuple[str, str], TeacherIdentity]:
    identities = {}
    for teacher in config.teachers.values():
        settings = teacher.config()
        key = (str(settings.engine.resolve()), str(settings.network.resolve()))
        identity = identities.setdefault(key, None)
        if identity is None:
            identity = identities[key] = TeacherIdentity.read(settings)
        if (identity.engine_sha256, identity.network_sha256) != (teacher.engine_sha256, teacher.network_sha256):
            raise GameError("teacher_mismatch", "Teacher assets differ from the pinned recipe.")
    return identities


def generate_policies(
    store: Collection,
    config: PolicyGenerationConfig,
    *,
    provider: Callable[[Game, TeacherConfig], TeacherAnalysis] | None = None,
    event: Callable[[dict], None] | None = None,
    clock: Callable[[], float] = monotonic,
    continue_from_run: int | None = None,
) -> dict:
    """Generate complete games incrementally; retain quotas/shortfalls independently.

    Each game has independent actor/intervention/sampler RNG streams. Changing
    sample quotas or requested game count does not change its actor trajectory.
    Raw actor evidence is spooled per game, then only selected/audited records are
    persisted. Failed attempts are always retained. Memory does not grow with the
    number of source games.
    """
    config = PolicyGenerationConfig.model_validate(config.model_dump())
    identities = pin_teachers(config)
    if provider is None:
        with SessionProvider(identities) as live:
            return _generate(store, config, live, identities, event, clock, continue_from_run)
    return _generate(store, config, provider, identities, event, clock, continue_from_run)


def _generate(store, config, provider, identities, event, clock, continue_from_run):
    io = CollectionIO(store)
    inherited = io.continuation(continue_from_run, config.model_dump())
    origin = provenance()
    run = store.run(
        RunPayload(
            config={
                "recipe": config.model_dump(),
                "implementation_sha256": origin["source_sha256"],
                "continued_from_run": continue_from_run,
                "inherited_games": inherited,
            },
            provenance=origin,
            seed=config.seed,
            planned_games=sum(s.games for s in config.sources) - len(inherited),
        )
    )
    store.run_status(run, "running")
    started, active_game = clock(), None
    deadline = started + config.seconds
    excluded = reserved_inputs(config.corpus)
    counters = Counter()
    phases, shortfalls = Counter(), Counter()
    game_count, reused_games, rejected_games, reused_rejections = 0, 0, 0, 0
    inherited_pending = set(inherited)
    before = Counter()
    querying_actor = False

    def query(game, settings, *, game_id, retain, role, metadata=None):
        if clock() + settings.timeout_seconds > deadline:
            raise GameError("dataset_timeout", "Insufficient time for the pinned query timeout.")
        key = (str(settings.engine.resolve()), str(settings.network.resolve()))
        expected = analysis_spec(settings, identities[key])
        occurrence = io.occurrence(game_id, Snapshot(moves=list(game.moves)), metadata=metadata) if retain else None
        if occurrence is not None:
            saved = io.success(occurrence, expected)
            if saved is not None:
                return saved
        for retry in range(2):
            if clock() + settings.timeout_seconds > deadline:
                raise GameError("dataset_timeout", "Insufficient time for retry under the pinned timeout.")
            attempt = store.begin_analysis(occurrence, store.spec(expected)) if occurrence is not None else None
            answer = None
            tick = clock()
            counters[f"{role}_attempts"] += 1
            try:
                answer = provider(game, settings)
                if (
                    answer.snapshot != Snapshot(moves=list(game.moves))
                    or AnalysisSpec.from_analysis(answer) != expected
                ):
                    raise GameError("invalid_supervision", "Teacher answer differs from the exact state/specification.")
                Example(analysis=answer, source_ids=["policy-runner"])
                parse_candidates(answer)
                if attempt is not None:
                    store.finish_analysis(attempt, answer)
                counters[f"{role}_reported_nodes"] += answer.reported_nodes or 0
                counters[f"{role}_successes"] += 1
                return answer
            except BaseException as exc:
                if occurrence is None:
                    occurrence = io.occurrence(game_id, Snapshot(moves=list(game.moves)), metadata=metadata)
                if attempt is None:
                    attempt = store.begin_analysis(occurrence, store.spec(expected))
                store.finish_analysis(
                    attempt,
                    failure=f"{type(exc).__name__}: {exc}",
                    raw=[answer.model_dump_json()] if answer is not None else [],
                )
                counters["failures"] += 1
                transient = isinstance(exc, GameError) and exc.code in {"teacher_timeout", "teacher_exit"}
                if not transient or retry == 1:
                    raise
                counters["retries"] += 1
            finally:
                counters[f"{role}_seconds"] += clock() - tick

    try:
        for source in config.sources:
            io.validate_parent(source, excluded)
            for index in range(source.games):
                if clock() >= deadline:
                    raise GameError("dataset_timeout", "Generation allowance exhausted.")
                actor_identity = {
                    "version": "policy-actor-v1",
                    "seed": config.seed,
                    "source": source.id,
                    "index": index,
                    "start": state_fingerprint(source.start.snapshot),
                    "policy": source.actor.model_dump(),
                    "parent_trajectory": source.parent_trajectory,
                    "teacher": (
                        None
                        if source.actor.mode == "random"
                        else config.teachers[config.actor_teacher].model_dump(exclude={"engine", "network"})
                    ),
                }
                key = fingerprint("policy-source-v1", actor_identity | {"plies": source.additional_plies})
                payload = GamePayload(
                    source_id=key,
                    family=source.start.family_id or key,
                    split=source.split,
                    mode="random" if source.actor.mode == "random" else "teacher-guided",
                    initial=source.start.snapshot,
                    snapshot=source.start.snapshot,
                    actor=actor_identity,
                    parent_digest=source.parent_trajectory,
                    themes=[*source.start.themes, f"policy:{source.actor.mode}"],
                )
                inherited_id = inherited.get(key)
                if inherited_id is not None:
                    saved = store.game(inherited_id)
                    if saved.source_id != key or saved.split != payload.split or saved.family != payload.family:
                        raise ValueError("Inherited source identity differs from the frozen plan.")
                    inherited_pending.remove(key)
                rejected_id = io.rejected_game(run, key)
                if inherited_id is not None:
                    status = store.db.execute("SELECT status FROM games WHERE id=?", (inherited_id,)).fetchone()[0]
                    if status != "complete":
                        rejected_id = inherited_id
                if rejected_id is not None:
                    rejected_games += 1
                    reused_rejections += 1
                    if event:
                        event(
                            {
                                "kind": "reused-rejection",
                                "game_id": rejected_id,
                                "result": store.game(rejected_id).actor["generation_result"],
                            }
                        )
                    continue
                game_id = None if inherited_id is not None else store.begin_game(run, key, payload)
                if game_id is None:
                    game_id = inherited_id or io.completed_game(run, key)
                    previous = store.game(game_id).actor["generation_result"]
                    phases.update(previous["sampling"]["actual"])
                    shortfalls.update(previous["sampling"]["shortfall"])
                    game_count += 1
                    reused_games += 1
                    if event:
                        event({"kind": "reused-game", "game_id": game_id, "result": previous})
                    continue
                active_game = game_id
                rng = Random(fingerprint("policy-moves-v1", actor_identity))
                sampler = Random(fingerprint("policy-sampling-v1", actor_identity))
                intervention_rng = Random(fingerprint("policy-intervention-v1", actor_identity))
                game = source.start.snapshot.game()
                intervention_at = None
                if source.actor.mode == "intervention":
                    lo = max(len(game.moves), source.actor.intervention_min_ply)
                    hi = min(len(game.moves) + source.additional_plies - 1, source.actor.intervention_max_ply)
                    intervention_at = intervention_rng.randint(lo, hi)
                settings = config.teachers[config.actor_teacher].config()
                if source.actor.mode == "plausible":
                    settings = replace(settings, multipv=source.actor.candidate_count)
                decisions, states, offsets = {}, [], {}
                intervention_done = False
                # Per-game spool caps memory even for verbose candidate evidence.
                with TemporaryFile(mode="w+t", encoding="utf-8") as answers:
                    for _ in range(source.additional_plies):
                        if clock() >= deadline:
                            raise GameError("dataset_timeout", "Generation allowance exhausted.")
                        if game.outcome:
                            break
                        states.append(game)
                        ply = len(game.moves)
                        before = counters.copy()
                        querying_actor = True
                        legal = sorted(legal_moves(game.board, game.turn))
                        if source.actor.mode == "random":
                            decision = ActorDecision(
                                move=rng.choice(legal), reason="uniform-legal", eligible_moves=legal
                            )
                        else:
                            audit = (ply - len(source.start.snapshot.moves)) % config.actor_audit_every == 0
                            answer = query(
                                game,
                                settings,
                                game_id=game_id,
                                retain=audit,
                                role="actor",
                                metadata={"actor_audit": audit},
                            )
                            offsets[ply] = answers.tell()
                            answers.write(answer.model_dump_json() + "\n")
                            if source.actor.mode == "plausible":
                                decision = choose_plausible(game, answer, source.actor, rng)
                            else:
                                alternatives = [move for move in legal if move != answer.move]
                                intervene = not intervention_done and ply == intervention_at and bool(alternatives)
                                decision = ActorDecision(
                                    move=intervention_rng.choice(alternatives) if intervene else answer.move,
                                    reason="marked-intervention" if intervene else "teacher-best",
                                    eligible_moves=alternatives if intervene else [answer.move],
                                    intervention=intervene,
                                )
                                intervention_done |= intervene
                        decisions[ply] = decision.model_dump()
                        game = game.apply(decision.move)
                        store.append(
                            game_id,
                            Snapshot(moves=list(game.moves)),
                            actor_nodes=counters["actor_reported_nodes"] - before["actor_reported_nodes"],
                            actor_queries=counters["actor_attempts"] - before["actor_attempts"],
                            actor_ms=1000 * (counters["actor_seconds"] - before["actor_seconds"]),
                        )
                        querying_actor = False
                    selection = sample_positions(states, source.sampling, sampler, excluded)
                    by_ply = {len(state.moves): state for state in states}
                    for ply in selection.selected:
                        state = by_ply[ply]
                        occurrence = io.occurrence(
                            game_id,
                            Snapshot(moves=list(state.moves)),
                            metadata={
                                "selected": True,
                                "actor_decision": decisions[ply],
                                "sampling_policy": source.sampling.model_dump(),
                            },
                        )
                        if ply in offsets:
                            answers.seek(offsets[ply])
                            io.retain(occurrence, TeacherAnalysis.model_validate_json(answers.readline()))
                        for name in config.supervision:
                            query(state, config.teachers[name].config(), game_id=game_id, retain=True, role="label")
                    result = {
                        "source": source.id,
                        "index": index,
                        "policy": source.actor.mode,
                        "start_ply": len(source.start.snapshot.moves),
                        "final_ply": len(game.moves),
                        "sampling": selection.model_dump(),
                        "intervention_planned_ply": intervention_at,
                        "intervention_applied": intervention_done,
                        "decision_reasons": dict(Counter(d["reason"] for d in decisions.values())),
                        "decisions": [{"ply": ply, **value} for ply, value in decisions.items()],
                    }
                    io.record_game_result(game_id, result)
                    try:
                        store.finish_game(game_id, "terminal" if game.outcome else "ply-budget")
                    except TrajectorySplitConflict as exc:
                        store.finish_game(game_id, "rejected-trajectory", str(exc))
                        active_game = None
                        rejected_games += 1
                        if event:
                            event(
                                {
                                    "kind": "rejected-game",
                                    "game_id": game_id,
                                    "result": result,
                                    "reason": "exact-trajectory-crosses-splits",
                                }
                            )
                        continue
                    active_game = None
                    game_count += 1
                    phases.update(selection.actual)
                    shortfalls.update(selection.shortfall)
                    if event:
                        event({"kind": "completed-game", "game_id": game_id, "result": result})
        if inherited_pending:
            raise ValueError("Inherited identities are absent from the frozen plan.")
        store.run_status(run, "complete")
    except BaseException as exc:
        if active_game is not None:
            if querying_actor:
                store.append(
                    active_game,
                    store.game(active_game).snapshot,
                    actor_nodes=counters["actor_reported_nodes"] - before["actor_reported_nodes"],
                    actor_queries=counters["actor_attempts"] - before["actor_attempts"],
                    actor_ms=1000 * (counters["actor_seconds"] - before["actor_seconds"]),
                )
            reason = (
                "interrupted"
                if isinstance(exc, KeyboardInterrupt)
                else "deadline"
                if isinstance(exc, GameError) and exc.code == "dataset_timeout"
                else "error"
            )
            store.finish_game(active_game, reason, str(exc))
        store.run_status(run, "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", str(exc))
        if event:
            event(
                {"kind": "failed", "run_id": run, "error": f"{type(exc).__name__}: {exc}", "counters": dict(counters)}
            )
        raise
    return {
        "status": "shortfall" if rejected_games or any(shortfalls.values()) else "complete",
        "generation_status": "complete",
        "run_id": run,
        "games": game_count,
        "reused_games": reused_games,
        "rejected_games": rejected_games,
        "reused_rejections": reused_rejections,
        "planned_games": sum(s.games for s in config.sources),
        "inherited_games": inherited,
        "selected_by_phase": dict(phases),
        "shortfall_by_phase": dict(shortfalls),
        "seconds": clock() - started,
        "execution_counters": dict(counters),
        "collection": store.counts(),
    }
