"""The optional package alone owns its compiler requirement."""

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

setup(
    ext_modules=[
        Pybind11Extension(
            "qi_game_native._native",
            ["src/qi_game_native/binding.cpp"],
            depends=["src/qi_game_native/core.hpp"],
            cxx_std=17,
            extra_compile_args=["-O3", "-Wall", "-Wextra", "-Werror"],
        )
    ],
    cmdclass={"build_ext": build_ext},
)
