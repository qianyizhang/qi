"""Generated-data readers preserve evidence and expose honest selection denominators."""

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from qi.api import create_app
from qi.collection_view import (
    analysis_evidence,
    collection_page,
    collection_quality,
    discover_collections,
    game_detail,
    game_position,
)
from qi.game import GameError
from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis
from qi.training_data.generation_io import CollectionIO
from qi.training_data.store import AnalysisSpec, Collection, GamePayload, RunPayload


def build_review_collection(path):
    """Hermetic browser/API evidence, including overlap and unequal label coverage."""
    with Collection(path) as store:
        run = store.run(
            RunPayload(config={"recipe": {"name": "Review fixture"}}, provenance={}, seed=1, planned_games=1)
        )

        def game(key, split, moves, *, run_id=run, status="accepted", selected=True):
            gid = store.begin_game(
                run_id,
                key,
                GamePayload(
                    source_id=key,
                    family=key,
                    split=split,
                    mode="random",
                    initial=Snapshot(),
                    snapshot=Snapshot(),
                    actor={"source": key, "policy": {"mode": "random" if split == "validation" else "plausible"}},
                ),
            )
            for i in range(len(moves)):
                store.append(gid, Snapshot(moves=moves[: i + 1]))
            if selected:
                CollectionIO(store).occurrence(gid, Snapshot(), {"selected": True})
                CollectionIO(store).record_game_result(
                    gid,
                    {
                        "sampling": {
                            "selected": [0],
                            "actual": {"opening": 1},
                            "requested": {"opening": 2},
                            "shortfall": {"opening": 1},
                        }
                    },
                )
            if status == "accepted":
                store.finish_game(gid, "ply-budget")
            elif status == "rejected":
                store.finish_game(gid, "rejected-trajectory", "Exact trajectory crosses splits.")
            elif status == "failed":
                store.finish_game(gid, "error", "Teacher failed")
            return gid

        first = game("train-example", "train", ["b0c2", "b9c7"])
        store.run_status(run, "complete")
        recovery = store.run(
            RunPayload(
                config={"recipe": {"name": "Review continuation"}, "continued_from_run": run},
                provenance={},
                seed=2,
                planned_games=4,
            )
        )
        second = game("validation-example", "validation", ["c3c4"], run_id=recovery)
        game("rejected-example", "validation", ["b0c2", "b9c7"], run_id=recovery, status="rejected")
        game("failed-example", "train", [], run_id=recovery, status="failed")
        game("running-example", "train", [], run_id=recovery, status="running", selected=False)
        for gid, budgets in [(first, [100, 1000, 100]), (second, [100])]:
            occurrence = store.db.execute("SELECT id FROM position_occurrences WHERE game_id=?", (gid,)).fetchone()[0]
            for i, nodes in enumerate(budgets):
                answer = TeacherAnalysis(
                    schema_version=2,
                    adapter_version="uci-teacher-v2",
                    snapshot=Snapshot(),
                    state_hash=Snapshot().game().state_hash,
                    move="b0c2" if i == 0 else "c3c4",
                    engine_name="fixture",
                    engine_sha256="a" * 64,
                    network_sha256="b" * 64,
                    settings={"Threads": "1", "Hash": "16", "MultiPV": "1", "Ponder": "false"},
                    requested_nodes=nodes,
                    requested_depth=None,
                    timeout_seconds=1.0,
                    reported_nodes=nodes,
                    reported_depth=2,
                    elapsed_ms=1.0,
                    score={"kind": "cp", "value": 20 + i, "bound": "exact"},
                    search_info=[],
                )
                aid = store.begin_analysis(occurrence, store.spec(AnalysisSpec.from_analysis(answer)))
                store.finish_analysis(aid, answer)
    return first, second


@pytest.fixture
def collection(tmp_path, monkeypatch):
    path = tmp_path / "fixture.sqlite"
    build_review_collection(path)
    monkeypatch.setenv("QI_COLLECTION_PATHS", str(path))
    monkeypatch.setenv("QI_LAB_STATE", str(tmp_path / "jobs"))
    return path, discover_collections().collections[0].id


def test_counts_rejects_failures_and_continuations_are_distinct(collection):
    _, identity = collection
    page = collection_page(identity)
    assert (page.overall.attempts, page.overall.accepted, page.overall.rejected, page.overall.other) == (5, 2, 1, 2)
    assert page.overall.selected == 2  # Rejected and failed selected positions are excluded.
    assert page.overall.outcomes == {"unfinished": 2}  # A ply budget is not a draw.
    assert page.overall.sampling_games == page.overall.shortfall_games == 2
    assert page.overall.actual == {"opening": 2}
    assert page.overall.requested == {"opening": 4}
    assert page.runs[0].continued_from == 1
    assert sum(s.accepted for s in page.run_stats.values()) == page.overall.accepted
    assert collection_page(identity, disposition="rejected").total == 1
    assert collection_page(identity, split="validation", disposition="accepted").filtered.accepted == 1
    assert collection_page(identity, q="train-example").games[0].id == 1
    assert collection_page(identity, lens="shortfall").total == 2
    assert collection_page(identity, lens="shortfall", phase="opening").total == 2
    assert collection_page(identity, lens="shortfall", phase="endgame").total == 0
    assert collection_page(identity, limit=2, offset=2).games[0].id == 3
    assert collection_page(identity, attempts=page.games[0].attempt).total == 1


def test_quality_audit_uses_accepted_selected_occurrences_and_distinct_budgets(collection):
    _, identity = collection
    q = collection_quality(identity)
    assert q.selected_occurrences == 2 and q.unique_inputs == 1 and q.cross_split_inputs == 1
    assert (q.affected_train, q.affected_validation) == (1, 1)
    assert q.single_pv_budget_coverage == {"2": 1, "1": 1}
    assert q.specs[0].occurrences == 2  # Repeated success for the same spec counts once.
    assert q.overlap_examples[0].train_game == 1 and q.overlap_examples[0].validation_game == 2


def test_replay_analysis_resolution_and_evidence_are_readonly(collection):
    path, identity = collection
    before = path.read_bytes()
    d = game_detail(identity, 1)
    assert d.snapshot.moves == ["b0c2", "b9c7"]
    assert [a.id for a in d.occurrences[0].analyses if a.resolved] == [1, 2]
    assert game_position(identity, 1, 1).board == Snapshot(moves=["b0c2"]).game().board
    assert analysis_evidence(identity, 1, 1).answer.move == "b0c2"
    assert game_detail(identity, 3).duplicate_games == [1]
    with pytest.raises(ValueError, match="beyond"):
        game_position(identity, 1, 3)
    with pytest.raises(ValueError, match="not found"):
        analysis_evidence(identity, 2, 1)
    assert path.read_bytes() == before


def test_reader_does_not_recover_or_lock_live_writer(collection):
    path, identity = collection
    with Collection(path) as writer:
        gid = writer.begin_game(
            2,
            "live",
            GamePayload(
                source_id="live",
                family="live",
                split="train",
                mode="random",
                initial=Snapshot(),
                snapshot=Snapshot(),
                actor={},
            ),
        )
        changes = writer.db.total_changes
        assert collection_page(identity).games[0].id == gid
        assert game_detail(identity, gid).game.status == "running"
        assert writer.db.total_changes == changes
        assert writer.db.execute("SELECT status FROM games WHERE id=?", (gid,)).fetchone()[0] == "running"


def test_discovery_isolated_and_http_paths_bounded(collection, monkeypatch, tmp_path):
    path, identity = collection
    bad = tmp_path / "bad.sqlite"
    bad.write_bytes(b"not sqlite")
    link = tmp_path / "link.sqlite"
    link.symlink_to(path)
    monkeypatch.setenv("QI_COLLECTION_PATHS", f"{path}:{bad}:{link}")
    catalog = discover_collections()
    assert len(catalog.collections) == 1 and len(catalog.issues) == 1
    with TestClient(create_app()) as client:
        assert client.get("/data").status_code == 200
        assert client.get(f"/api/collections/{identity}").json()["overall"]["accepted"] == 2
        assert client.get(f"/api/collections/{identity}?limit=101").status_code == 422
        assert client.get(f"/api/collections/{identity}?offset=-1").status_code == 422
        assert client.get("/api/collections/not-a-local-id").status_code == 409
        assert client.get(f"/api/collections/{identity}/quality").json()["cross_split_inputs"] == 1
        assert client.get(f"/api/collections/{identity}/games/1/analyses/1").status_code == 200
        assert client.post(f"/api/collections/{identity}").status_code == 405


def test_tampered_outcome_fails_replay_validation(collection):
    path, identity = collection
    with sqlite3.connect(path) as db:
        db.execute("UPDATE games SET outcome=? WHERE id=1", (json.dumps({"winner": "red", "reason": "checkmate"}),))
    with pytest.raises(ValueError, match="referee replay"):
        game_detail(identity, 1)


def test_unknown_schema_and_empty_collection_are_explicit(tmp_path, monkeypatch):
    path = tmp_path / "empty.sqlite"
    with Collection(path):
        pass
    monkeypatch.setenv("QI_COLLECTION_PATHS", str(path))
    identity = discover_collections().collections[0].id
    assert collection_page(identity).overall.mean_plies is None
    assert collection_quality(identity).selected_occurrences == 0
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=99")
    assert "Unsupported collection schema 99" in discover_collections().issues[0]
    with pytest.raises(ValueError, match="schema 99"):
        collection_page(identity)
    with pytest.raises(GameError, match="not found"):
        collection_page("../../etc/passwd")
