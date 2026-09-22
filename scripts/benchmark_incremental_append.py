"""AB-ARCH-007: compare incremental collection writes against complete c44e08d controls."""

from pathlib import Path

from generation_benchmark_harness import INCREMENTAL_RUNTIME_COMPARISON, main

if __name__ == "__main__":
    main(protocol=INCREMENTAL_RUNTIME_COMPARISON, entrypoint=Path(__file__), description=__doc__)
