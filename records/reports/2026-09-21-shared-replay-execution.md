---
description: Shared native validation removes duplicate rules and improves the previous integration, but remains near Python throughput.
scope: generation execution boundary and performance
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Shared replay execution

**Keep native opt-in.** Sharing validated native results removes repeated Python
rules and improves throughput by 1.164x against the previous native integration.
It does not meet the predeclared 1.2x gain over the default: the paired result is
0.984x, with native losing two of three rounds. The real-teacher pilot is also
near parity. These results support the completed execution boundary, not default
adoption or a playing-strength claim.

[AB-ARCH-005](../work-items/items/AB-ARCH-005-shared-replay-execution.md) owns the
protocol and decisions. [Compact results](../../data/evaluation/shared-replay-20260921.json)
retain every measured cell. Raw collections, exact source/binary copies, logs
and profiles are local under `artifacts/shared-replay-20260921`.

## Implemented boundary

An explicitly selected trajectory factory now serves the entire policy-generation
path through one run-owned `ReplaySession`. Immutable `GameView` values carry the
board, history, state hash, legal moves, check and outcome. A bounded cache retains
at most 301 histories; consecutive moves advance one backend cursor, and uncached
branches restore through that backend. Only backend results enter the cache.

Collection legality, teacher-input validation, candidate evidence and sampling
reuse those results. Cached legality never substitutes for SQLite's persisted
prefix, lifecycle, split or transaction checks. Every move still commits durably.
Failed writes cannot advance the stored game, and retry/recovery tests cover this
distinction. Forged teacher views are rejected before an engine query. Scope exit
closes both teacher and referee resources, including failure paths.

The direct Python default remains. Search, player sessions, the older library
generator and collection operations outside this explicit run scope retain their
reference behavior. This slice adds no global backend setting or scheduler.
Custom generation providers now receive immutable views when a factory is selected;
the owning [guide](../../src/qi/training_data/README.md) documents that boundary.

## Fixed full-pipeline comparison

The historical controls execute the complete `92943ff` runtime, including its
store, models and teacher code, from an archived tree. They cannot inherit the
new validation path. Each worker verifies its imported runtime root. All arms use
the same native binary where applicable, fixed actors, RNG, sampling and inputs;
only runtime selection differs. Fresh processes and collections run serially in
three alternating four-arm rounds on macOS ARM64/Python 3.12.

All 12 workers produced exactly the same 64 trajectories, 17,169 plies, 417 selected
occurrences and 417 deterministic fixture labels. Outcomes were 18 checkmates and
46 ply-limit draws, with the same 43 endgame and 52 opening quota shortfalls.
The semantic digest also matches AB-ARCH-004. Independent Python verification
runs after timing and checks replay, outcomes, decisions, occurrence board/turn,
snapshot fingerprint, model-input hash, phase and legal supervision. SQLite
integrity and foreign-key checks pass. Repeated workers are not additional
independent trajectories, and fixture labels provide no teacher-quality evidence.

| Execution | Median wall time | Plies/s | Selected examples/s |
| --- | ---: | ---: | ---: |
| Previous direct Python | 2.534 s | 6,777 | 164.6 |
| Previous native integration | 3.098 s | 5,543 | 134.6 |
| Current direct Python | 2.615 s | 6,565 | 159.5 |
| Shared native execution | 2.578 s | 6,661 | 161.8 |

Decision ratios use the median of within-round time ratios, not a ratio of these
independently calculated medians. Current-default/native ratios were 0.984,
1.015 and 0.982. Previous-native/shared-native ratios were 1.164, 1.236 and 1.148.
Current-default/previous-default runtime was 1.020x by median paired ratio, below
the 5% regression flag; its individual ratios ranged from 0.999 to 1.046.
These short local windows do not establish a small regression or speedup.

Native's Python legal-move cache recorded one miss and one hit before independent
verification, both from initial-position preflight. Every historical-native and
default worker recorded 17,131 misses. Integration tests additionally reject any
reference move generation on generated native positions and count each move's
single execution across random, plausible and intervention actors.

## Real-teacher diagnostic and remaining costs

Four plausible-actor games used the same pinned Pikafish/NNUE assets, one thread,
1,000 nodes and a 32-ply cap. All four workers across two alternating paired rounds
matched 128 plies, 20 selections, actor choices, occurrences and supervision.
All games stopped at the workload cap. Only elapsed time, UCI `time`/`nps` fields
and the engine-network locator are removed from comparison; raw records retain
them. Median runtime was 0.738 s for Python and 0.731 s for native. The paired
ratio was 1.009x, with opposite round winners: no established speedup.
Native again recorded only the initial-position Python rule miss.

A separate native profile preserves the controlled semantic digest. Of 3.519 s
profiled function time, collection append accumulated 1.641 s; SQLite transaction
exits alone took 0.736 s. Loading/validating stored games accumulated 0.566 s,
native contract inspection 0.466 s, and sampling 0.464 s. Native core stepping
itself took 0.144 s. Cumulative categories overlap and must not be added; profile
overhead means these numbers cannot replace unprofiled results.

The remaining opportunity is reducing Python contract construction and repeated
collection payload serialization while preserving every-move durability. The
profile supplies a hypothesis, not evidence that any proposed replacement wins.
Relaxing commit frequency would change recovery behavior and is outside this slice.
Worker CPU/RSS exclude Pikafish's child process; reported peak RSS includes later
independent verification. Linux CI remains configured rather than locally executed.

## Attempts, evidence and reproduction

The full `make check` gate passed: lint/format, documentation, catalog structure,
OpenAPI/type checks, production browser build, 792 Python tests (one skipped)
and five browser unit tests. Isolated sdist-to-wheel checks passed 70 game-package
tests and eight native-package tests. The unchanged C++ core was not modified or
re-sanitized in this slice. Runtime checks include native actor/sampler parity,
resume, failure cleanup, teacher-view rejection and transaction-abort recovery.

Two small development attempts failed in the new independent verifier, after
their first historical-default cell generated successfully. The first compared
two intentionally different hashes; the second used a snapshot method absent
from historical `Game`. Both attempts and logs are retained. `development-03`
then passed all four arms before confirmation. No failed development timings
are used in the conclusion.

Both confirmation and teacher comparisons retain 302-file source manifests;
every frozen file matches its recorded hash. The prior study's live runner
evidence locator is superseded by an appended catalog revision pointing to its
identical frozen copy. Its earlier records, script and conclusions remain intact.

Use the current maintained sources for a new study. The baseline must be an
entire `92943ff` archive under this repository, with its matching native extension;
the retained archive is `artifacts/shared-replay-20260921/baseline-92943ff`.
Reproducing recorded cells requires their frozen sources, lock and binary rather
than a later checkout. With the retained baseline and new output paths:

```bash
uv sync --locked --extra native
uv run --locked --extra native python scripts/benchmark_shared_execution.py prepare \
  --output artifacts/shared-replay-new/inputs
uv run --locked --extra native python scripts/benchmark_shared_execution.py compare \
  --config artifacts/shared-replay-new/inputs/controlled.json \
  --baseline artifacts/shared-replay-20260921/baseline-92943ff \
  --output artifacts/shared-replay-new/confirmation --rounds 3
```

Preparation also accepts `--teacher-config` pointing to a policy-generation recipe
with pinned local teacher assets. Compare its emitted `teacher.json` using
`--workload teacher --rounds 2`. A standalone `worker --arm native --profile`
uses a separate output directory for diagnostics. Existing outputs are never
overwritten. Raw local artifacts are ignored by Git; the compact results,
maintained study runner and this report are tracked.
