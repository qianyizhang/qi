"""The teaching example must preserve replay, sampling, score and API semantics."""

from itertools import combinations

import pytest
from fastapi.testclient import TestClient
from qi_game.reference import restore

from qi.api import create_app
from qi.generation_lesson import generation_lesson, practice_sampling
from qi.players.policy.encoding import input_key
from qi.training_data.contracts import classify_phase


def test_saved_lesson_replays_and_accounts_for_all_supervision():
    lesson = generation_lesson()
    example = lesson.example
    assert len(lesson.frames) == 33
    end = lesson.frames[-1]
    assert end.position.outcome.winner == "black"
    assert end.position.outcome.reason == "checkmate"
    assert end.phase == "middlegame"
    assert example.sampling.selected == [3, 10, 17, 22, 26, 31]
    assert sum(example.sampling.shortfall.values()) == 11
    assert example.sampling.available == {"opening": 3, "middlegame": 28, "endgame": 0}
    assert all(lesson.frames[p].phase != "endgame" for p in example.sampling.selected)
    assert len(example.analyses) == 12
    assert {a.ply for a in example.analyses} == set(example.sampling.selected)
    for ply in example.sampling.selected:
        analyses = [a for a in example.analyses if a.ply == ply]
        assert {a.nodes for a in analyses} == {10000, 100000}
        assert all(a.move in lesson.frames[ply].position.legal_moves for a in analyses)
    exact = [a for a in example.analyses if a.score.kind == "cp" and a.score.bound == "exact"]
    assert [(a.ply, a.nodes, a.score.value) for a in exact] == [(10, 100000, -21), (17, 10000, 51)]
    assert lesson.frames[17].position.turn == "black"
    assert sum(a.score.kind == "mate" for a in example.analyses) == 2
    assert example.batch.attempts == example.batch.accepted + example.batch.rejected
    assert example.batch.endgame_shortfall_games < example.batch.accepted


@pytest.mark.parametrize("spacing", [1, 4, 8])
def test_practice_respects_window_phase_spacing_and_keeps_recorded_evidence(spacing):
    lesson = generation_lesson()
    before = lesson.model_dump_json()
    result = practice_sampling(spacing, 7)
    assert result == practice_sampling(spacing, 7)
    assert all(1 <= p < 32 for p in result.selected)
    assert all(abs(a - b) >= spacing for a, b in combinations(result.selected, 2))
    games = [restore(lesson.frames[p].position.snapshot) for p in result.selected]
    assert len({input_key(g) for g in games}) == len(games)
    for phase, quota in result.requested.items():
        assert result.actual[phase] == sum(classify_phase(g) == phase for g in games)
        assert result.actual[phase] <= quota
        assert result.shortfall[phase] == quota - result.actual[phase]
    assert result.actual["endgame"] == 0
    assert lesson.model_dump_json() == before


def test_lesson_http_needs_no_collection_or_teacher_and_bounds_practice(monkeypatch, tmp_path):
    monkeypatch.setenv("QI_COLLECTION_PATHS", "")
    monkeypatch.setenv("QI_LAB_STATE", str(tmp_path / "lab"))
    with TestClient(create_app()) as client:
        lesson = client.get("/api/learn/generation")
        assert lesson.status_code == 200
        assert lesson.json()["example"]["game_id"] == 6286
        assert client.get("/api/learn/generation/sampling?spacing=1&seed=7").json()["actual"]["middlegame"] == 8
        for query in ["spacing=0", "spacing=9", "seed=-1", "seed=32", "spacing=bad"]:
            assert client.get(f"/api/learn/generation/sampling?{query}").status_code == 422
        assert client.get("/api/learn/generation").json() == lesson.json()
