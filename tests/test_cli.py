"""Installed command integration check."""

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
