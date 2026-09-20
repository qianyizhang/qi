"""Build sdist -> wheel, install locked dependencies, then reproduce outside the checkout."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def check_package(output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "UV_CACHE_DIR": str(root / ".cache/uv")}
    env.pop("PYTHONPATH", None)

    def run(*args, cwd=root, stdout=None):
        subprocess.run(args, cwd=cwd, env=env, check=True, stdout=stdout)

    dist = output / "dist"
    for package in ("qi-game", "qi"):
        run("uv", "build", "--package", package, "--sdist", "--out-dir", str(dist))
    for archive in sorted(dist.glob("*.tar.gz")):
        run("uv", "build", "--wheel", str(archive), "--out-dir", str(dist))
    requirements = output / "requirements.txt"
    run(
        "uv",
        "export",
        "--locked",
        "--extra",
        "learning",
        "--no-dev",
        "--no-emit-workspace",
        "--output-file",
        str(requirements),
        stdout=subprocess.DEVNULL,
    )
    with TemporaryDirectory(prefix="qi-package-") as directory:
        work = Path(directory).resolve()
        python = work / "venv/bin/python"
        qi = work / "venv/bin/qi"
        run("uv", "venv", "--python", sys.executable, str(work / "venv"), cwd=work)
        run("uv", "pip", "install", "--python", str(python), "-r", str(requirements), cwd=work)
        run(
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            *map(str, sorted(dist.glob("*.whl"))),
            cwd=work,
        )
        env["UV_OFFLINE"] = "true"
        run(
            str(python),
            "-I",
            "-c",
            "from qi.learning.provenance import source_identity; "
            "p=source_identity(); "
            "assert all(p[k] is None for k in ('source_sha256','git_revision','git_dirty')), p",
            cwd=work,
        )
        with (output / "stdout.json").open("w") as stream:
            subprocess.run(
                [str(qi), "learn", "reference", "--output", str(output / "run")],
                cwd=work,
                env=env,
                check=True,
                stdout=stream,
            )
    print(f"Installed-package reference passed: {output / 'run/verification.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    check_package(parser.parse_args().output)
