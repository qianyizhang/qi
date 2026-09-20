---
description: Optional native trajectory integration passes conformance but does not improve full generation throughput.
scope: native generation performance and conformance
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Native execution inside policy generation

**Keep the direct Python default.** The optional C++ package and actual generation
integration pass the measured semantic controls, but native execution takes about
20% longer on the controlled full pipeline. The small real-teacher pilot is near
parity. The next useful optimization is completing the execution boundary through
collection validation and sampling, where Python still repeats rule work.

[AB-ARCH-004](../work-items/items/AB-ARCH-004-native-generation.md) owns the protocol
and attempts. [Compact results](../../data/evaluation/native-generation-20260921.json)
retain every measured cell; complete local records and source snapshots live under
`artifacts/native-generation-20260921`.

## What is implemented

[The optional package](../../packages/qi-game-native/README.md) owns its C++17 core,
pybind11 binding and build dependencies. It provides replay restoration, persistent
state, detached inspection, guarded moves, atomic batches of caller-supplied
actions, explicit close and snapshot-referee injection. The default installation
requires no native build. Run metadata pins the extension binary independently
of semantic state and actor RNG identities.

`generate_policies(..., trajectory_factory=NativeTrajectory)` uses native rules
and transitions. Actors, lexical move ordering, per-game RNG, sampler, teachers,
every-move persistence and collection validation retain their current behavior.
The runner still schedules one game at a time; batch stepping is independently
available and verified. This does not move a complete actor/trajectory loop into
C++ and does not replace search or the older library generator.

## Controlled full-pipeline result

Every cell generated the same 64 distinct trajectories, 17,169 plies, 417 selected
examples and 417 deterministic fixture labels: 18 checkmates and 46 ply-limit
draws. Sampling reported 43 endgame and 52 opening shortfalls. The fixture labels
isolate execution/data costs; they are not useful teacher-quality evidence.
All 18 primary workers across both confirmation attempts matched the same complete
semantic digest, including decisions, retained occurrences and labels. Repeated
workers are not additional independent trajectories.

The initial integration compared the original runner with both persistent
adapters. Native achieved 0.810x the original throughput; the Python adapter added
11.8% runtime. That finding is preserved in `confirmation-01`. The implementation
was then corrected to keep the original direct Python default, and the unchanged
inputs were rerun in three alternating rounds (`confirmation-02`):

| Execution | Median wall time | Legal plies/s | Selected examples/s |
| --- | ---: | ---: | ---: |
| Original committed Python runner | 2.476 s | 6,935 | 168.4 |
| Final direct Python default | 2.451 s | 7,004 | 170.1 |
| Explicit native trajectory | 2.900 s | 5,920 | 143.8 |

Ratios are paired Python time divided by native time: native throughput was
0.835x the final default, below the predeclared 1.2x advancement threshold.
Default/original runtime was 0.996x by median paired ratio; the adapter regression
is absent from the default. Native was slower in every primary round. Worker
peak RSS was approximately 113–114 MiB, including subsequent evidence verification.

## Real-teacher pilot

Four plausible-actor games used pinned local Pikafish/NNUE, one thread, 1,000 nodes
and a 32-ply cap. All four workers across two paired rounds matched 128 plies,
20 selected examples, actor decisions, outcomes and supervision. All games were
workload-truncated at 32 plies; no referee terminal outcome was claimed.
Elapsed milliseconds and UCI `time`/`nps` fields were excluded from the semantic
projection; raw records retain them.

Median times were 0.684 s for default Python and 0.664 s for native; the paired
gain was 1.030x, with native winning one round and losing the other. This short
diagnostic does not establish a speedup or represent longer/deeper teacher work.
CPU and peak RSS fields cover the Python worker, not its Pikafish child process.

## Where the time goes

A separate post-hoc profile of the 64-game native workload preserved the same
semantic digest. Collection append accounted for 2.357 s of 4.077 s profiled
function time (about 58%). Python replay/restore still ran; Python legal-move
generation accounted for 0.673 s cumulative, while the native batch call itself
took 0.138 s. SQLite transaction exits took 0.697 s. Cumulative categories overlap
and must not be added. Profiling changes timing; these are diagnostic numbers,
not replacements for the unprofiled comparison.

The integration currently adds native execution alongside independent Python
collection replay validation. The earlier 3.91x complete-native-loop result from
[AB-ARCH-003](2026-09-21-native-backends.md) excluded these consumers and used a
different controlled actor. It cannot be transferred to this pipeline.

## Verification and decision

The package matched all ten frozen replay fixtures and 169 complete game
comparisons at batch widths 1, 8, 32 and 128 (128 distinct seeds). Tests cover
batch rejection atomicity, stale precedence, malformed Unicode/NUL actions,
invalid full histories, terminal rejection, detached results and closed handles.
Production integration tests cover random/plausible/intervention actor parity,
sampling, supervision, resume, failure cleanup and the HTTP boundary. The
standalone core sanitizer also covers both frozen terminal diagrams and 128
trajectories. Isolated sdist/wheel checks passed on macOS ARM64. CI adds macOS and
Linux lanes; Linux has not been executed locally.

The full `make check` gate passed: lint, format, documentation, catalog structure,
OpenAPI/type checks, production browser build, 785 Python tests (one skipped) and
five browser unit tests. All retained confirmation source copies matched their
152-file manifests. The final runtime matches the follow-up source snapshot;
only the standalone sanitizer subsequently gained the two terminal-diagram checks.

Retain the native package as an explicit experimental option. Before advancing
adoption, extend the replaceable execution boundary through incremental collection
validation and observation/sampling consumers, preserving per-move durability and
the same independent correctness controls. Re-measure the full pipeline after
that change. Wider batches or a faster native move generator alone do not address
the measured duplication. No default backend, dataset quality or playing-strength
claim changes.

## Reproduction

Run from the repository root, using new output paths. Historical confirmation
reproduction uses its frozen source tree and extension, not a later checkout.
For a fresh comparison of the maintained implementation:

```bash
uv sync --locked --extra native
mkdir -p artifacts/native-generation-new
git show 41fdb96:src/qi/training_data/generation_runner.py \
  > artifacts/native-generation-new/baseline_runner.py
uv run --locked --extra native python scripts/benchmark_native_generation.py prepare \
  --output artifacts/native-generation-new/inputs
uv run --locked --extra native python scripts/benchmark_native_generation.py compare \
  --config artifacts/native-generation-new/inputs/controlled.json \
  --baseline artifacts/native-generation-new/baseline_runner.py \
  --output artifacts/native-generation-new/comparison --reference-arm default
```

Preparation accepts `--teacher-config` pointing to an existing policy-generation
config with valid pinned local teacher assets; it emits a bounded `teacher.json`.
Compare that config with `--workload teacher --rounds 2 --reference-arm default`.
Every worker writes its config, SQLite collection, semantic projection and result;
comparisons retain logs and refuse existing output directories. The optional
worker `--profile` mode is diagnostic and must use a separate output directory.
