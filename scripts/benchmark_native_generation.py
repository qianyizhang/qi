"""Isolated native-generation comparison; preserve every cell and semantic record."""

from pathlib import Path

from generation_benchmark_harness import NATIVE_GENERATION_COMPARISON, main

if __name__ == "__main__":
    main(protocol=NATIVE_GENERATION_COMPARISON, entrypoint=Path(__file__), description=__doc__)
