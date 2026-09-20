"""Evidence persistence preserves bytes and never invents a checkout identity."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from qi import artifacts
from qi.learning.provenance import source_identity


@pytest.mark.parametrize("indent", [None, 2])
def test_atomic_json_keeps_existing_compact_and_learning_formats(tmp_path, indent):
    path = tmp_path / "evidence.json"
    value = {"name": "棋", "values": [1, None]}
    expected = json.dumps(value, separators=(",", ":")) if indent is None else json.dumps(value, indent=2) + "\n"
    artifacts.write_json(path, value, indent=indent)
    assert path.read_bytes() == expected.encode()
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("failure", ["serialization", "replace"])
def test_failed_write_preserves_previous_evidence_and_removes_temporary(tmp_path, monkeypatch, failure):
    path = tmp_path / "evidence.json"
    path.write_text('{"previous":true}')
    value = {"next": float("nan") if failure == "serialization" else True}
    if failure == "replace":

        def fail_replace(*args):
            raise OSError("injected replacement failure")

        monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises((ValueError, OSError)):
        artifacts.write_json(path, value)
    assert path.read_text() == '{"previous":true}'
    assert list(tmp_path.iterdir()) == [path]


@pytest.fixture
def source_tree(tmp_path, monkeypatch):
    files = {
        "src/qi/a.py": "a",
        "src/qi/report.js": "report",
        "src/qi/sub/b.py": "b",
        "src/qi/static/bundle.js": "generated",
        "docs/project.md": "documentation",
        "pyproject.toml": "project",
        "uv.lock": "lock",
    }
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    monkeypatch.setattr(artifacts, "ROOT", tmp_path)
    return tmp_path


def test_source_hash_profiles_preserve_their_existing_coverage(source_tree, monkeypatch):
    commands = []

    def git(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "revision\n" if "rev-parse" in command else "")

    monkeypatch.setattr(artifacts.subprocess, "run", git)
    python_bytes = b"src/qi/a.py\0a\0src/qi/sub/b.py\0b\0pyproject.toml\0project\0uv.lock\0lock\0"
    assets_bytes = (
        b"src/qi/a.py\0a\0src/qi/report.js\0report\0src/qi/sub/b.py\0b\0pyproject.toml\0project\0uv.lock\0lock\0"
    )
    learning = source_identity()
    search = artifacts.provenance()
    assert learning["source_sha256"] == hashlib.sha256(python_bytes).hexdigest()
    assert search["source_sha256"] == hashlib.sha256(assets_bytes).hexdigest()
    assert learning["git_revision"] == search["commit"] == "revision"
    assert learning["git_dirty"] is False and search["working_tree"] == ""
    assert commands[1][-7:] == ["status", "--porcelain", "--", "src/qi", "packages", "pyproject.toml", "uv.lock"]
    assert commands[3][-2:] == ["status", "--porcelain"]


def test_missing_git_retains_available_source_identity(source_tree, monkeypatch):
    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(artifacts.subprocess, "run", missing_git)
    source = artifacts.source_provenance()
    assert source["source_sha256"] is not None
    assert source["commit"] is source["working_tree"] is None


def test_game_package_code_and_dependencies_change_execution_identity(source_tree):
    previous = artifacts.source_provenance()["source_sha256"]
    for name in ("packages/qi-game/pyproject.toml", "packages/qi-game/src/qi_game/reference.py"):
        path = source_tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("initial")
        added = artifacts.source_provenance()["source_sha256"]
        assert added != previous
        path.write_text("modified")
        changed = artifacts.source_provenance()["source_sha256"]
        assert changed != added
        assert source_identity()["source_sha256"] != previous
        previous = changed


def test_installed_layout_records_unknown_checkout_without_searching_parent_git(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "ROOT", tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("An installed package must not acquire an enclosing repository's identity.")

    monkeypatch.setattr(artifacts.subprocess, "run", forbidden)
    learning = source_identity()
    search = artifacts.provenance()
    assert learning["source_sha256"] is learning["git_revision"] is learning["git_dirty"] is None
    assert search["source_sha256"] is search["commit"] is search["working_tree"] is None
    assert learning["python"] and search["packages"]["qi"]
