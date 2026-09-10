"""Shared bounded continuation loop with independent move choice and supervision."""

from collections.abc import Callable
from dataclasses import replace
from random import Random
from time import monotonic

from pydantic import ValidationError

from qi.evaluation import Corpus
from qi.game import Game, GameError, legal_moves
from qi.players.policy.encoding import input_key
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity, analyze
from qi.training_data.contracts import (
    Example,
    GenerationRecipe,
    Library,
    Source,
    SourcePlan,
    classify_phase,
    fingerprint,
    satisfies_objective,
    state_fingerprint,
    supervision_spec,
)
from qi.training_data.v1 import reserved_inputs


def teacher_spec(config: TeacherConfig, identity: TeacherIdentity | None = None) -> dict:
    identity = identity or TeacherIdentity.read(config)
    identity.require(config)
    return {
        "target": "legal-teacher-move-v1",
        "authority": "teacher-preference",
        "adapter": "uci-teacher-v1",
        "engine_sha256": identity.engine_sha256,
        "network_sha256": identity.network_sha256,
        "settings": {"Threads": "1", "Hash": "16", "MultiPV": "1", "Ponder": "false"},
        "nodes": config.nodes,
        "depth": config.depth,
    }


def source_identity(recipe: GenerationRecipe, plan: SourcePlan, index: int, actor_spec: dict) -> tuple[dict, str]:
    """Shared continuation-v2 identity; sampling settings never seed actor randomness."""
    actor = {
        "seed": recipe.seed,
        "plan_id": plan.id,
        "mode": plan.mode,
        "start": state_fingerprint(plan.start.snapshot),
        "index": index,
        "actor": actor_spec if plan.mode == "teacher-guided" else "sorted-legal-random-v1",
    }
    return actor, fingerprint("generated-source-v2", {"actor": actor, "plan": plan.model_dump()})


def generate_library(
    recipe: GenerationRecipe,
    corpus: Corpus,
    teacher: TeacherConfig,
    *,
    actor_teacher: TeacherConfig | None = None,
    labeler: Callable[[Game, TeacherConfig], TeacherAnalysis] = analyze,
    checkpoint: Callable[[Library], None] | None = None,
    teacher_identity: TeacherIdentity | None = None,
) -> Library:
    recipe = GenerationRecipe.model_validate(recipe.model_dump())
    recipe.require_current()
    actor_teacher = actor_teacher or teacher
    deadline = monotonic() + recipe.seconds
    label_spec = teacher_spec(teacher, teacher_identity)
    actor_spec = label_spec if actor_teacher == teacher else teacher_spec(actor_teacher, teacher_identity)
    reserved = reserved_inputs(corpus)
    sources, examples = [], {}
    failure = None

    def query(game: Game, config: TeacherConfig, spec: dict) -> TeacherAnalysis:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GameError("dataset_timeout", "Generation deadline reached.")
        result = labeler(game, replace(config, timeout_seconds=min(config.timeout_seconds, remaining)))
        if (
            result.snapshot.moves != list(game.moves)
            or result.state_hash != game.state_hash
            or supervision_spec(result) != spec
        ):
            raise GameError("invalid_supervision", "Teacher answer differs from requested state or supervision recipe.")
        try:
            Example(analysis=result, source_ids=["validation-only"])
        except ValidationError as exc:
            raise GameError("invalid_supervision", "Teacher returned an invalid training target.") from exc
        return result

    def snapshot(status: str) -> Library:
        return Library(
            recipe=recipe,
            reserved_corpus=corpus,
            sources=sources,
            examples=list(examples.values()),
            status=status,
            failure=failure,
        ).model_copy(deep=True)

    for plan in recipe.sources:
        for index in range(plan.games):
            actor_identity, source_id = source_identity(recipe, plan, index, actor_spec)
            rng = Random(fingerprint("continuation-actor-v2", actor_identity))
            sampler_rng = Random(fingerprint("position-sampler-v2", actor_identity))
            game = plan.start.snapshot.game()
            candidates, cached = [], {}
            reason = "ply-budget"
            try:
                for _ in range(plan.additional_plies):
                    if monotonic() >= deadline:
                        raise GameError("dataset_timeout", "Generation deadline reached.")
                    if game.outcome:
                        break
                    phase = (
                        plan.start.curated_phase
                        if game.moves == tuple(plan.start.snapshot.moves) and plan.start.curated_phase is not None
                        else classify_phase(game)
                    )
                    if plan.window.matches(game, phase) and input_key(game) not in reserved:
                        candidates.append(game)
                    if plan.mode == "random":
                        move = rng.choice(sorted(legal_moves(game.board, game.turn)))
                    else:
                        answer = query(game, actor_teacher, actor_spec)
                        cached[state_fingerprint(answer.snapshot)] = answer
                        move = answer.move
                    game = game.apply(move)
                if game.outcome:
                    reason = "terminal"
                sampler_rng.shuffle(candidates)
                retained = 0
                seen = set()
                for candidate in candidates:
                    if retained == plan.samples:
                        break
                    key = input_key(candidate)
                    if key in seen:
                        continue
                    seen.add(key)
                    answer = cached.get(state_fingerprint(Snapshot(moves=list(candidate.moves))))
                    if answer is None or supervision_spec(answer) != label_spec:
                        answer = query(candidate, teacher, label_spec)
                    # An objective is a checked condition, never an interpretation of an engine score.
                    if not satisfies_objective(candidate, answer.move, plan.start.objective):
                        continue
                    example = Example(analysis=answer, source_ids=[source_id])
                    if example.fingerprint in examples:
                        examples[example.fingerprint].source_ids.append(source_id)
                    else:
                        examples[example.fingerprint] = example
                    retained += 1
            except (GameError, OSError, ValidationError) as exc:
                failure = str(exc)
                reason = (
                    "deadline"
                    if monotonic() >= deadline or getattr(exc, "code", None) == "dataset_timeout"
                    else "error"
                )
                if game.outcome:
                    reason = "terminal"
            sources.append(
                Source(
                    id=source_id,
                    family_id=plan.start.family_id or source_id,
                    plan_id=plan.id,
                    snapshot=Snapshot(moves=list(game.moves)),
                    actor_spec={
                        "mode": plan.mode,
                        "recipe": actor_spec if plan.mode == "teacher-guided" else "sorted-legal-random-v1",
                    },
                    stop_reason=reason,
                )
            )
            if checkpoint is not None or failure:
                current = snapshot("incomplete")
                if checkpoint is not None:
                    checkpoint(current)
                if failure:
                    return current
    return snapshot("complete")
