"""Shared content identity and atomic persistence for local evidence artifacts."""

import hashlib
import json
import os
import subprocess
from importlib.metadata import version
from pathlib import Path
from platform import platform, python_version
from tempfile import NamedTemporaryFile
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]


class SourceProvenance(TypedDict):
    source_sha256: str | None
    commit: str | None
    working_tree: str | None


class Provenance(SourceProvenance):
    python: str
    platform: str
    packages: dict[str, str]


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def source_provenance(*, include_assets: bool = True, paths: tuple[str, ...] = ()) -> SourceProvenance:
    source_root = ROOT / "src/qi"
    dependencies = [ROOT / "pyproject.toml", ROOT / "uv.lock"]
    # CONTRACT: An installed package cannot claim a source-and-lockfile checkout identity.
    if not source_root.is_dir() or not all(path.is_file() for path in dependencies):
        return {"source_sha256": None, "commit": None, "working_tree": None}
    suffixes = (".py", ".html", ".js", ".css") if include_assets else (".py",)
    files = sorted(
        path
        for path in source_root.rglob("*")
        if path.suffix in suffixes and (not include_assets or "static" not in path.parts)
    )
    files += dependencies
    source = hashlib.sha256()
    for path in files:
        source.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")

    def git(*args):
        try:
            result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False)
        except OSError:
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    return {
        "source_sha256": source.hexdigest(),
        "commit": git("rev-parse", "HEAD"),
        "working_tree": git("status", "--porcelain", *(("--", *paths) if paths else ())),
    }


def provenance() -> Provenance:
    return {
        **source_provenance(),
        "python": python_version(),
        "platform": platform(),
        "packages": {name: version(name) for name in ("qi", "pydantic")},
    }


def write_json(path: Path, data, *, indent: int | None = None) -> None:
    stream = NamedTemporaryFile(mode="w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
    temporary = Path(stream.name)
    try:
        with stream:
            json.dump(
                data, stream, indent=indent, allow_nan=False, separators=None if indent is not None else (",", ":")
            )
            if indent is not None:
                stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
