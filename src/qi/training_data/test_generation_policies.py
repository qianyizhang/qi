"""Behavioral checks for evidence-gated actors and bounded position selection."""

from random import Random

import pytest
from pydantic import ValidationError
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves

from qi.players.policy.encoding import input_key
from qi.teacher import TeacherAnalysis, TeacherScore
from qi.training_data.generation_policies import (
    ActorPolicy,
    SamplingPolicy,
    choose_plausible,
    sample_positions,
)


def answer(lines=(), *, game=None, move=None, score=None):
    game = game or Game()
    return TeacherAnalysis(
        schema_version=2,
        adapter_version="uci-teacher-v2",
        snapshot=Snapshot(moves=list(game.moves)),
        state_hash=game.state_hash,
        move=move or sorted(legal_moves(game.board, game.turn))[0],
        engine_name="fake",
        engine_sha256="engine",
        network_sha256="network",
        settings={"MultiPV": "3"},
        requested_nodes=100,
        requested_depth=None,
        timeout_seconds=1.0,
        reported_nodes=100,
        reported_depth=6,
        score=score,
        elapsed_ms=1.0,
        search_info=list(lines),
    )


def rows(depth=6, scores=(100, 70, 20)):
    moves = sorted(legal_moves(Game().board, Game().turn))[:3]
    return [
        f"info depth {depth} multipv {rank} score cp {score} pv {move}"
        for rank, (move, score) in enumerate(zip(moves, scores, strict=True), 1)
    ]


def trajectory(plies=24, seed=7):
    rng = Random(seed)
    game = Game()
    result = [game]
    for _ in range(plies):
        game = game.apply(rng.choice(sorted(legal_moves(game.board, game.turn))))
        result.append(game)
        if game.outcome:
            break
    return result


def test_uniform_eligible_gap_and_determinism():
    game = Game()
    response = answer(rows())
    choices = [choose_plausible(game, response, ActorPolicy(), Random(seed)) for seed in range(32)]
    eligible = sorted(legal_moves(game.board, game.turn))[:2]
    assert {choice.move for choice in choices} == set(eligible)
    assert all(choice.eligible_moves == eligible and choice.depth == 6 for choice in choices)
    assert choose_plausible(game, response, ActorPolicy(), Random(4)) == choices[4]
    assert choose_plausible(game, response, ActorPolicy(max_cp_gap=0), Random(3)).move == response.move


@pytest.mark.parametrize(
    ("lines", "reason"),
    [
        ([], "missing-candidates"),
        (rows()[:2], "incomplete-common-depth"),
        ([rows()[0], rows(7)[1], rows()[2]], "incomplete-common-depth"),
        ([rows()[0], rows()[1].replace("cp 70", "cp 70 lowerbound"), rows()[2]], "incompatible-scores"),
        ([rows()[0], rows()[1].replace("cp 70", "cp 70 upperbound"), rows()[2]], "incompatible-scores"),
        ([rows()[0], rows()[1].replace("score cp 70 ", ""), rows()[2]], "incompatible-scores"),
        ([rows()[0], rows()[1].replace("cp 70", "mate 3"), rows()[2]], "mate-score"),
        ([rows()[0], rows()[1], rows()[2].replace("multipv 3", "multipv 2")], "incomplete-common-depth"),
        (rows(scores=(100, 101, 20)), "inconsistent-ranks"),
        ([line.replace("depth 6 ", "") for line in rows()], "incomplete-common-depth"),
    ],
)
def test_insufficient_or_incompatible_evidence_falls_back(lines, reason):
    response = answer(lines)
    choice = choose_plausible(Game(), response, ActorPolicy(), Random(1))
    assert choice.move == response.move
    assert choice.reason == reason
    assert choice.eligible_moves == [response.move]


def test_deepest_complete_and_stale_mate_guard():
    response = answer(rows(3) + rows(6) + rows(7)[:1])
    assert choose_plausible(Game(), response, ActorPolicy(), Random(0)).depth == 6
    response.search_info[-1] = response.search_info[-1].replace("cp 100", "mate 2")
    assert choose_plausible(Game(), response, ActorPolicy(), Random(0)).reason == "mate-score"
    response = answer(rows(), score=TeacherScore(kind="mate", value=2, bound="exact"))
    assert choose_plausible(Game(), response, ActorPolicy(), Random(0)).reason == "mate-score"


def test_changed_best_and_duplicate_roots_fall_back():
    moves = sorted(legal_moves(Game().board, Game().turn))
    response = answer(rows(), move=moves[3])
    assert choose_plausible(Game(), response, ActorPolicy(), Random(0)).reason == "latest-best-mismatch"
    response = answer([*rows(), rows(7)[0].replace(moves[0], moves[1])])
    assert choose_plausible(Game(), response, ActorPolicy(), Random(0)).reason == "latest-best-mismatch"
    response = answer([rows()[0], rows()[1].replace(moves[1], moves[0]), rows()[2]])
    assert choose_plausible(Game(), response, ActorPolicy(), Random(0)).reason == "duplicate-candidate-roots"


@pytest.mark.parametrize("line", ["info depth 5 multipv 1 score cp nope pv a0a1", "info depth 5 pv z0z1"])
def test_malformed_or_illegal_evidence_is_integrity_error_even_when_final_mate(line):
    response = answer([line], score=TeacherScore(kind="mate", value=2, bound="exact"))
    with pytest.raises(GameError, match="Malformed candidate"):
        choose_plausible(Game(), response, ActorPolicy(), Random(0))


def test_illegal_selected_move_or_wrong_state_is_integrity_error():
    response = answer(rows(), move="z0z1")
    with pytest.raises(GameError, match="exact nonterminal"):
        choose_plausible(Game(), response, ActorPolicy(), Random(0))
    response = answer(rows())
    response.state_hash = "other"
    with pytest.raises(GameError, match="exact nonterminal"):
        choose_plausible(Game(), response, ActorPolicy(), Random(0))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"candidate_count": 0},
        {"candidate_count": 257},
        {"max_cp_gap": -1},
        {"intervention_min_ply": 9, "intervention_max_ply": 8},
        {"candidate_count": "3"},
        {"mode": "best"},
        {"probability_rule": "temperature"},
    ],
)
def test_actor_policy_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValidationError):
        ActorPolicy(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"phase_counts": {}},
        {"phase_counts": {"opening": 0}},
        {"phase_counts": {"opening": -1}},
        {"phase_counts": {"opening": 257}},
        {"phase_counts": {"opening": True}},
        {"phase_counts": {"opening": "2"}},
        {"phase_counts": {"late": 2}},
        {"min_spacing": 0},
        {"min_ply": 4, "max_ply": 3},
    ],
)
def test_sampling_policy_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValidationError):
        SamplingPolicy(**kwargs)


def test_sampling_quotas_spacing_reserved_duplicates_and_honest_shortfalls():
    games = trajectory()
    policy = SamplingPolicy(phase_counts={"opening": 5, "middlegame": 5, "endgame": 5}, min_spacing=4)
    reserved = {input_key(games[1])}
    candidates = [*games, games[3]]
    result = sample_positions(candidates, policy, Random(12), reserved)
    assert result.excluded >= 1
    assert result.duplicates >= 1
    assert 1 not in result.selected
    assert len(result.selected) == sum(result.actual.values())
    assert all(b - a >= 4 for a, b in zip(result.selected, result.selected[1:], strict=False))
    assert result.actual["endgame"] == 0
    assert result.shortfall["endgame"] == 5
    assert all(result.actual[p] + result.shortfall[p] == result.requested[p] for p in result.requested)
    assert all(result.actual[p] <= result.available[p] for p in result.requested)
    assert result == sample_positions(list(reversed(candidates)), policy, Random(12), reserved)
    assert result.model_validate_json(result.model_dump_json()) == result


def test_selection_empty_and_noninitial_prefix_absolute_plies():
    policy = SamplingPolicy(phase_counts={"opening": 2, "middlegame": 2})
    empty = sample_positions([], policy, Random(0))
    assert empty.selected == [] and empty.shortfall == policy.phase_counts
    games = trajectory()[8:]
    result = sample_positions(games, policy, Random(0))
    assert all(ply >= 8 for ply in result.selected)


def test_sampling_rejects_mixed_source_trajectories():
    a, b = trajectory(seed=1), trajectory(seed=2)
    with pytest.raises(ValueError, match="one replay trajectory"):
        sample_positions([a[2], b[3]], SamplingPolicy(), Random(0))


def test_independent_rng_keeps_actor_and_sampler_draws_separate():
    actor = Random(7)
    expected = choose_plausible(Game(), answer(rows()), ActorPolicy(), Random(7))
    sample_positions(trajectory(), SamplingPolicy(), Random(7))
    assert choose_plausible(Game(), answer(rows()), ActorPolicy(), actor) == expected


def test_repeated_board_identity_deduplicated_across_distinct_plies():
    game = Game()
    games = [game]
    for move in ["b0c2", "b9c7", "c2b0", "c7b9"]:
        game = game.apply(move)
        games.append(game)
    assert input_key(games[0]) == input_key(games[4])
    result = sample_positions(games, SamplingPolicy(phase_counts={"opening": 8}, min_spacing=1, min_ply=0), Random(3))
    assert result.duplicates == 1
    assert not ({0, 4} <= set(result.selected))
    assert result.available["opening"] == 4
    assert result.shortfall["opening"] == 4


def test_candidate_choice_is_legal_across_replayed_states():
    for game in trajectory()[1:]:
        if game.outcome:
            continue
        moves = sorted(legal_moves(game.board, game.turn))[:3]
        lines = [f"info depth 3 multipv {rank} score cp 0 pv {move}" for rank, move in enumerate(moves, 1)]
        response = answer(lines, game=game)
        decision = choose_plausible(game, response, ActorPolicy(), Random(len(game.moves)))
        assert decision.move in moves
        assert all(move in legal_moves(game.board, game.turn) for move in decision.eligible_moves)
