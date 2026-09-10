"""Bounded generation and reanalysis into a collection, with resumable source keys."""

from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from random import Random
from time import monotonic, perf_counter

from qi.artifacts import provenance
from qi.evaluation import Corpus
from qi.game import GameError, legal_moves
from qi.players.policy.encoding import input_key
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity, TeacherSession, analyze
from qi.training_data.config import PreparationConfig
from qi.training_data.contracts import Example, fingerprint, satisfies_objective
from qi.training_data.generation import source_identity, teacher_spec
from qi.training_data.store import AnalysisPayload, AnalysisSpec, Collection, GamePayload, RunPayload
from qi.training_data.v1 import reserved_inputs


def analyze_occurrence(
    store: Collection, occurrence: int, config: TeacherConfig, spec: AnalysisSpec, labeler=analyze, *, force=False
) -> TeacherAnalysis:
    spec_id = store.spec(spec, {"engine": str(config.engine), "network": str(config.network)})
    existing = store.first_success(occurrence, spec_id)
    if existing and not force:
        return AnalysisPayload.model_validate_json(
            store.db.execute("SELECT json(payload) FROM analyses WHERE id=?", (existing[0],)).fetchone()[0]
        ).answer
    attempt = store.begin_analysis(occurrence, spec_id)
    answer = None
    try:
        answer = labeler(store.snapshot(occurrence).game(), config)
        store.finish_analysis(attempt, answer)
        return answer
    except BaseException as exc:
        store.finish_analysis(
            attempt, failure=f"{type(exc).__name__}: {exc}", raw=[answer.model_dump_json()] if answer else []
        )
        raise


def generate_collection(store: Collection, config: PreparationConfig, *, labeler: Callable = analyze) -> dict:
    config = PreparationConfig.model_validate(config.model_dump())
    config.generation.require_current()
    corpus = Corpus.model_validate_json(Path(config.corpus).read_text())
    if corpus.digest != config.corpus_sha256:
        raise ValueError("Reserved corpus identity differs from configuration.")
    teacher = config.supervision.teacher()
    identity = TeacherIdentity.read(teacher)
    actor = config.actor_teacher.teacher() if config.actor_teacher else teacher
    label_spec = AnalysisSpec(
        supervision=teacher_spec(teacher, identity), timeout_seconds=float(teacher.timeout_seconds)
    )
    actor_spec = AnalysisSpec(supervision=teacher_spec(actor), timeout_seconds=float(actor.timeout_seconds))
    persistent = config.teacher_process == "persistent"
    if persistent and labeler is not analyze:
        raise ValueError("Persistent mode uses the session labeler.")
    if persistent and (actor.engine.resolve(), actor.network.resolve()) != (
        teacher.engine.resolve(),
        teacher.network.resolve(),
    ):
        raise ValueError("Persistent actor/supervisor must share pinned files.")
    recipe = config.generation
    run = store.run(
        RunPayload(
            config=config.model_dump(),
            provenance=provenance(),
            seed=recipe.seed,
            planned_games=sum(p.games for p in recipe.sources),
        )
    )
    store.run_status(run, "running")
    deadline = monotonic() + recipe.seconds
    reserved = reserved_inputs(corpus)
    active_game = None
    try:
        with TeacherSession(teacher, identity=identity) if persistent else nullcontext() as session:
            provider = session.analyze if session else labeler

            def query(game, settings):
                if deadline - monotonic() < settings.timeout_seconds:
                    raise GameError("dataset_timeout", "Insufficient remaining time for the pinned query timeout.")
                return provider(game, settings)

            for plan in recipe.sources:
                for index in range(plan.games):
                    actor_identity, key = source_identity(recipe, plan, index, actor_spec.supervision)
                    payload = GamePayload(
                        source_id=key,
                        family=plan.start.family_id or key,
                        split=plan.split,
                        mode=plan.mode,
                        initial=plan.start.snapshot,
                        snapshot=plan.start.snapshot,
                        actor=actor_identity,
                        plan=plan,
                        themes=plan.start.themes,
                        objective=plan.start.objective,
                    )
                    game_id = store.begin_game(run, key, payload)
                    cached = {}
                    if game_id is not None:
                        active_game = game_id
                        rng = Random(fingerprint("continuation-actor-v2", actor_identity))
                        game = plan.start.snapshot.game()
                        for _ in range(plan.additional_plies):
                            if monotonic() >= deadline:
                                raise GameError("dataset_timeout", "Collection generation deadline reached.")
                            if game.outcome:
                                break
                            snap = Snapshot(moves=list(game.moves))
                            occurrence = store.occurrence(
                                game_id, snap, phase=plan.start.curated_phase if snap == plan.start.snapshot else None
                            )
                            nodes, elapsed, queries = 0, 0.0, 0
                            if plan.mode == "random":
                                move = rng.choice(sorted(legal_moves(game.board, game.turn)))
                            else:
                                # Retain bounded per-game actor answers; persist selected answers below.
                                # Failed actor queries always get a durable attempt.
                                answer = None
                                query_started = perf_counter()
                                try:
                                    answer = query(game, actor)
                                    if answer.snapshot != snap or AnalysisSpec.from_analysis(answer) != actor_spec:
                                        raise ValueError("Actor answer differs from requested state/specification.")
                                    Example(analysis=answer, source_ids=[key])
                                except BaseException as exc:
                                    attempt = store.begin_analysis(occurrence, store.spec(actor_spec))
                                    store.finish_analysis(
                                        attempt,
                                        failure=f"{type(exc).__name__}: {exc}",
                                        raw=[answer.model_dump_json()] if answer else [],
                                    )
                                    store.append(
                                        game_id, snap, actor_queries=1, actor_ms=(perf_counter() - query_started) * 1000
                                    )
                                    raise
                                cached[occurrence] = answer
                                move, nodes, elapsed, queries = (
                                    answer.move,
                                    answer.reported_nodes or 0,
                                    answer.elapsed_ms,
                                    1,
                                )
                            game = game.apply(move)
                            store.append(
                                game_id,
                                Snapshot(moves=list(game.moves)),
                                actor_nodes=nodes,
                                actor_ms=elapsed,
                                actor_queries=queries,
                            )
                        store.finish_game(game_id, "terminal" if game.outcome else "ply-budget")
                        active_game = None
                    else:
                        game_id = store.db.execute(
                            "SELECT id FROM games WHERE run_id=? AND logical_key=? AND status='complete'", (run, key)
                        ).fetchone()[0]
                    candidates = []
                    for row in store.db.execute(
                        "SELECT id,phase FROM position_occurrences WHERE game_id=? ORDER BY ply_count", (game_id,)
                    ):
                        game = store.snapshot(row[0]).game()
                        if not game.outcome and plan.window.matches(game, row[1]) and input_key(game) not in reserved:
                            candidates.append((row[0], game))
                    Random(fingerprint("position-sampler-v2", actor_identity)).shuffle(candidates)
                    retained, seen = 0, set()
                    for occurrence, game in candidates:
                        if retained == plan.samples:
                            break
                        if input_key(game) in seen:
                            continue
                        seen.add(input_key(game))
                        if monotonic() >= deadline:
                            raise GameError("dataset_timeout", "Collection labeling deadline reached.")
                        cached_answer = cached.get(occurrence)
                        if cached_answer is not None and actor_spec == label_spec:
                            spec_id = store.spec(label_spec)
                            if not store.first_success(occurrence, spec_id):
                                attempt = store.begin_analysis(occurrence, spec_id)
                                try:
                                    store.finish_analysis(attempt, cached_answer)
                                except BaseException as exc:
                                    store.finish_analysis(
                                        attempt, failure=str(exc), raw=[cached_answer.model_dump_json()]
                                    )
                                    raise
                            answer = cached_answer
                        else:
                            answer = analyze_occurrence(store, occurrence, teacher, label_spec, query)
                        if satisfies_objective(game, answer.move, plan.start.objective):
                            retained += 1
            store.run_status(run, "complete")
    except BaseException as exc:
        if active_game is not None:
            store.finish_game(active_game, "error", str(exc))
        store.run_status(run, "failed", str(exc))
        raise
    return {"status": "complete", "run_id": run, "analysis_spec": label_spec.identity, **store.counts()}
