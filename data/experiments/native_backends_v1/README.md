---
description: Reproduce the bounded imported-versus-minimal C++ referee experiment.
scope: experimental native backend study
status: experimental
last_update: 2026-09-21
document_class: artifact
---

# Native backend comparison

[AB-ARCH-003](../../../records/work-items/items/AB-ARCH-003-native-backend-experiment.md)
owns the protocol; [the report](../../../records/reports/2026-09-21-native-backends.md)
owns results, implementation trade-offs and limits. These are experimental
candidates, not production backends. The private C ABI assumes valid,
exclusively owned handles supplied by its Python wrapper.

## Reproduce on macOS ARM64

Use the root development environment. Optional dependencies and binaries stay
under the ignored artifact directory; the workspace dependency graph is unchanged.
Linux execution has not been tested.

```bash
UV_CACHE_DIR=/tmp/qi-native-uv-cache uv pip install \
  --index-url https://pypi.org/simple \
  --target artifacts/native-backends-20260921/deps \
  -r data/experiments/native_backends_v1/requirements.txt
clang++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Werror -fPIC -shared \
  data/experiments/native_backends_v1/minimal.cpp \
  -o artifacts/native-backends-20260921/minimal.dylib
.venv/bin/pytest -q data/experiments/native_backends_v1/test_study.py
.venv/bin/python data/experiments/native_backends_v1/study.py run \
  --output artifacts/native-backends-20260921/confirmation-fresh
```

Always choose a fresh output directory. The runner retains source, reference,
fixture, dependency and binary bytes, validates conformance, then runs isolated
workers serially in alternating order. It checks exact trajectory digests and
rejects source/binary changes during execution. Each worker retains its full
trajectories and timing record; the run produces `manifest.json`,
`validation.json` and `summary.json`.

The measured core and runner remain byte-identical to the recorded trial.
Optional test setup was refined afterward; original tests remain in its `frozen/`
tree. For exact historical reproduction use that tree and the recorded environment.
The published pyffish wheel's compiler flags are unknown; its installed bytes and
GPLv3+ package metadata are retained.

## Native memory checks

```bash
clang++ -std=c++17 -O1 -g -fsanitize=address,undefined \
  -fno-omit-frame-pointer -Wall -Wextra -Werror \
  data/experiments/native_backends_v1/sanitizer.cpp \
  -o artifacts/native-backends-20260921/sanitizer
artifacts/native-backends-20260921/sanitizer
```

Backend tests skip only their own missing optional dependency. The output-overwrite
check runs without either native candidate. All commands above are explicit study
checks; they are not added to the default application test suite.
