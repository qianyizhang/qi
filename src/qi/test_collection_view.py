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


@pytest.fixture
def projection_collection(tmp_path, monkeypatch):
    """Fixed indexed summaries; replay validity is covered by the detail tests above."""
    path = tmp_path / "projection.sqlite"
    # id, run, policy, split, status, generated plies, initial plies, outcome, reason
    rows = [
        (1, 1, "random", "train", "complete", 49, 1, "red", "checkmate"),
        (2, 1, "plausible", "train", "complete", 50, 2, None, "repetition"),
        (3, 1, "random", "validation", "complete", 249, 1, "black", "checkmate"),
        (4, 2, "plausible", "train", "complete", 250, 0, None, None),
        (5, 2, "random", "validation", "complete", 299, 1, None, "ply-limit"),
        (6, 2, "plausible", "train", "complete", 300, 0, None, "repetition"),
        (7, 2, "random", "validation", "failed", 100, 0, None, None),
        (8, 2, "random", "train", "failed", 150, 0, None, None),
        (9, 2, "plausible", "validation", "failed", 250, 0, None, None),
        (10, 2, "random", "train", "running", 0, 0, None, None),
        (11, 2, "plausible", "train", "interrupted", 300, 0, None, None),
        (12, 1, "random", "train", "complete", 100, 0, "red", "stalemate"),
        (13, 2, "plausible", "validation", "complete", 150, 0, None, None),
    ]
    # selected count, actual, requested, shortfall; preserve zero-valued phase keys.
    sampling = {
        1: (2, {"opening": 1, "middlegame": 1, "endgame": 0}, {"opening": 3, "middlegame": 1}, {"opening": 2}),
        2: (3, {"opening": 1, "middlegame": 2}, {"opening": 1, "middlegame": 2}, {}),
        3: (1, {"endgame": 1}, {"endgame": 2}, {"endgame": 1}),
        5: (1, {"unknown": 1}, {"unknown": 1, "opening": 0}, {}),
        6: (0, {"opening": 0}, {"opening": 0}, {}),
        7: (100, {"opening": 100}, {"opening": 200}, {"opening": 100}),
        8: (100, {"opening": 100}, {"opening": 200}, {"opening": 100}),
    }
    with Collection(path) as store:
        for seed in range(1, 4):
            store.run(RunPayload(config={}, provenance={}, seed=seed, planned_games=13))
        for gid, run, policy, split, status, length, start, winner, reason in rows:
            payload = GamePayload(
                source_id="École%_ Straẞe" if gid == 1 else f"Source {gid}",
                family=str(gid),
                split=split,
                mode="random",
                initial=Snapshot(),
                snapshot=Snapshot(),
                actor={"source": f"Actor {gid}", "policy": {"mode": policy}} if policy == "plausible" else {},
            )
            assert store.begin_game(run, str(gid), payload) == gid
            data = payload.model_dump()
            data["initial"]["moves"] = ["a0a1"] * start
            data["snapshot"]["moves"] = ["a0a1"] * (start + length)
            if gid in sampling:
                selected, actual, requested, shortfall = sampling[gid]
                data["actor"]["generation_result"] = {
                    "sampling": {
                        "selected": list(range(selected)),
                        "actual": actual,
                        "requested": requested,
                        "shortfall": shortfall,
                    }
                }
            with store.db:
                store.db.execute(
                    """UPDATE games SET attempt=?,status=?,stop_reason=?,failure=?,trajectory=?,
                      outcome=?,payload=jsonb(?) WHERE id=?""",
                    (
                        f"attempt-{gid}",
                        status,
                        "rejected-trajectory" if gid == 7 else "error" if gid in (8, 9) else "ply-budget",
                        "Exact trajectory crosses splits." if gid == 8 else "Teacher failed" if gid == 9 else None,
                        "shared-trajectory" if gid in (1, 2, 7) else f"trajectory-{gid}",
                        json.dumps({"winner": winner, "reason": reason}) if reason else None,
                        json.dumps(data),
                        gid,
                    ),
                )
    monkeypatch.setenv("QI_COLLECTION_PATHS", str(path))
    return discover_collections().collections[0].id


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"run": 1}, [12, 3, 2, 1]),
        ({"run": 3}, []),
        ({"policy": "random"}, [12, 10, 8, 7, 5, 3, 1]),
        ({"split": "validation"}, [13, 9, 7, 5, 3]),
        ({"disposition": "accepted"}, [13, 12, 6, 5, 4, 3, 2, 1]),
        ({"disposition": "rejected"}, [8, 7]),
        ({"disposition": "failed"}, [9]),
        ({"disposition": "running"}, [10]),
        ({"disposition": "interrupted"}, [11]),
        ({"outcome": "red"}, [12, 1]),
        ({"outcome": "red · checkmate"}, [1]),
        ({"outcome": "black"}, [3]),
        ({"outcome": "draw"}, [6, 5, 2]),
        ({"outcome": "draw · repetition"}, [6, 2]),
        ({"outcome": "unfinished"}, [13, 11, 10, 9, 8, 7, 4]),
        ({"q": "ÉCOLE"}, [1]),
        ({"q": "STRAẞE"}, [1]),
        ({"q": "STRASSE"}, []),  # str.lower(), not Unicode casefold().
        ({"q": "%_"}, [1]),  # SQL wildcard characters are literal substrings.
        ({"q": "3"}, [13, 3]),
        ({"q": "Actor"}, [13, 11, 9, 6, 4, 2]),
        ({"q": "absent"}, []),
        ({"lens": "shortfall"}, [3, 1]),
        ({"lens": "shortfall", "phase": "opening"}, [1]),
        ({"lens": "shortfall", "phase": "middlegame"}, []),
        ({"lens": "shortfall", "phase": "endgame"}, [3]),
        ({"lens": "shortfall", "phase": "unknown"}, []),
        ({"lens": "long"}, [11, 9, 6, 5, 4]),
        ({"phase": "opening"}, [8, 7, 2, 1]),
        ({"phase": "middlegame"}, [2, 1]),
        ({"phase": "endgame"}, [3]),
        ({"phase": "unknown"}, [5]),
        ({"attempts": "attempt-2,attempt-12,attempt-2,absent"}, [12, 2]),
        ({"attempts": "attempt-1"}, [1]),
        ({"attempts": "attempt-100"}, []),
        ({"run": 2, "policy": "random", "split": "validation", "lens": "long", "phase": "unknown"}, [5]),
        ({"sort": "newest"}, [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
        ({"sort": "longest"}, [11, 6, 5, 9, 4, 3, 13, 8, 12, 7, 2, 1, 10]),
        ({"sort": "shortfall"}, [8, 7, 1, 3, 13, 12, 11, 10, 9, 6, 5, 4, 2]),
    ],
)
def test_collection_cohorts_and_sort_order(projection_collection, filters, expected):
    page = collection_page(projection_collection, **filters)
    assert [game.id for game in page.games] == expected
    assert page.total == page.filtered.attempts == len(expected)
    assert page.overall.attempts == 13
    assert page.overall.accepted == 8


def test_collection_aggregates_preserve_denominators_and_phase_totals(projection_collection):
    page = collection_page(projection_collection)
    assert page.overall.model_dump() == {
        "attempts": 13,
        "accepted": 8,
        "rejected": 2,
        "other": 3,
        "selected": 7,
        "shortfall_games": 2,
        "sampling_games": 5,
        "unique_trajectories": 7,
        "mean_plies": 180.875,
        "policies": {"random": 4, "plausible": 4},
        "splits": {"train": 5, "validation": 3},
        "outcomes": {"red": 2, "black": 1, "draw · repetition": 2, "draw · ply-limit": 1, "unfinished": 2},
        "lengths": {"0-49": 1, "50-99": 1, "100-149": 1, "150-199": 1, "200-249": 1, "250-299": 2, "300": 1},
        "actual": {"opening": 2, "middlegame": 3, "endgame": 1, "unknown": 1},
        "requested": {"opening": 4, "middlegame": 3, "endgame": 2, "unknown": 1},
    }
    assert page.filtered == page.overall
    first, second, empty = (page.run_stats[str(i)] for i in (1, 2, 3))
    assert (first.attempts, first.accepted, first.unique_trajectories, first.mean_plies) == (4, 4, 3, 112)
    assert (first.selected, first.shortfall_games, first.sampling_games) == (6, 2, 3)
    assert first.actual == {"opening": 2, "middlegame": 3, "endgame": 1}
    assert first.requested == {"opening": 4, "middlegame": 3, "endgame": 2}
    assert (second.attempts, second.accepted, second.rejected, second.other, second.mean_plies) == (9, 4, 2, 3, 249.75)
    assert (second.selected, second.shortfall_games, second.sampling_games) == (1, 0, 2)
    assert second.actual == {"opening": 0, "unknown": 1}
    assert second.requested == {"opening": 0, "unknown": 1}
    assert empty.model_dump() == {
        **dict.fromkeys(
            (
                "attempts",
                "accepted",
                "rejected",
                "other",
                "selected",
                "shortfall_games",
                "sampling_games",
                "unique_trajectories",
            ),
            0,
        ),
        "mean_plies": None,
        **{key: {} for key in ("policies", "splits", "outcomes", "lengths", "actual", "requested")},
    }
    assert collection_page(projection_collection, q="absent").filtered == empty
    rejected = collection_page(projection_collection, disposition="rejected").filtered
    assert rejected == empty.model_copy(update={"attempts": 2, "rejected": 2})
    assert collection_page(projection_collection, run=1).filtered == first


def test_collection_pagination_only_materializes_the_requested_page(projection_collection, monkeypatch):
    from qi import collection_view

    materialized = []
    original = collection_view._game

    def project(row):
        materialized.append(row["id"])
        return original(row)

    monkeypatch.setattr(collection_view, "_game", project)
    page = collection_page(projection_collection, disposition="accepted", sort="longest", offset=2, limit=2)
    assert materialized == [4, 3]
    assert [game.id for game in page.games] == [4, 3]
    assert (page.offset, page.limit, page.total, page.filtered.accepted) == (2, 2, 8, 8)
    assert page.filtered.mean_plies == 180.875
    assert page.filtered.selected == 7
    materialized.clear()
    past_end = collection_page(projection_collection, disposition="accepted", offset=8, limit=2)
    assert past_end.games == materialized == []
    assert past_end.filtered == page.filtered
