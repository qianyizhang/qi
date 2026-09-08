"""Shared content identity and atomic persistence for local evidence artifacts."""

import hashlib
import json
import os
import subprocess
from importlib.metadata import version
from pathlib import Path
from platform import platform, python_version
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]


class Provenance(TypedDict):
    source_sha256: str
    commit: str | None
    working_tree: str | None
    python: str
    platform: str
    packages: dict[str, str]


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def provenance() -> Provenance:
    files = sorted(
        path
        for path in (ROOT / "src/qi").rglob("*")
        if path.suffix in (".py", ".html", ".js", ".css") and "static" not in path.parts
    )
    files += [ROOT / "pyproject.toml", ROOT / "uv.lock"]
    source = hashlib.sha256()
    for path in files:
        source.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")

    def git(*args):
        result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    return {
        "source_sha256": source.hexdigest(),
        "commit": git("rev-parse", "HEAD"),
        "working_tree": git("status", "--porcelain"),
        "python": python_version(),
        "platform": platform(),
        "packages": {name: version(name) for name in ("qi", "pydantic")},
    }


def write_json(path: Path, data) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        json.dump(data, stream, allow_nan=False, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
