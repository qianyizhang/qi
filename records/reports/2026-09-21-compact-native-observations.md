---
description: Compact native observations improve controlled generation throughput by 1.102x over Python but remain below the adoption threshold.
scope: native trajectory interface performance
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Compact native observations

Compact native trajectories achieved **1.102x the direct Python throughput**,
winning all three controlled rounds, and 1.085x the previous shared-native
integration. Exact outputs were preserved. This improves the interface but misses
the predeclared 1.2x adoption threshold, so native remains explicitly selected.
The small real-teacher pilot measured 1.027x; it does not establish a broadly
representative teacher-workload speedup.

[AB-ARCH-006](../work-items/items/AB-ARCH-006-compact-native-observations.md) owns
the predeclared comparison and decision. [Compact results](../../data/evaluation/compact-native-20260921.json)
retain every cell; full local collections, logs, profiles and source/binary copies
live under `artifacts/compact-native-20260921`. This extends
[shared validation](2026-09-21-shared-replay-execution.md) by reducing interface
work after duplicated Python rules were removed.

## Implemented change

`Trajectory.inspect()` and `step()` now return immutable `GameView` values directly.
The native handle caches its current view, retains a Python history tuple and
updates the canonical replay hash incrementally. C++ inspection exports the
board, side, outcome, check and legal actions without exporting full history.
`ReplaySession` reuses this result without constructing another view through
Pydantic contracts. Reference trajectories implement the same interface.

Scalar native stepping has its own C++ entry point. It validates first and stages
allocations before committing a new state, avoiding batch containers. Batch
stepping retains all-or-nothing staging and caller order. Python history/hash
updates are prepared before native execution and committed only on success.
Failed actions or metadata preparation leave native state and replay identity
unchanged; tests check successful follow-up moves to detect hidden state drift.

The snapshot-based referee and HTTP still return fresh `Position` contracts via
explicit conversion. Callers can modify those wire objects; retained views remain
immutable across later steps and close. Maintained consumers import `GameView`
from `qi_game.trajectory` and migrate directly. The package guide owns the current
contract. Storage, per-move commits, actor RNG, rules and sampling policies are
unchanged. The Python default remains direct reference execution.

## Controlled generation

Three alternating four-arm rounds use fresh processes and collections. Historical
arms execute the entire archived `c4a8d91` runtime and its original native binary;
current arms execute the new source and binary. Imported runtime roots are checked.
The fixed workload retains seed 29, 64 random-actor games, a 300-ply cap, the same
phase quotas and deterministic legal fixture supervision. Timing is serial,
without concurrent builds or tests.

All 12 workers match **64 trajectories, 17,169 plies and 417 selected fixture
labels**, including decisions, occurrences, outcomes and supervision. Outcomes
remain 18 checkmates and 46 ply-limit draws, with 43 endgame and 52 opening quota
shortfalls. The semantic digest matches both earlier integration studies.
Independent post-timing Python verification checks full replay, final outcomes,
decisions, occurrence fields and legal labels; SQLite integrity and foreign-key
checks pass. Fixture labels are correctness controls, not teaching-quality evidence.

| Execution | Median wall time | Plies/s | Selected examples/s |
| --- | ---: | ---: | ---: |
| Previous direct Python | 2.616 s | 6,564 | 159.4 |
| Previous shared native | 2.680 s | 6,406 | 155.6 |
| Current direct Python | 2.644 s | 6,494 | 157.7 |
| Compact native | 2.397 s | 7,163 | 174.0 |

The decision uses medians of within-round time ratios, not ratios of independently
computed medians. Python/native ratios are 1.082, 1.102 and 1.108; previous-native/
compact-native ratios are 1.123, 1.085 and 1.080. Current/previous Python runtime
is 1.011x by median paired ratio, below the 5% regression flag. These short local
windows do not establish small default-path changes. Repeated trajectories are
not additional independent workload samples.

## Teacher pilot and remaining costs

Two alternating paired rounds use four plausible-actor games, 32 plies, the same
pinned Pikafish/NNUE, one thread and 1,000 nodes. All four cells match 128 plies,
20 selections, actor choices, occurrences and labels. All games stop at the
workload cap. Median wall time is 0.671 s for Python and 0.653 s for native;
native wins both rounds with a 1.027x median paired ratio. Only elapsed time,
UCI `time`/`nps` and the network locator are removed from semantic comparison;
raw records preserve them. The short pilot does not represent deeper teacher work.

Both native arms record just one Python legal-move cache miss before independent
verification, for initial-position preflight. Current and historical Python arms
record 17,131 misses on the controlled workload. Thus the new gain follows the
interface change, not further removal of duplicated rules.

Median unprofiled referee-phase time falls from 0.488 s in the previous native
arm to 0.333 s in the compact arm. Current native append time is 1.395 s and
sampling time 0.098 s. These counters cover named blocks only; they do not exhaust
wall time or independently isolate every cost.

A separate native profile retains exact semantic parity. It attributes 1.531 s
cumulative to collection append, including 0.718 s in SQLite transaction exits,
and 0.512 s to stored-game loading/validation. Cumulative categories overlap.
The profile reports inconsistent scalar-call counts around the native binding,
so it is not used for per-step timing claims. Unprofiled paired measurements and
phase counters determine the conclusion. Worker CPU/RSS exclude the teacher child
process; peak RSS also includes post-timing verification.

The next performance hypothesis is reducing repeated collection payload decoding
and serialization while preserving per-move durability. It needs its own bounded
trial. No persistence change, default promotion, search change or strength claim
is part of this result.

## Evidence and reproduction

The development four-arm parity trial passed before confirmation, and no timed
attempt failed. Each full comparison retains a 304-file source/binary manifest;
all frozen hashes and executed runtime sources verify. Historical study scripts,
reports and catalog evidence remain unchanged. The old and new native binaries
are separately retained and identified by SHA-256.

The first isolated-native check found one unmigrated smoke assertion expecting
`Position.snapshot`; its failed log is retained. The assertion now checks the
immutable view's move tuple, and the isolated gate is rerun separately. This was
a verification-tool migration, not a runtime or timed-result change.

Final checks pass: `make check` covers 792 Python tests (one skipped), five browser
unit tests, lint/format, documentation/catalog, OpenAPI/types and the production
browser build. Isolated sdist-to-wheel checks pass 70 game-package tests and ten
native-package tests. ASan/UBSan exercises the new scalar path through malformed
actions, repetition, both frozen terminal diagrams and 128 complete games.
Differential tests cover ten frozen replays and complete games at batch widths
1, 8, 32 and 128, with width one using the dedicated scalar call. Integration
tests preserve generation, recovery, teacher validation and HTTP behavior.

Use the current maintained source for a new comparison. Recorded-result
reproduction requires the frozen source, lock and binary, rather than a later
checkout. The retained complete baseline is
`artifacts/compact-native-20260921/baseline-c4a8d91`. With new output paths:

```bash
uv sync --locked --extra native
uv run --locked --extra native python scripts/benchmark_compact_native.py prepare \
  --output artifacts/compact-native-new/inputs
uv run --locked --extra native python scripts/benchmark_compact_native.py compare \
  --config artifacts/compact-native-new/inputs/controlled.json \
  --baseline artifacts/compact-native-20260921/baseline-c4a8d91 \
  --output artifacts/compact-native-new/confirmation --rounds 3
```

Preparation accepts `--teacher-config` with pinned local teacher assets; compare
the emitted `teacher.json` using `--workload teacher --rounds 2`. The standalone
worker's `--profile` mode requires a separate output directory. Existing outputs
are never overwritten. Raw local artifacts are ignored by Git; maintained code,
compact cells and this finding are tracked. Linux coverage remains configured in
CI rather than locally executed.
