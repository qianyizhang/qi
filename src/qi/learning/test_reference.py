"""Reference preview and fixture identities remain teacher/torch independent."""

import json
import runpy
from pathlib import Path

from typer.testing import CliRunner

from qi.cli import app
from qi.learning.reference import BUNDLE
from qi.training_data.loading import load_dataset


def test_reference_preview_and_deterministic_fixture(tmp_path):
    output = tmp_path / "unused"
    result = CliRunner().invoke(app, ["learn", "reference", "--preview", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert not output.exists()
    preview = json.loads(result.stdout)
    assert preview["planned_trials"] == 1
    assert len(preview["trials"][0]["train_inputs"]) == 8
    assert len(preview["validation_inputs"]) == 4
    builder = Path(__file__).resolve().parents[3] / "scripts/build_reference_fixture.py"
    regenerated = runpy.run_path(str(builder))["build_fixture"]()
    assert regenerated == load_dataset(BUNDLE / "dataset.json")
    assert regenerated.digest == preview["expected"]["dataset_sha256"]
