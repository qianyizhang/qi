"""Installed command integration check."""

import json
import subprocess
from importlib.metadata import version


def test_installed_cli_version() -> None:
    result = subprocess.run(["qi", "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == version("qi")
    assert result.stderr == ""


def test_invalid_arguments_are_structured() -> None:
    result = subprocess.run(["qi", "apply"], capture_output=True, text=True)
    assert result.returncode == 2
    assert not result.stdout
    assert '"code": "invalid_arguments"' in result.stderr


def test_installed_catalog_gate_propagates_command_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QI_WORKSPACE", str(tmp_path))
    command = ["qi", "experiment", "check-catalog", "--summary"]
    valid = subprocess.run(command, capture_output=True, text=True, check=True)
    assert json.loads(valid.stdout)["issues"] == []

    owner = tmp_path / "records/work-items/items/broken.md"
    owner.parent.mkdir(parents=True)
    owner.write_text("# Invalid catalog record\n\n```experiment\n{}\n```\n")
    invalid = subprocess.run(command, capture_output=True, text=True)
    assert invalid.returncode == 1
    assert json.loads(invalid.stdout)["issues"]
    assert invalid.stderr == ""
