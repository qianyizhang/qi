"""AB-ARCH-005: compare complete historical/current runtimes and shared validation."""

from pathlib import Path

from generation_benchmark_harness import RUNTIME_TREE_COMPARISON, main

if __name__ == "__main__":
    main(protocol=RUNTIME_TREE_COMPARISON, entrypoint=Path(__file__), description=__doc__)
