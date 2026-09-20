"""Frozen pre-extraction behavior and dependency isolation for the public boundary."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.referee import Referee
from qi_game.reference import Game, PythonReferee, inspect, replay

FROZEN = json.loads((Path(__file__).parent / "fixtures/referee-v1.json").read_text())


@pytest.mark.parametrize("case", FROZEN["replays"], ids=lambda case: case["name"])
def test_replay_and_guarded_apply_match_pre_extraction_results(case):
    backend: Referee = PythonReferee()
    expected = case["position"]
    snapshot = Snapshot.model_validate(expected["snapshot"])
    replay.cache_clear()
    assert backend.inspect(snapshot).model_dump() == expected
    if snapshot.moves:
        parent = Snapshot(moves=snapshot.moves[:-1])
        before = parent.model_dump()
        state_hash = backend.inspect(parent).state_hash
        assert backend.apply(parent, snapshot.moves[-1], state_hash).model_dump() == expected
        assert parent.model_dump() == before


@pytest.mark.parametrize("case", FROZEN["diagrams"], ids=lambda case: case["name"])
def test_terminal_precedence_matches_pre_extraction_results(case):
    state = case["state"]
    game = Game(state["board"], state["turn"], tuple(state["moves"]), tuple(state["positions"]))
    assert inspect(game).model_dump() == case["position"]


@pytest.mark.parametrize(
    "move,guard,code",
    [
        ("bad", "stale", "stale_state"),
        ("bad", None, "invalid_move"),
        ("a9a8", None, "wrong_player"),
        ("a0a9", None, "illegal_move"),
    ],
)
def test_failed_actions_do_not_modify_snapshot_or_future_results(move, guard, code):
    backend = PythonReferee()
    snapshot = Snapshot()
    expected = FROZEN["replays"][0]["position"]
    with pytest.raises(GameError) as error:
        backend.apply(snapshot, move, expected["state_hash"] if guard is None else guard)
    assert error.value.code == code
    assert snapshot.model_dump() == expected["snapshot"]
    assert backend.inspect(snapshot).model_dump() == expected


def test_terminal_snapshot_rejects_further_actions_and_stale_guard_takes_precedence():
    backend = PythonReferee()
    end = FROZEN["replays"][2]["position"]
    snapshot = Snapshot.model_validate(end["snapshot"])
    for guard, code in ((end["state_hash"], "game_over"), ("stale", "stale_state")):
        with pytest.raises(GameError) as error:
            backend.apply(snapshot, "bad", guard)
        assert error.value.code == code
    assert backend.inspect(snapshot).model_dump() == end


@pytest.mark.parametrize(
    "value",
    [
        {"schema_version": 2},
        {"ruleset": "unknown"},
        {"initial_fen": "arbitrary"},
        {"moves": ["a3a4"] * 301},
        {"moves": [1]},
        {"player": "random"},
    ],
)
def test_snapshot_rejects_unknown_interpretations(value):
    with pytest.raises(ValidationError):
        Snapshot.model_validate(value)


def test_contracts_load_without_implementation_and_reference_has_no_app_dependencies():
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import importlib.abc
import sys

class BlockApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        assert fullname.split('.')[0] not in {'qi', 'torch', 'numpy', 'fastapi', 'typer', 'pyarrow'}, fullname

sys.meta_path.insert(0, BlockApplication())
from qi_game.contracts import Snapshot
from qi_game.referee import Referee
assert 'qi_game.reference' not in sys.modules
from qi_game.reference import PythonReferee
assert len(PythonReferee().inspect(Snapshot()).legal_moves) == 44
""",
        ],
        check=True,
    )
