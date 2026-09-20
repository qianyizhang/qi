"""Identity, isolation, quota and continuation contracts without an engine or torch."""

from dataclasses import replace
from random import Random

import pytest
from pydantic import ValidationError
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves, restore

from qi.training_data.assembly import Bucket, MixtureRecipe, TrainingDataset, assemble
from qi.training_data.contracts import (
    GenerationRecipe,
    Library,
    SamplingWindow,
    SourcePlan,
    StartingPosition,
    classify_phase,
    observation_fingerprint,
    state_fingerprint,
)
from qi.training_data.generation import generate_library


def mixture(library, count=2):
    return MixtureRecipe(
        id="fixture",
        supervision_fingerprint=library.examples[0].supervision_fingerprint,
        buckets=[
            Bucket(id=f"{mode}-{split}", split=split, modes=[mode], count=count)
            for mode in ("random", "teacher-guided")
            for split in ("train", "validation")
        ],
    )


def test_two_mode_mixture_roundtrip_and_fixed_validation(library):
    small = assemble(library, mixture(library, 1))
    large_recipe = mixture(library, 1)
    for bucket in large_recipe.buckets:
        if bucket.split == "train":
            bucket.count = 3
    large = assemble(library, large_recipe)
    assert small.manifest.status == large.manifest.status == "complete"
    assert small.split_labels("validation") == large.split_labels("validation")
    assert len(large.labels) == 8
    assert TrainingDataset.model_validate_json(large.model_dump_json()).manifest == large.manifest
    assert {label.input_sha256 for label in large.split_labels("train")}.isdisjoint(
        label.input_sha256 for label in large.split_labels("validation")
    )
    assert "validation/phase:opening" in large.slice_inputs()
    assert "train/theme:development" in large.slice_inputs()


def test_semantic_fingerprints_ignore_telemetry_but_pin_targets_and_recipe(library):
    first = assemble(library, mixture(library))
    altered = library.model_copy(deep=True)
    for example in altered.examples:
        example.analysis.elapsed_ms += 500
        example.analysis.timeout_seconds += 1
        example.analysis.settings["EvalFile"] = "/different/local/path"
    second = assemble(altered, mixture(altered))
    assert first.manifest.fingerprint == second.manifest.fingerprint
    assert first.digest != second.digest
    example = library.examples[0]
    target_changed = example.model_copy(deep=True)
    target_changed.analysis.move = next(
        m
        for m in legal_moves(restore(example.analysis.snapshot).board, restore(example.analysis.snapshot).turn)
        if m != example.analysis.move
    )
    assert target_changed.fingerprint != example.fingerprint
    other = mixture(library)
    other.seed += 1
    assert assemble(library, other).manifest.fingerprint != first.manifest.fingerprint


def test_state_and_observation_are_distinct_identities():
    first = Snapshot()
    repeated = Snapshot(moves=["b0c2", "b9c7", "c2b0", "c7b9"])
    assert state_fingerprint(first) != state_fingerprint(repeated)
    assert observation_fingerprint(restore(first)) == observation_fingerprint(restore(repeated))


def test_incomplete_quota_does_not_redistribute_or_train(library):
    recipe = mixture(library)
    recipe.buckets[0].count = 100
    dataset = assemble(library, recipe)
    assert dataset.manifest.status == "incomplete"
    assert dataset.manifest.actual[recipe.buckets[0].id] == 3
    assert dataset.manifest.actual[recipe.buckets[1].id] == 2
    with pytest.raises(ValueError, match="Incomplete mixture"):
        dataset.require_complete()
    raw = dataset.model_dump()
    raw["manifest"]["status"] = "complete"
    with pytest.raises(ValidationError, match="Manifest selection"):
        TrainingDataset.model_validate(raw)


def test_overlapping_buckets_assign_once_in_declared_order(library):
    recipe = mixture(library)
    recipe.buckets.insert(1, Bucket(id="overlap", split="train", modes=["random"], count=1))
    dataset = assemble(library, recipe)
    assert dataset.manifest.actual["overlap"] == 0
    assert len({row.example for row in dataset.manifest.selections}) == len(dataset.labels)


def test_actor_supervision_reuse_requires_matching_spec(data_setup):
    recipe, corpus, teacher, labeler, calls = data_setup
    recipe.sources = [recipe.sources[2]]
    first = generate_library(recipe, corpus, teacher, labeler=labeler)
    assert len(calls) == 8  # all selected analyses reuse exact actor answers
    calls.clear()
    second = generate_library(recipe, corpus, teacher, actor_teacher=replace(teacher, nodes=101), labeler=labeler)
    assert len(calls) == 11  # separate supervisor budget forces three new queries
    assert all(e.analysis.requested_nodes == 100 for e in second.examples)
    assert first.sources[0].snapshot == second.sources[0].snapshot


def test_wrong_state_or_recipe_never_enters_library(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup

    def wrong(game, config):
        result = labeler(game, config)
        result.requested_nodes += 1
        return result

    result = generate_library(recipe, corpus, teacher, labeler=wrong)
    assert result.status == "incomplete" and not result.examples
    assert "requested state or supervision" in result.failure


def test_failed_labeling_preserves_partial_examples(data_setup):
    recipe, corpus, teacher, labeler, calls = data_setup
    checkpoints = []

    def failing(game, config):
        if len(calls) == 2:
            raise GameError("teacher_exit", "synthetic failure")
        return labeler(game, config)

    result = generate_library(recipe, corpus, teacher, labeler=failing, checkpoint=checkpoints.append)
    assert result.status == "incomplete" and len(result.examples) == 2
    assert checkpoints[-1] == result
    assert Library.model_validate_json(result.model_dump_json()).failure == result.failure


def test_family_and_repeated_start_isolation_reject_before_assembly(data_setup, library):
    recipe, _, _, _, _ = data_setup
    recipe.sources[3].start.family_id = recipe.sources[2].start.family_id
    with pytest.raises(ValidationError, match="family cannot cross splits"):
        GenerationRecipe.model_validate(recipe.model_dump())
    raw = library.model_dump()
    raw["recipe"]["sources"][3]["start"]["snapshot"] = raw["recipe"]["sources"][2]["start"]["snapshot"]
    raw["sources"][3]["snapshot"] = raw["sources"][2]["snapshot"]
    with pytest.raises(ValidationError, match="cannot mint another family"):
        Library.model_validate(raw)


def test_ambiguous_observation_targets_rejected_but_library_can_retain_alternatives(library):
    alternate = library.examples[0].model_copy(deep=True)
    game = restore(alternate.analysis.snapshot)
    alternate.analysis.move = next(
        move for move in sorted(legal_moves(game.board, game.turn)) if move != alternate.analysis.move
    )
    library.examples.append(alternate)
    assert Library.model_validate(library.model_dump())
    with pytest.raises(ValueError, match="Ambiguous supervision"):
        assemble(library, mixture(library))


def test_shared_observation_across_independent_families_rejected(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup
    # Teacher-guided standard starts produce the same game, despite distinct family IDs.
    for plan in recipe.sources:
        plan.mode = "teacher-guided"
        plan.start = StartingPosition(id="initial", version="1")
    library = generate_library(recipe, corpus, teacher, labeler=labeler)
    assert any(len(e.source_ids) > 1 for e in library.examples)
    with pytest.raises(ValueError, match="crosses training and held-out"):
        assemble(library, mixture(library))


def test_phase_policy_and_sampling_ply_are_independent():
    assert classify_phase(Game()) == "opening"
    developed = restore(Snapshot(moves=["b0c2", "b9c7", "h0g2", "h9g7"]))
    assert classify_phase(developed) == "middlegame"
    # A reachable endgame fixture found with deterministic legal play; no imported diagram.
    rng, game = Random(0), Game()
    while not game.outcome and classify_phase(game) != "endgame":
        game = game.apply(rng.choice(sorted(legal_moves(game.board, game.turn))))
    assert classify_phase(game) == "endgame"
    assert SamplingWindow(min_ply=0, max_ply=5, phases=["middlegame"]).matches(developed, classify_phase(developed))
    assert not SamplingWindow(min_ply=5, phases=["middlegame"]).matches(developed, classify_phase(developed))
    assert not SamplingWindow(phases=["opening"]).matches(developed, classify_phase(developed))


def test_curated_phase_requires_provenance_and_only_applies_to_exact_start(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup
    plan = recipe.sources[2]
    plan.start.curated_phase = "unknown"
    with pytest.raises(ValidationError, match="explicit authority"):
        StartingPosition.model_validate(plan.start.model_dump())
    plan.start.phase_authority = "fixture annotation"
    plan.window.phases = ["unknown"]
    recipe.sources = [plan]
    library = generate_library(recipe, corpus, teacher, labeler=labeler)
    assert len(library.examples) == 1
    assert library.examples[0].analysis.snapshot == plan.start.snapshot
    assert len(library.sources[0].snapshot.moves) == 9  # sampler doesn't end the continuation


def test_reserved_history_prefixes_are_excluded_before_quota_accounting(library):
    from qi.evaluation import Opening
    from qi.players.policy.encoding import input_key
    from qi.training_data.v1 import reserved_inputs

    example = library.examples[0]
    library.reserved_corpus.openings.append(
        Opening(
            id="new-held-out-family",
            description="Reserve this full history and all prefixes",
            snapshot=example.analysis.snapshot,
        )
    )
    dataset = assemble(library, mixture(library))
    reserved = reserved_inputs(library.reserved_corpus)
    assert input_key(restore(example.analysis.snapshot)) in reserved
    assert all(label.input_sha256 not in reserved for label in dataset.labels)


def test_wrong_snapshot_and_illegal_targets_preserve_failure(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup

    def wrong(game, config):
        result = labeler(game, config)
        result.move = "a0a9"
        return result

    library = generate_library(recipe, corpus, teacher, labeler=wrong)
    assert library.status == "incomplete" and not library.examples
    assert "invalid training target" in library.failure


def test_objective_accepts_only_referee_immediate_win():
    from qi.training_data.contracts import satisfies_objective

    assert not satisfies_objective(Game(), "b0c2", "win-in-one")
    rng, game = Random(2), Game()
    while not game.outcome:
        move = rng.choice(sorted(legal_moves(game.board, game.turn)))
        after = game.apply(move)
        if after.outcome and after.outcome.winner:
            assert satisfies_objective(game, move, "win-in-one") == (after.outcome.winner == game.turn)
            break
        game = after
    else:
        pytest.fail("The replay fixture must end in a decisive outcome.")


def test_deadline_keeps_an_explicit_unfinished_source(data_setup, monkeypatch):
    recipe, corpus, teacher, labeler, _ = data_setup
    ticks = iter([0, 301])
    monkeypatch.setattr("qi.training_data.generation.monotonic", lambda: next(ticks, 302))
    library = generate_library(recipe, corpus, teacher, labeler=labeler)
    assert library.status == "incomplete"
    assert library.sources[0].stop_reason == "deadline"
    assert restore(library.sources[0].snapshot).outcome is None
    assert not library.examples


def test_sampling_settings_and_game_count_do_not_change_existing_trajectory(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup
    recipe.sources = [recipe.sources[0]]
    baseline = generate_library(recipe, corpus, teacher, labeler=labeler)
    changed = recipe.model_copy(deep=True)
    changed.sources[0].samples = 1
    changed.sources[0].games = 2
    changed.sources[0].window.min_ply = 2
    result = generate_library(changed, corpus, teacher, labeler=labeler)
    assert baseline.sources[0].snapshot == result.sources[0].snapshot


def test_retained_checkpoint_objects_do_not_gain_future_lineage(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup
    recipe.sources = [recipe.sources[2]]
    recipe.sources[0].games = 2
    recipe.sources[0].samples = 8
    checkpoints = []
    generate_library(recipe, corpus, teacher, labeler=labeler, checkpoint=checkpoints.append)
    assert len(checkpoints[0].sources) == 1
    assert all(len(e.source_ids) == 1 for e in checkpoints[0].examples)
    Library.model_validate(checkpoints[0].model_dump())


def test_duplicate_themes_cannot_inflate_diagnostic_slice_counts():
    with pytest.raises(ValidationError, match="themes"):
        StartingPosition(id="duplicate", version="1", themes=["development", "development"])


def test_first_bucket_owns_all_histories_of_the_same_observation(data_setup):
    recipe, corpus, teacher, labeler, _ = data_setup
    histories = [
        ["b0c2", "b9c7", "h0g2", "h9g7"],
        ["b0c2"],
        ["h0g2", "h9g7", "b0c2", "b9c7"],
        ["a3a4"],
    ]
    recipe.sources = [
        SourcePlan(
            id=f"alias-{i}",
            mode="teacher-guided" if i == 2 else "random",
            split="validation" if i == 3 else "train",
            additional_plies=1,
            samples=1,
            start=StartingPosition(
                id=f"start-{i}", version="1", family_id=f"family-{i}", snapshot=Snapshot(moves=moves)
            ),
        )
        for i, moves in enumerate(histories)
    ]
    library = generate_library(recipe, corpus, teacher, labeler=labeler)
    for seed in range(12):
        recipe = MixtureRecipe(
            id="aliases",
            seed=seed,
            supervision_fingerprint=library.examples[0].supervision_fingerprint,
            buckets=[
                Bucket(id="first", split="train", modes=["random"], count=1),
                Bucket(id="later", split="train", modes=["teacher-guided"], count=1),
                Bucket(id="held-out", split="validation", count=1),
            ],
        )
        dataset = assemble(library, recipe)
        assert dataset.manifest.actual["later"] == 0


def test_old_generation_recipes_remain_readable_but_cannot_silently_regenerate(data_setup, library):
    old = library.model_dump()
    old["recipe"]["version"] = "continuations-v1"
    assert Library.model_validate(old).recipe.version == "continuations-v1"
    recipe, corpus, teacher, labeler, _ = data_setup
    recipe.version = "continuations-v1"
    with pytest.raises(GameError, match="continuations-v2"):
        generate_library(recipe, corpus, teacher, labeler=labeler)
