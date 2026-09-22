"""Build sdist -> wheel, install locked dependencies, then reproduce outside the checkout."""

import argparse
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from package_check import PackageRunner, build_distribution, create_isolated_environment, export_requirements

EXCLUDED_APPLICATION_SOURCES = {
    ".agents",
    ".claude",
    ".codex",
    "data",
    "docs",
    "packages",
    "records",
    "scripts",
    "tests",
    "web",
}


def check_application_sdist(archive: Path) -> None:
    """Keep repository governance and source-only UI files out of the app sdist."""

    with tarfile.open(archive, "r:gz") as distribution:
        top_level_entries = {
            parts[1] for member in distribution.getmembers() if len(parts := Path(member.name).parts) > 1
        }
    leaked_sources = sorted(top_level_entries & EXCLUDED_APPLICATION_SOURCES)
    if leaked_sources:
        raise RuntimeError(f"application sdist contains repository-only paths: {', '.join(leaked_sources)}")


def check_package(output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    runner = PackageRunner.create(root)

    dist = output / "dist"
    game_distribution = build_distribution(runner, "qi-game", dist)
    application_distribution = build_distribution(runner, "qi", dist)
    check_application_sdist(application_distribution.sdist)
    requirements = output / "requirements.txt"
    export_requirements(runner, requirements, extras=("learning",), no_dev=True)
    with TemporaryDirectory(prefix="qi-package-") as directory:
        work = Path(directory).resolve()
        environment = create_isolated_environment(
            runner,
            work / "venv",
            requirements,
            (game_distribution.wheel, application_distribution.wheel),
        )
        runner.use_offline_cache()
        runner.run(
            environment.python,
            "-I",
            "-c",
            "from qi.learning.provenance import source_identity; "
            "p=source_identity(); "
            "assert all(p[k] is None for k in ('source_sha256','git_revision','git_dirty')), p",
            cwd=work,
        )
        with (output / "stdout.json").open("w") as stream:
            runner.run(
                environment.executable("qi"),
                "learn",
                "reference",
                "--output",
                output / "run",
                cwd=work,
                stdout=stream,
            )
    print(f"Installed-package reference passed: {output / 'run/verification.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    check_package(parser.parse_args().output)
