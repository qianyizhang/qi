---
description: Native state copying erodes engine gains; storage dominates cheap generation and teacher search dominates realistic generation.
scope: generation throughput and native execution diagnosis
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Where the native speedup goes

**The small pipeline gain is reproducible, and there is a real native implementation
cost.** The maintained scalar path copies the full repetition map and history for
every move, then destroys the old state. This accounts for 56.1% of the native-core
diagnostic. Beyond the engine, durable collection writes dominate the cheap
controlled workload; teacher search dominates the realistic workload.

The replaced component is the **referee**: legality, transitions and outcomes.
Policy generation still selects actions, samples positions and writes evidence
in Python. Its expensive teacher search already runs in an external native
Pikafish process. Replacing the referee cannot accelerate that search.

[AB-LEARN-008](../work-items/items/AB-LEARN-008-experiment-performance.md) owns
the predeclared protocol and decisions. [Compact results](../../data/evaluation/generation-profile-20260921.json)
contain every comparison and derived ratio. Measurements use runtime `90a8a73`;
referee, generation and durability behavior are unchanged by this investigation.

## Matched full-pipeline measurements

Three alternating fresh-process Python/native pairs per workload, local Apple
Silicon macOS, Python 3.12.13, cold reference caches, fresh SQLite WAL/FULL
collections. Backend load and collection creation precede timing; teacher startup,
generation, validation and persistence occur inside timing. Independent replay,
supervision validation and SQLite checks run afterward.

| Workload | Python median | Native median | Median paired native throughput |
| --- | ---: | ---: | ---: |
| Prior controlled workload: 64 random games, up to 300 plies, fixture labels | 2.093 s | 1.926 s | **1.097x** |
| Real teacher: 16 plausible-actor games, four development families, up to 96 additional plies | 24.077 s | 23.233 s | **1.039x** |

The controlled cells match all 17,169 plies and 417 selected/labeled positions;
the semantic digest also matches the prior incremental-append experiment.
The teacher cells match 1,402 additional plies, 169 selected positions, 338
supervision calls and 1,402 actor calls. Three games end in checkmate, one in
repetition, and 12 at the workload cap. Phase quota shortfalls remain explicit.
These are completed bounded workloads, not 16 completed full games.

Teacher settings extend the existing generation-resource recipe: seed 17,
one thread, a 10k-node three-candidate plausible actor, and both 10k/100k-node
supervision. Starts are the first four distinct families in the development book;
the sealed test book is untouched. All comparisons preserve actor decisions,
outcomes, selected occurrences, supervision and node counts. Existing timing and
runtime fields are excluded from normalized comparisons; raw records retain them.
Diagnostic collections are not training exports.

The teacher throughput ratio is not a clean estimate of referee savings:
Python-worker CPU medians are 1.559/1.423 s, but waited-child CPU medians are
22.543/21.835 s for Python/native. The teacher did identical reported work at
different wall/CPU costs under local scheduling and clock variation. Native wins
the three unprofiled pairs, but the separate profiled pair reverses order.
There is no evidence here for a broad teacher-pipeline acceleration.

## Why the earlier 3.91x does not carry through

The [original native experiment](2026-09-21-native-backends.md) kept the complete
controlled game loop inside C++, crossing back after a whole game. The maintained
generation runner calls the scalar binding per move and asks for observations.
It also preserves allocation-failure atomicity by staging a full state copy.

An identical-action diagnostic replays the 64 controlled trajectories without
teacher, storage or actor selection. Every arm inspects every position. Three
alternating rounds, each with three cold-reference repetitions, produce identical
board/turn/outcome/check/legal-action projections. Full-view arms independently
verify history hashes after timing.

| Execution boundary | Median time for 17,169 actions | Paired speedup over Python |
| --- | ---: | ---: |
| Python trajectory with full immutable observations | 0.362 s | 1.000x |
| Maintained native trajectory with full immutable observations | 0.242 s | **1.475x** |
| Raw native binding, omitting Python history/hash/view management | 0.202 s | **1.780x** |

The raw binding has a narrower contract and is a component diagnostic. These
measurements are not the default Python generation path: it can defer legality
until an outcome/action query and does not request every full-view field.
The shared Python trajectory adapter itself is not a large remaining regression:
a separate three-round full-pipeline comparison measures 1.016x throughput versus
direct Python, close to parity.

### Native state-copy cost

The production scalar implementation in
[core.hpp](../../packages/qi-game-native/src/qi_game_native/core.hpp) validates the
move, copies `State`, advances the copy, then move-assigns it over the old state.
`State` contains a growing `unordered_map<string, int>` of repetition counts and
a history vector. Copying it allocates/copies entries; committing releases the old
map. This work grows with game history even though each move updates one board
and one repetition entry.

A standalone driver built with `-O3` against the same core measures five replays
of the 64-game action set, 85,845 actions. Three alternating unprofiled rounds:

- Staged production stepping: median **0.967 s**.
- Diagnostic in-place stepping: median **0.405 s**, **2.394x** paired throughput.
- Separate staged profile: copying **0.356 s**, replacing/freeing old state
  **0.180 s**, next-position observation/legal generation **0.395 s** out of
  **0.956 s** total. Copy plus replacement is **56.1%**.

The diagnostic consumes the in-check result and hashes every board, outcome,
ply, check flag and ordered internal action list. All modes match an independently
computed Python reference digest. The common digest has measurement overhead.
In-place mode deliberately lacks the production allocation-failure guarantee;
it is evidence of avoidable work, not a safe replacement or a measured pipeline
speedup. The initial driver discarded the check result and could let the compiler
remove it; that retained attempt is superseded by the corrected `core-02` result.

The Python/native language boundary contributes some cost, but merely moving the
existing Python wrapper into C++ would leave this map-copy cost intact. Nor does
native code automatically improve the algorithm: the small C++ legal generator
still tests candidate king safety, while the Python reference already uses
precomputed occupancy-mask geometry.

## Costs outside the referee

Separate profiles use nested wall spans with exclusive accounting, plus cProfile
for function discovery. Profiling increases runtime; use the unprofiled pairs for
speed claims. Native binding calls have explicit counters/timers because cProfile
alone does not give reliable pybind scalar-call attribution.

In the controlled native profile (3.126 s):

| Exclusive measured category | Time | Profiled wall share |
| --- | ---: | ---: |
| SQLite transaction exits, 20,283 calls | 0.686 s | 21.9% |
| SQLite statements, 45,418 calls | 0.294 s | 9.4% |
| Other work inside collection append | 0.473 s | 15.1% |
| Shared replay/Python wrapper work, excluding native children | 0.210 s | 6.7% |
| Native binding step plus inspection | 0.255 s | 8.2% |

The remainder includes sampling, serialization, model validation, provenance and
instrumentation. Phase classification alone takes 0.404 s cumulative across
18,003 calls; this overlaps the remaining categories and must not be added to the
table. Python move generation is not secretly running throughout the native path:
the controlled native run has one initial legal-cache miss, versus 17,131 in Python.
Native steps can be fewer than generated plies because shared cached prefixes and
constructor restoration also supply observations.

A paired synchronization sensitivity test changes **only disposable collections**
to `synchronous=OFF`, preserving generated outputs. Across three rounds it gives
1.387x Python and 1.418x native throughput, about 28%/29% less wall time. Native's
advantage over Python remains modest even there. This establishes substantial
synchronization cost; it does not authorize weaker durability, and transaction
exit timing is not an isolated filesystem-sync measurement.

For the teacher workload, the dominant cost changes:

- Teacher response-line reads consume **90.3% / 90.4%** of profiled Python/native
  wall time. The selector wait itself is 21.425/22.601 s.
- SQLite statements plus transaction exits take **0.342/0.370 s**.
- Native binding step/inspection together take **0.024 s**; native construction
  adds 0.003 s. Optimizing those cannot materially shrink a roughly 24-second run.
- Waited-child CPU confirms active external computation rather than attributing
  idle Python waiting to Python execution. Child accounting also includes small
  provenance Git processes; it is not a teacher-only hardware profile.

The existing `referee_seconds` counters must not compare engine performance:
Python's timer ends before the next lazy legal-move calculation, which may be
charged to append or the next loop iteration. Native's step materializes the next
legal moves before its timer ends. The explicit whole-action comparison above
avoids that mismatched accounting boundary.

## Next optimization decision

1. **For realistic teacher generation, test bounded parallel independent games.**
   The current policy runner and its persistent teacher session are serial. Start
   with two isolated workers/collections on disjoint frozen sources, each retaining
   one-thread teacher settings, then compare against serial execution of the same
   work. Require identical per-source trajectories, supervision and recovery;
   measure combined resources and retained positions/s. The older `v1.py` worker
   pool does not provide this for the policy runner. This is the highest-value
   next throughput experiment; no scheduler or concurrency gain is claimed here.
2. **For the C++ backend itself, replace full-state copying with bounded atomic
   preparation.** Preallocate the next history/repetition update before a nonthrowing
   commit, retaining guard/error precedence, invalid-action and allocation-failure
   atomicity. Prove correctness with conformance, allocation-failure tests and
   sanitizers, then rerun the fixed full pipeline. Keep multi-handle batch
   atomicity distinct. The diagnostic establishes a target, not the safe design.
3. **For cheap generation, prioritize persistence and repeated preparation costs.**
   Preserve every-move WAL/FULL recovery. A storage-layout or commit-boundary
   change needs its own contract decision; turning synchronization off is rejected
   as an optimization. Further rules work has limited end-to-end headroom here.

Python remains default and native remains explicit. None of these results meets
the existing 1.2x native advancement criterion on the measured full pipeline.
No playing-strength, label-quality or population-wide throughput claim follows.

## Evidence, limitations and reproduction

All pipeline cells agree within workload, including profile, shared-adapter and
synchronization diagnostics. Raw semantic records, SQLite collections, per-worker
logs, profiles and frozen source/binary manifests remain under
`artifacts/generation-profile-20260921`. Main results retain verified source
manifests; compact results link every raw summary with a SHA-256. The initial
launcher failed after its first worker due to relative-path bookkeeping; it is
retained as incomplete and excluded from paired results.

This is one local machine and two bounded workload families. Repeats are timing
replications, not independent datasets. No CPU affinity or clock control was
imposed; no Linux run was performed. Reported worker peak RSS is captured before
verification. Child RSS is a separate maximum, not simultaneous combined peak
memory. Profile and timing numbers answer different questions.

The [study guide](../../data/experiments/generation_profile_v1/README.md) owns
current commands and driver boundaries. Reusable timing, POSIX resource accounting
and function-profile export now live in `qi.profiling`; workload fixtures and
weaker diagnostic modes stay in the study directory. Historical reproduction uses
the frozen sources/binary above; current-source reruns are new measurements.

The original measurement verification passed three harness tests, 20 native/backend
integration tests, and `make test-native` isolated source/wheel and generation/HTTP
checks. Subsequent cleanup added scoped instrumentation restoration, bounded
partial-sweep receipts, argument validation and optimized-Python-safe native replay.
It preserves the measurements and semantic projections; the owner records current
verification separately from the original run receipts.
Catalog structure and this study's evidence hashes verify. The global optional
hash check still reports the pre-existing, unrelated AB-EVAL-005 mismatch for
`scripts/import_benchmark_book.py`; it is not changed or waived by this study.
