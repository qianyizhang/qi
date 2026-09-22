"""Build and test qi-game outside the workspace with only its declared dependencies."""

import argparse
import os
import shlex
import sysconfig
from pathlib import Path
from tempfile import TemporaryDirectory

from package_check import PackageRunner, build_distribution, create_isolated_environment, export_requirements


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", action="store_true", help="Also build and isolate the optional C++ package.")
    native = parser.parse_args().native
    package = "qi-game-native" if native else "qi-game"
    root = Path(__file__).resolve().parents[1]
    runner = PackageRunner.create(root)

    with TemporaryDirectory(prefix="qi-game-package-") as directory:
        work = Path(directory).resolve()
        if native:
            executable = work / "native-sanitizer"
            compiler = shlex.split(os.environ.get("CXX") or sysconfig.get_config_var("CXX") or "c++")
            runner.run(
                *compiler,
                "-std=c++17",
                "-O1",
                "-g",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                str(root / "packages/qi-game-native/sanitizer.cpp"),
                "-o",
                str(executable),
            )
            runner.run(executable, cwd=work)
        dist = work / "dist"
        distributions = [build_distribution(runner, "qi-game", dist)]
        if native:
            native_dist = work / "native-dist"
            distributions.append(build_distribution(runner, package, native_dist, wheel_directory=dist))
        requirements = work / "requirements.txt"
        export_requirements(runner, requirements, package=package)
        environment = create_isolated_environment(
            runner,
            work / "venv",
            requirements,
            (distribution.wheel for distribution in distributions),
        )
        runner.use_offline_cache()
        runner.run(
            environment.python,
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
            runner.run(
                environment.python,
                "-I",
                "-c",
                """
import sys
from qi_game_native.backend import NativeTrajectory
from qi_game.contracts import Snapshot
assert 'qi_game.reference' not in sys.modules
game = NativeTrajectory(Snapshot())
assert game.step('b2e2').moves == ('b2e2',)
game.close()
assert 'qi_game.reference' not in sys.modules
""",
                cwd=work,
            )
        runner.run(
            environment.python,
            "-I",
            "-m",
            "pytest",
            "--pyargs",
            "qi_game_native" if native else "qi_game",
            "-q",
            cwd=work,
        )
    print(f"Isolated {package} sdist/wheel checks passed.")


if __name__ == "__main__":
    main()
