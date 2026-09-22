"""AB-ARCH-006: compare compact native observations against complete c4a8d91 controls."""

from pathlib import Path

from generation_benchmark_harness import RUNTIME_TREE_COMPARISON, main

if __name__ == "__main__":
    main(protocol=RUNTIME_TREE_COMPARISON, entrypoint=Path(__file__), description=__doc__)
