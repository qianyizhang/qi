"""Hermetic subprocess tests for the local teacher boundary."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.reference import Game, replay, restore

from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherSession, analyze, digest, read_info


def fake_teacher(tmp_path: Path, mode: str = "ok") -> TeacherConfig:
    script = tmp_path / "fake-engine"
    script.write_text(f"""#!{sys.executable}
import os, sys, time
from pathlib import Path
mode = {mode!r}
queries = 0
Path({str(tmp_path / "pid")!r}).write_text(str(os.getpid()))
for raw in sys.stdin:
    command = raw.strip()
    with open({str(tmp_path / "commands")!r}, "a") as log:
        log.write(command + "\\n")
    if command == "uci":
        if mode == "hang":
            print("unfinished", end="", flush=True)
            time.sleep(20)
        if mode == "flood":
            print("x" * 1_100_000, flush=True)
        if mode == "exit":
            sys.exit(3)
        print("id name Fake Teacher 1")
        for name in ("Threads", "Hash", "MultiPV", "Ponder", "EvalFile"):
            if mode != "missing-option":
                print("option name " + name + " type string")
        print("uciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("go "):
        queries += 1
        if queries == 2:
            if mode == "late-hang":
                time.sleep(20)
            if mode == "late-exit":
                sys.exit(3)
            if mode == "late-flood":
                print("x" * 1_100_000, flush=True)
            if mode == "late-illegal":
                print("bestmove a0a9", flush=True)
                continue
        if mode == "large-ok":
            print("info string " + "x" * 600_000)
        print("info depth 3 nodes 42 score mate -2 upperbound pv b9c7")
        move = "a0a9" if mode == "illegal" else "b9c7"
        if mode == "none":
            move = "(none)"
        if mode == "malformed":
            print("bestmove b9c7 extra", flush=True)
        else:
            print("bestmove " + move, flush=True)
""")
    script.chmod(0o700)
    network = tmp_path / "fake.nnue"
    network.write_bytes(b"fake network")
    return TeacherConfig(script, network, nodes=100, depth=3, timeout_seconds=2)


def test_teacher_full_history_identity_perspective_and_no_mutation(tmp_path) -> None:
    config = fake_teacher(tmp_path)
    game = replay(("b2e2",))
    before = game.state_hash
    result = analyze(game, config)
    assert result.move == "b9c7"
    assert game.state_hash == before == result.state_hash
    assert restore(result.snapshot) == game
    assert result.engine_sha256 == digest(config.engine)
    assert result.network_sha256 == digest(config.network)
    assert result.engine_name == "Fake Teacher 1"
    assert result.score.kind == "mate" and result.score.value == -2
    assert result.score.bound == "upperbound" and result.score.perspective == "side_to_move"
    assert result.reported_nodes == 42 and result.reported_depth == 3
    assert TeacherAnalysis.model_validate_json(result.model_dump_json()) == result
    commands = (tmp_path / "commands").read_text().splitlines()
    assert commands == [
        "uci",
        "setoption name Threads value 1",
        "setoption name Hash value 16",
        "setoption name MultiPV value 1",
        "setoption name Ponder value false",
        f"setoption name EvalFile value {config.network.resolve()}",
        "ucinewgame",
        "isready",
        "position startpos moves b2e2",
        "go nodes 100 depth 3",
    ]
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


@pytest.mark.parametrize(
    ("mode", "code"),
    [
        ("hang", "teacher_timeout"),
        ("exit", "teacher_exit"),
        ("flood", "teacher_output_limit"),
        ("missing-option", "teacher_protocol"),
        ("illegal", "teacher_illegal_move"),
        ("none", "teacher_illegal_move"),
        ("malformed", "teacher_protocol"),
    ],
)
def test_teacher_failures_leave_no_process_or_move(tmp_path, mode, code) -> None:
    config = fake_teacher(tmp_path, mode)
    config = replace(config, timeout_seconds=2)
    game = replay(("b2e2",))
    with pytest.raises(GameError) as error:
        analyze(game, config)
    assert error.value.code == code
    assert game.moves == ("b2e2",)
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_teacher_terminal_and_forged_history_rejected_before_process(tmp_path) -> None:
    config = fake_teacher(tmp_path)
    with pytest.raises(GameError, match="after the game"):
        analyze(replay(("b0c2", "b9c7", "c2b0", "c7b9") * 2), config)
    with pytest.raises(GameError, match="must replay"):
        analyze(replace(Game(), turn="black"), config)
    assert not (tmp_path / "pid").exists()


@pytest.mark.parametrize("line", ["info nodes -1", "info depth x", "info score cp", "info score bogus 3"])
def test_malformed_search_information_is_rejected(line) -> None:
    with pytest.raises(GameError):
        read_info([line])


def test_teacher_cli_and_error_stream(tmp_path) -> None:
    config = fake_teacher(tmp_path)
    state = tmp_path / "state.json"
    state.write_text(Snapshot(moves=["b2e2"]).model_dump_json())
    command = ["qi", "teach", "--state", str(state), "--engine", str(config.engine), "--network", str(config.network)]
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    assert not result.stderr
    assert json.loads(result.stdout)["move"] == "b9c7"
    fake_teacher(tmp_path, "illegal")
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 1 and not result.stdout
    assert json.loads(result.stderr)["error"]["code"] == "teacher_illegal_move"


def test_session_reuses_process_resets_history_budget_and_identity(tmp_path, monkeypatch):
    config = fake_teacher(tmp_path, "large-ok")
    game = replay(("b2e2",))
    fresh = analyze(game, config)
    hashes = []
    original_digest = digest

    def counted(path):
        hashes.append(path)
        return original_digest(path)

    monkeypatch.setattr("qi.teacher.digest", counted)
    (tmp_path / "commands").unlink()
    with TeacherSession(config) as session:
        first = session.analyze(game, config)
        pid = int((tmp_path / "pid").read_text())
        second = session.analyze(replay(("h2e2",)), replace(config, nodes=200, depth=4))
        assert int((tmp_path / "pid").read_text()) == pid
        assert session.engine.process.poll() is None
        assert first.model_dump(exclude={"elapsed_ms"}) == fresh.model_dump(exclude={"elapsed_ms"})
        assert second.snapshot.moves == ["h2e2"]
        assert second.requested_nodes == 200 and second.requested_depth == 4
        assert hashes == [config.engine, config.network]
    commands = (tmp_path / "commands").read_text().splitlines()
    assert commands.count("uci") == 1
    assert commands.count("ucinewgame") == commands.count("isready") == 2
    assert commands[-4:] == ["ucinewgame", "isready", "position startpos moves h2e2", "go nodes 200 depth 4"]
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    with pytest.raises(GameError, match="closed"):
        session.analyze(game, config)


@pytest.mark.parametrize(
    "mode,code",
    [
        ("late-hang", "teacher_timeout"),
        ("late-exit", "teacher_exit"),
        ("late-flood", "teacher_output_limit"),
        ("late-illegal", "teacher_illegal_move"),
    ],
)
def test_late_session_failure_reaps_and_never_retries(tmp_path, mode, code):
    config = fake_teacher(tmp_path, mode)
    game = replay(("b2e2",))
    with TeacherSession(config) as session:
        session.analyze(game, config)
        with pytest.raises(GameError) as error:
            session.analyze(game, replace(config, timeout_seconds=0.1))
        assert error.value.code == code
        with pytest.raises(ProcessLookupError):
            os.kill(int((tmp_path / "pid").read_text()), 0)
        with pytest.raises(GameError, match="closed"):
            session.analyze(game, config)
    assert (tmp_path / "commands").read_text().splitlines().count("uci") == 1


def test_session_renews_query_deadline_and_rejects_different_files(tmp_path, monkeypatch):
    config = fake_teacher(tmp_path)
    game = replay(("b2e2",))
    with TeacherSession(config) as session:
        session.analyze(game, config)
        session.engine.deadline = 0
        session.analyze(game, config)
        other = tmp_path / "other.nnue"
        other.write_bytes(b"another network")
        with pytest.raises(GameError, match="same engine"):
            session.analyze(game, replace(config, network=other))
        assert session.closed
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_session_cancellation_reaps_process(tmp_path):
    config = fake_teacher(tmp_path)
    with pytest.raises(KeyboardInterrupt), TeacherSession(config) as session:
        session.analyze(replay(("b2e2",)), config)
        raise KeyboardInterrupt
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)
    assert session.closed


def test_node_only_queries_are_versioned_and_optional_output_settings_are_reset(tmp_path):
    config = fake_teacher(tmp_path)
    engine = config.engine.read_text().replace('"Ponder", "EvalFile")', '"Ponder", "EvalFile", "UCI_ShowWDL")')
    config.engine.write_text(engine)
    game = replay(("b2e2",))
    with TeacherSession(config) as session:
        first = session.analyze(game, replace(config, depth=None, multipv=2, show_wdl=True))
        second = session.analyze(game, config)
    assert first.requested_depth is None and first.schema_version == 2
    assert first.adapter_version == "uci-teacher-v2" and first.score is None
    assert first.settings["MultiPV"] == "2" and first.settings["UCI_ShowWDL"] == "true"
    assert second.settings["MultiPV"] == "1" and second.settings["UCI_ShowWDL"] == "false"
    assert second.schema_version == 1 and second.score.kind == "mate"
    assert TeacherAnalysis.model_validate_json(first.model_dump_json()) == first
    commands = (tmp_path / "commands").read_text().splitlines()
    assert [line for line in commands if line.startswith("go ")] == ["go nodes 100", "go nodes 100 depth 3"]
    assert commands.count("uci") == 1 and commands.count("ucinewgame") == 2


def test_optional_wdl_requires_engine_support(tmp_path):
    config = fake_teacher(tmp_path)
    with pytest.raises(GameError, match="UCI_ShowWDL"):
        with TeacherSession(config) as session:
            session.analyze(replay(("b2e2",)), replace(config, show_wdl=True))


def test_thread_changes_reach_engine_and_preserve_prior_evidence(tmp_path):
    config = fake_teacher(tmp_path)
    game = replay(("b2e2",))
    with TeacherSession(config) as session:
        first = session.analyze(game, config)
        second = session.analyze(game, replace(config, threads=4))
    assert first.settings["Threads"] == "1"
    assert second.settings["Threads"] == "4"
    assert "setoption name Threads value 4" in (tmp_path / "commands").read_text()
    from qi.teacher import TeacherIdentity
    from qi.training_data.generation_io import analysis_spec

    assert (
        analysis_spec(config, TeacherIdentity.read(config)).identity
        != analysis_spec(replace(config, threads=4), TeacherIdentity.read(config)).identity
    )


@pytest.mark.parametrize("threads", [0, 17, 1.5, True])
def test_invalid_thread_budget(tmp_path, threads):
    with pytest.raises(GameError, match="threads"):
        replace(fake_teacher(tmp_path), threads=threads)
