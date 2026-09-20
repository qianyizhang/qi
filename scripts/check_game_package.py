"""Build and test qi-game outside the workspace with only its declared dependencies."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", action="store_true", help="Also build and isolate the optional C++ package.")
    native = parser.parse_args().native
    package = "qi-game-native" if native else "qi-game"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "UV_CACHE_DIR": str(root / ".cache/uv")}
    env.pop("PYTHONPATH", None)

    def run(*args, cwd=root, stdout=None):
        subprocess.run(args, cwd=cwd, env=env, stdout=stdout, check=True)

    with TemporaryDirectory(prefix="qi-game-package-") as directory:
        work = Path(directory).resolve()
        dist = work / "dist"
        run("uv", "build", "--package", "qi-game", "--sdist", "--out-dir", str(dist))
        run("uv", "build", "--wheel", str(next(dist.glob("*.tar.gz"))), "--out-dir", str(dist), cwd=work)
        if native:
            native_dist = work / "native-dist"
            run("uv", "build", "--package", package, "--sdist", "--out-dir", str(native_dist))
            run("uv", "build", "--wheel", str(next(native_dist.glob("*.tar.gz"))), "--out-dir", str(dist), cwd=work)
        requirements = work / "requirements.txt"
        run(
            "uv",
            "export",
            "--locked",
            "--package",
            package,
            "--no-emit-workspace",
            "--output-file",
            str(requirements),
            stdout=subprocess.DEVNULL,
        )
        python = work / "venv/bin/python"
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
            """
from importlib.util import find_spec
from pathlib import Path
import qi_game
assert Path(qi_game.__file__).is_relative_to(Path.cwd()), qi_game.__file__
for name in ('qi', 'fastapi', 'typer', 'torch', 'numpy', 'pyarrow'):
    assert find_spec(name) is None, name
""",
            cwd=work,
        )
        if native:
            run(
                str(python),
                "-I",
                "-c",
                """
import sys
from qi_game_native.backend import NativeTrajectory
from qi_game.contracts import Snapshot
assert 'qi_game.reference' not in sys.modules
game = NativeTrajectory(Snapshot())
assert game.step('b2e2').snapshot.moves == ['b2e2']
game.close()
assert 'qi_game.reference' not in sys.modules
""",
                cwd=work,
            )
        run(str(python), "-I", "-m", "pytest", "--pyargs", "qi_game_native" if native else "qi_game", "-q", cwd=work)
    print(f"Isolated {package} sdist/wheel checks passed.")


if __name__ == "__main__":
    main()
