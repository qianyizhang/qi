"""Shared-reference pairing, frozen selection, unknown coverage and failure evidence."""

import json
from collections import Counter
from hashlib import sha256

import pytest
from qi_game.reference import legal_moves, restore

from qi.learning.teacher_quality import Study, prepare_inputs, run, summarize
from qi.learning.teacher_quality_scores import candidates, disadvantage
from qi.teacher import TeacherAnalysis


def reference(label):
    game = restore(label.analysis.snapshot)
    moves = sorted(legal_moves(game.board, game.turn))
    lines = [
        f"info depth 5 multipv {rank} score cp {-rank} wdl {1000 - rank} 0 {rank} pv {move}"
        for rank, move in enumerate(moves, 1)
    ]
    return label.analysis.model_copy(
        update={"search_info": lines, "settings": {"MultiPV": str(len(moves)), "UCI_ShowWDL": "true"}}
    )


def test_candidate_scores_use_complete_same_depth_not_last_line(tiny_dataset):
    analysis = reference(tiny_dataset.labels[0])
    parsed = candidates(analysis)
    first = next(iter(parsed["moves"]))
    assert disadvantage(parsed, first)["expected_score_loss"] == 0
    # An incomplete final update must not mix with the previous complete depth.
    extra = analysis.search_info[0].replace("depth 5", "depth 6").replace("score cp -1", "score cp -999")
    assert candidates(analysis.model_copy(update={"search_info": [*analysis.search_info, extra]})) == parsed
    incomplete = candidates(analysis.model_copy(update={"search_info": analysis.search_info[:-1]}))
    assert incomplete["status"] == "unknown"
    assert disadvantage(incomplete, first)["expected_score_loss"] is None
    bounded = analysis.model_copy(
        update={"search_info": [line.replace("score cp", "upperbound score cp") for line in analysis.search_info]}
    )
    assert candidates(bounded)["status"] == "unknown"
    mate = candidates(
        analysis.model_copy(
            update={
                "search_info": [
                    analysis.search_info[0].replace("score cp -1", "score mate 2"),
                    *analysis.search_info[1:],
                ]
            }
        )
    )
    assert disadvantage(mate, first)["cp_gap"] is None
    assert disadvantage(mate, first)["mate"] == 2


@pytest.fixture
def study_setup(tiny_dataset, tmp_path):
    import qi.learning.teacher_quality as module

    empty_hash = sha256(b"").hexdigest()
    dataset = tiny_dataset.model_copy(
        update={
            "labels": [
                label.model_copy(
                    update={
                        "analysis": label.analysis.model_copy(
                            update={
                                "requested_nodes": 1000,
                                "requested_depth": 3,
                                "engine_sha256": empty_hash,
                                "network_sha256": empty_hash,
                                "settings": {"Threads": "1", "Hash": "16", "MultiPV": "1", "Ponder": "false"},
                            }
                        )
                    }
                )
                for label in tiny_dataset.labels
            ]
        }
    )
    path = tmp_path / "parent.json"
    path.write_text(dataset.model_dump_json())
    counts = Counter(source.split for source in dataset.sources)
    study = Study(
        datasets=[str(path)],
        dataset_file_sha256=[sha256(path.read_bytes()).hexdigest()],
        engine=str(tmp_path / "fake-engine"),
        network=str(tmp_path / "fake-network"),
        engine_sha256=empty_hash,
        network_sha256=empty_hash,
        train_positions=len(dataset.split_labels("train")),
        train_games=counts["train"],
        validation_games=counts["validation"],
        seeds=[7],
        updates=2,
        seconds=60,
    )
    lookup = {label.analysis.state_hash: label for label in dataset.labels}

    class Session:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def analyze(self, game, config):
            assert config.depth is None
            label = lookup[game.state_hash]
            original = reference(label) if config.show_wdl else label.analysis
            return TeacherAnalysis.model_validate(
                original.model_copy(
                    update={
                        "schema_version": 2,
                        "adapter_version": "uci-teacher-v2",
                        "requested_nodes": config.nodes,
                        "requested_depth": None,
                        "settings": {"MultiPV": str(config.multipv), "UCI_ShowWDL": str(config.show_wdl).lower()},
                    }
                ).model_dump()
            )

    return module, study, Session


def test_selection_is_data_only_and_rejects_changed_parent(study_setup):
    _module, study, _ = study_setup
    first, protocol = prepare_inputs(study)
    assert prepare_inputs(study)[1] == protocol
    assert len(first[0].split_labels("validation")) == study.validation_games
    with pytest.raises(ValueError, match="bytes changed"):
        prepare_inputs(study.model_copy(update={"dataset_file_sha256": ["0" * 64]}))


def test_complete_paired_run_and_corruption(study_setup, tmp_path, monkeypatch):
    from qi.learning.teacher_quality_verify import verify

    pytest.importorskip("torch")
    module, study, session = study_setup
    monkeypatch.setattr(module, "TeacherSession", session)
    output = tmp_path / "study"
    result = run(study, output)
    assert result["status"] == "complete", result.get("error")
    assert result["summary"]["completed_fits"] == 2
    assert result["summary"]["outcome"] == "inconclusive"  # identical supervision => no improvement
    a, b = result["trials"]
    assert a["evaluation_inputs"] == b["evaluation_inputs"]
    assert a["evaluation"]["agreement"] == b["evaluation"]["agreement"]
    assert json.loads((output / "protocol.json").read_text())["support"]["nodes"] == 1_000_000
    torch = pytest.importorskip("torch")
    torch.set_num_threads(2)
    messages = []

    def progress(message):
        assert torch.get_num_threads() == 1
        messages.append(message)

    try:
        assert verify(output, progress=progress)["verified"]
        assert torch.get_num_threads() == 2
        assert any("block 1/1" in message for message in messages)
        receipt_path = output / "receipts.json"
        original_receipts = receipt_path.read_text()
        receipts = json.loads(original_receipts)
        receipts.pop("block-0-baseline-seed-7.pt")
        receipt_path.write_text(json.dumps(receipts))
        with pytest.raises(ValueError, match="Missing checkpoint receipt"):
            verify(output)
        assert torch.get_num_threads() == 2
        receipt_path.write_text(original_receipts)
        answers_path = output / "answers.jsonl"
        original_answers = answers_path.read_text()
        answers = [json.loads(line) for line in original_answers.splitlines()]
        answers[0]["analysis"]["state_hash"] = "wrong-input"
        answers_path.write_text("\n".join(json.dumps(row) for row in answers) + "\n")
        receipts = json.loads(original_receipts)
        receipts["answers.jsonl"] = sha256(answers_path.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipts))
        with pytest.raises(ValueError, match="changed the frozen input"):
            verify(output)
        answers_path.write_text(original_answers)
        receipt_path.write_text(original_receipts)
    finally:
        torch.set_num_threads(1)
    rows = json.loads((output / "status.json").read_text())["trials"]
    rows[1]["evaluation_inputs"] = ["wrong"]
    with pytest.raises(ValueError, match="different inputs"):
        summarize(rows, study)
    with pytest.raises(FileExistsError):
        run(study, output)
    partial = summarize(result["trials"][:1], study)
    assert partial["completed_fits"] == 1 and partial["complete_blocks"] == 0
    for row in result["trials"]:
        row["disadvantages"][0] = disadvantage({"status": "unknown"}, "unused")
    unknown = summarize(result["trials"], study)
    assert not unknown["blocks"][0]["support_complete"]
    assert unknown["blocks"][0]["disadvantage_delta"] is None
    (output / "block-0-baseline-seed-7.evaluation.json").write_text("{}")
    with pytest.raises(ValueError, match="Receipt mismatch"):
        verify(output)


def test_failed_preparation_keeps_answers_and_planned_denominators(study_setup, tmp_path, monkeypatch):
    pytest.importorskip("torch")
    module, study, session = study_setup
    original = session.analyze
    calls = 0

    def fail(self, game, config):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("query failed")
        return original(self, game, config)

    monkeypatch.setattr(session, "analyze", fail)
    monkeypatch.setattr(module, "TeacherSession", session)
    result = run(study, tmp_path / "failed")
    assert result["status"] == "failed"
    assert result["queries"] == 1
    assert result["summary"]["planned_fits"] == 2 and result["summary"]["completed_fits"] == 0
    assert result["summary"]["agreement_delta"] is None
    assert len((tmp_path / "failed/answers.jsonl").read_text().splitlines()) == 1


def test_deadline_does_not_shrink_matrix(study_setup, tmp_path, monkeypatch):
    pytest.importorskip("torch")
    module, study, session = study_setup
    monkeypatch.setattr(module, "TeacherSession", session)
    ticks = iter(range(0, 100_000, 1000))
    monkeypatch.setattr(module, "perf_counter", lambda: next(ticks))
    result = run(study, tmp_path / "deadline")
    assert result["status"] == "deadline"
    assert result["summary"]["planned_fits"] == 2 and result["queries"] == 0


@pytest.mark.parametrize("seeds", [[-1, 2**64 - 1], [2**64], [-(2**63) - 1]])
def test_invalid_seeds_fail_before_preparation(study_setup, seeds):
    _, study, _ = study_setup
    with pytest.raises(ValueError, match="PyTorch initializations"):
        Study.model_validate({**study.model_dump(), "seeds": seeds})


def test_preflight_failure_receipts_are_verifiable(study_setup, tmp_path):
    from qi.learning.teacher_quality_verify import verify

    pytest.importorskip("torch")
    _, study, _ = study_setup
    output = tmp_path / "bad-parent"
    result = run(study.model_copy(update={"dataset_file_sha256": ["0" * 64]}), output)
    assert result["status"] == "failed"
    verified = verify(output)
    assert verified["scope"] == "preflight-failure-receipts"
    assert verified["summary"]["completed_fits"] == 0


def test_script_rejects_conflicting_modes_and_reports_missing_file(tmp_path, monkeypatch, capsys):
    import runpy
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[3] / "scripts/run_teacher_quality.py"
    monkeypatch.setattr(sys, "argv", [str(script), "--verify", "--config", "ignored.json", "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as failure:
        runpy.run_path(str(script), run_name="__main__")
    assert failure.value.code == 2
    assert "not allowed" in capsys.readouterr().err
    monkeypatch.setattr(
        sys, "argv", [str(script), "--config", str(tmp_path / "missing.json"), "--output", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as failure:
        runpy.run_path(str(script), run_name="__main__")
    assert failure.value.code == 1
    captured = capsys.readouterr()
    assert json.loads(captured.err)["status"] == "error"
    assert "Traceback" not in captured.err and not captured.out
