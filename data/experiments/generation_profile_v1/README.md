---
description: Reproduce bounded generation comparisons and native cost diagnostics.
scope: AB-LEARN-008 profiling drivers
status: experimental
last_update: 2026-09-21
document_class: artifact
---

# Generation profiling

These study-specific drivers use [qi.profiling](../../../src/qi/profiling.py)
for reusable timing and resource accounting. The
[report](../../../records/reports/2026-09-21-generation-bottlenecks.md) owns measured
findings; frozen sources under `artifacts/generation-profile-20260921` reproduce
the historical study. Current-source runs are new measurements.

Run from the checkout with the project environment installed. Native arms require
`uv sync --locked --extra native`; teacher runs require the pinned local assets in
the generated configuration. Preparation creates controlled fixture assets itself.
Absolute script and output paths also work from another directory.

```bash
.venv/bin/python data/experiments/generation_profile_v1/study.py prepare \
  --output artifacts/generation-profile-new/inputs
.venv/bin/python data/experiments/generation_profile_v1/study.py run \
  --config artifacts/generation-profile-new/inputs/controlled.json \
  --output artifacts/generation-profile-new/controlled --rounds 3
.venv/bin/python data/experiments/generation_profile_v1/study.py run --workload teacher \
  --config artifacts/generation-profile-new/inputs/teacher.json \
  --output artifacts/generation-profile-new/teacher --rounds 3
```

Every output path must be fresh. Sweeps alternate cell order in isolated workers,
freeze source/configuration, verify source hashes afterward and stop on semantic
mismatch. Workers allow at most 180 seconds each within a 20-minute sweep budget.
Failures retain logs, collections and completed cells in `failure.json`; only a
successful sweep writes `summary.json`. Direct `worker` invocations are not given
a subprocess deadline. Frozen configurations retain their original asset paths.

Use `--modes profile --rounds 1` for instrumented diagnostics; use unprofiled
`timing` cells for speed claims. Profiles are in each worker's `functions/` folder.
`--arms default,python-session,native` isolates shared-adapter cost.
`--arms default` works without the native extra. `--modes timing,off` changes
**only fresh diagnostic collections** to weaker SQLite synchronization in `off`
cells. It does not propose or change production durability.

Replay a controlled worker's identical actions, inspecting each position:

```bash
.venv/bin/python data/experiments/generation_profile_v1/actions.py \
  --input artifacts/generation-profile-new/controlled/round-1-default-timing/semantic.json \
  --output artifacts/generation-profile-new/actions-python --arm python --repeats 3
```

Repeat in fresh output directories with `--arm native` and `--arm raw-native`.
Compare `semantic_sha256` across arms. The raw arm omits Python history/hash/view
management; its smaller contract must stay explicit. This driver accepts only
games starting at the initial board.

`core.cpp` is a standalone C++ driver against the native `core.hpp`. Build with
`c++ -O3 -std=c++17 -I packages/qi-game-native/src/qi_game_native` and this source,
writing the executable under a fresh artifact directory. It takes three positional
arguments: a text file containing one game's space-separated moves per line,
`staged`, `inplace` or `profile`, and a positive repeat count. Convert the controlled
semantic records' `game.snapshot.moves` to that input. Compare every mode's
`state_digest` with an independent Python oracle before interpreting times.
`inplace` deliberately weakens allocation-failure atomicity and remains a diagnostic.

Validate changes with:

```bash
.venv/bin/ruff check data/experiments/generation_profile_v1
.venv/bin/ruff format --check data/experiments/generation_profile_v1
.venv/bin/pytest src/qi/test_profiling.py tests/test_generation_profile.py
```
