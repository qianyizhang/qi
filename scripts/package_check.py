"""Shared primitives for testing built distributions outside the checkout."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

CommandPart = str | os.PathLike[str]
StandardOutput = int | IO[Any] | None


@dataclass
class PackageRunner:
    """Run package checks without checkout imports or an implicit cache path."""

    root: Path
    environment: dict[str, str]

    @classmethod
    def create(
        cls,
        root: Path,
        environment: Mapping[str, str] | None = None,
    ) -> PackageRunner:
        root = root.resolve()
        clean_environment = dict(os.environ if environment is None else environment)
        cache_directory = Path(clean_environment.get("UV_CACHE_DIR", root / ".cache/uv"))
        if not cache_directory.is_absolute():
            cache_directory = root / cache_directory
        clean_environment["UV_CACHE_DIR"] = str(cache_directory)
        clean_environment.pop("PYTHONPATH", None)
        return cls(root=root, environment=clean_environment)

    def resolve_path(self, path: Path) -> Path:
        return path if path.is_absolute() else self.root / path

    def run(
        self,
        *command: CommandPart,
        cwd: Path | None = None,
        stdout: StandardOutput = None,
    ) -> None:
        subprocess.run(
            tuple(os.fspath(part) for part in command),
            cwd=self.root if cwd is None else self.resolve_path(cwd),
            env=self.environment,
            stdout=stdout,
            check=True,
        )

    def use_offline_cache(self) -> None:
        """Prevent installed-package checks from hiding missing dependencies."""

        self.environment["UV_OFFLINE"] = "true"


@dataclass(frozen=True)
class BuiltDistribution:
    sdist: Path
    wheel: Path


@dataclass(frozen=True)
class IsolatedEnvironment:
    root: Path

    @property
    def python(self) -> Path:
        return self.root / "bin/python"

    def executable(self, name: str) -> Path:
        return self.root / "bin" / name


def only_artifact(directory: Path, pattern: str) -> Path:
    """Return the one expected build artifact, rejecting stale or missing output."""

    if not directory.is_absolute():
        raise ValueError(f"artifact directory must be absolute: {directory}")
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one artifact matching {pattern!r} in {directory}, found {len(matches)}")
    return matches[0]


def build_distribution(
    runner: PackageRunner,
    package: str,
    sdist_directory: Path,
    *,
    wheel_directory: Path | None = None,
) -> BuiltDistribution:
    """Build a wheel from its sdist so the source archive is part of the test."""

    sdist_directory = runner.resolve_path(sdist_directory)
    wheel_directory = runner.resolve_path(wheel_directory or sdist_directory)
    prefix = package.replace("-", "_")
    runner.run(
        "uv",
        "build",
        "--package",
        package,
        "--sdist",
        "--out-dir",
        sdist_directory,
    )
    sdist = only_artifact(sdist_directory, f"{prefix}-*.tar.gz")
    runner.run("uv", "build", "--wheel", sdist, "--out-dir", wheel_directory, cwd=sdist_directory.parent)
    wheel = only_artifact(wheel_directory, f"{prefix}-*.whl")
    return BuiltDistribution(sdist=sdist, wheel=wheel)


def export_requirements(
    runner: PackageRunner,
    destination: Path,
    *,
    package: str | None = None,
    extras: Sequence[str] = (),
    no_dev: bool = False,
) -> None:
    destination = runner.resolve_path(destination)
    command: list[CommandPart] = ["uv", "export", "--locked"]
    if package is not None:
        command.extend(("--package", package))
    for extra in extras:
        command.extend(("--extra", extra))
    if no_dev:
        command.append("--no-dev")
    command.extend(("--no-emit-workspace", "--output-file", destination))
    runner.run(*command, stdout=subprocess.DEVNULL)


def create_isolated_environment(
    runner: PackageRunner,
    directory: Path,
    requirements: Path,
    wheels: Iterable[Path],
) -> IsolatedEnvironment:
    """Create a venv, install exported dependencies, then install local wheels only."""

    directory = runner.resolve_path(directory)
    requirements = runner.resolve_path(requirements)
    wheels = (runner.resolve_path(wheel) for wheel in wheels)
    environment = IsolatedEnvironment(directory)
    runner.run("uv", "venv", "--python", sys.executable, directory, cwd=directory.parent)
    runner.run(
        "uv",
        "pip",
        "install",
        "--python",
        environment.python,
        "-r",
        requirements,
        cwd=directory.parent,
    )
    runner.run(
        "uv",
        "pip",
        "install",
        "--python",
        environment.python,
        "--no-deps",
        *sorted(wheels),
        cwd=directory.parent,
    )
    return environment
