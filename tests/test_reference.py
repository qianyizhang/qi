"""Real reference execution and failures at the retained-artifact boundary."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from qi.cli import app
from qi.learning.reference import verify_reference

pytest.importorskip("torch")


@pytest.fixture(scope="module")
def reference_run(tmp_path_factory):
    output = tmp_path_factory.mktemp("reference") / "run"
    result = CliRunner().invoke(app, ["learn", "reference", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "passed"
    return output


def test_reference_verifies_saved_artifacts_and_preserves_existing_run(reference_run):
    before = (reference_run / "verification.json").read_bytes()
    result = CliRunner().invoke(app, ["learn", "reference", "--output", str(reference_run)])
    assert result.exit_code != 0
    assert (reference_run / "verification.json").read_bytes() == before
    assert verify_reference(reference_run)["status"] == "passed"


def test_reverification_checks_current_checkpoint_bytes(reference_run, tmp_path):
    output = tmp_path / "run"
    shutil.copytree(reference_run, output)
    assert verify_reference(output)["status"] == "passed"
    next(output.glob("*.pt")).write_bytes(b"changed after the first verification")
    result = verify_reference(output)
    assert result["status"] == "failed"
    assert result["checks"]["checkpoint_bytes"] is False


def test_reference_metric_failure_exits_nonzero_and_keeps_artifacts(tmp_path, monkeypatch):
    from qi.learning import reference

    bundle = tmp_path / "bundle"
    shutil.copytree(reference.BUNDLE, bundle)
    expected = json.loads((bundle / "expected.json").read_text())
    expected["metrics"]["validation.cross_entropy"]["expected"] = 100.0
    (bundle / "expected.json").write_text(json.dumps(expected))
    monkeypatch.setattr(reference, "BUNDLE", bundle)
    output = tmp_path / "run"
    result = CliRunner().invoke(app, ["learn", "reference", "--output", str(output)])
    assert result.exit_code != 0
    checks = json.loads((output / "verification.json").read_text())
    assert checks["status"] == "failed"
    assert checks["checks"]["validation.cross_entropy"] is False
    assert (output / "summary.json").is_file()
    assert len(list(output.glob("*.pt"))) == 1


@pytest.mark.parametrize("corruption", ["config", "metric", "checkpoint", "missing", "incomplete"])
def test_reference_rejects_corrupted_evidence(reference_run, tmp_path, corruption):
    output = tmp_path / "run"
    shutil.copytree(reference_run, output)
    if corruption == "config":
        path = output / "config.json"
        value = json.loads(path.read_text())
        value["training"]["seed"] += 1
        path.write_text(json.dumps(value))
    elif corruption in {"metric", "incomplete"}:
        path = output / "summary.json"
        value = json.loads(path.read_text())
        if corruption == "metric":
            value["trials"][0]["report"]["validation"]["cross_entropy"] += 10
        else:
            value["status"] = "incomplete"
        path.write_text(json.dumps(value))
    elif corruption == "checkpoint":
        next(output.glob("*.pt")).write_bytes(b"corrupted checkpoint")
    else:
        (output / "dataset.json").unlink()
    result = verify_reference(output)
    assert result["status"] == "failed"
    assert any(not passed for passed in result["checks"].values())
    assert json.loads((output / "verification.json").read_text())["status"] == "failed"
