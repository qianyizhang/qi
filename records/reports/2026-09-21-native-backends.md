---
description: Direct C++ engine import versus a minimal Qi-specific native trajectory implementation.
scope: native execution performance and conformance
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Imported versus minimal C++ execution

**Advance the minimal C++ trajectory implementation for the next integration
study.** Its coarse native loop was 3.80–3.91x faster than Python across three
rounds, while preserving all measured trajectories. The unmodified pyffish import
passed correctness but was approximately 128x slower than Python in this calling
pattern. No production default changed.

## Comparison and results

[AB-ARCH-003](../work-items/items/AB-ARCH-003-native-backend-experiment.md)
predeclared the conditions and advancement rule. Each of 21 isolated workers ran
the same 128 confirmation seeds through at most 300 legal plies. Every worker
produced the same 34,491 plies and the same complete trajectory digest. There were
33 checkmates, one stalemate and 94 ruleset ply-limit draws; no workload-truncated
games, worker failures or timeouts. These are 128 distinct controlled games
repeated across treatments/rounds, not 2,688 independent games.

| Execution | Median time for 128 games | Median legal plies/s | Median paired speedup vs Python | Peak process RSS |
| --- | ---: | ---: | ---: | ---: |
| Existing Python referee | 0.624 s | 55,308 | 1.00x | 46.9 MiB |
| Direct pyffish 0.0.90 import + Qi adapter | 79.648 s | 433 | 0.0078x | 131.0–131.1 MiB |
| Minimal C++, Python call per move | 0.356 s | 96,915 | 1.76x | 38.5–38.9 MiB |
| Minimal C++, complete game per native call | 0.160 s | 215,712 | 3.91x | 38.7–38.8 MiB |
| Minimal C++, 8-game native batches | 0.170 s | 202,674 | 3.67x | 39.1–39.3 MiB |
| Minimal C++, 32-game native batches | 0.180 s | 191,994 | 3.47x | 40.2 MiB |
| Minimal C++, 128-game native batches | 0.192 s | 179,236 | 3.22x | 45.2–45.4 MiB |

Speedup is the median of three paired round ratios, not a ratio inferred from
unrelated historical measurements. The main measurement includes execution,
final trajectory records and common JSON materialization; native batches also
pay C++ JSON construction and Python parsing. Backend loading is separate:
approximately 205–209 ms for pyffish and 0.78–0.98 ms for minimal C++. Common
Python/package imports precede those backend-load measurements. Total process
time and per-round values are retained in the raw summary.

The main benefit is retaining the trajectory loop in C++. Wider batches did
not improve this serial controlled-actor workload. That finding does not predict
batch-size effects for learned inference or parallel workers.

## Implementation trade-offs

The import arm uses unmodified pyffish 0.0.90 for legal moves, FEN transitions and
check detection. Its Python adapter retains the current FEN, translates
coordinates/order and applies Qi's repetition/ply rules. The wheel's compiler
flags are unknown; exact package and binary bytes are frozen.

The minimal arm is a 203-line C++17 game core with precomputed geometry, a compact
board, cached legal actions, exact repetition tracking and the controlled actor
loop. Scalar and coarse execution use the same core. Snapshot conversion and
saved SHA-256 identities stay in the Python adapter. It contains no search,
model, teacher or threading. The local binary is 40,256 bytes versus 1,213,264
bytes for the imported extension; these sizes are not equivalent feature sets.

Maintaining the minimal rules implementation becomes our responsibility. A
persistent native wrapper around Fairy-Stockfish's core remains untested.

## Conformance and verification

Both candidates matched the Python reference on:

- All ten frozen replay fixtures, including repetition and the 300-ply boundary;
  both terminal diagrams, including precedence over draw conditions.
- 6,075 positions from 64 development trajectories: ordered legal actions,
  board, side, in-check, outcome, history and semantic state hash.
- Malformed, illegal and wrong-side moves; stale-guard precedence; post-terminal
  rejection; invalid full histories; input and fresh-result isolation.
- All 128 confirmation trajectories, identically across all 21 workers.

Minimal native batches also matched all 64 development trajectories at each of
four batch sizes (256 trajectory comparisons), and native depth-three perft
matched 79,666. These finite controls do not prove correctness for every diagram.

Five focused tests passed, including real HTTP backend injection and scalar
state atomicity. The C++ core passed AddressSanitizer and UndefinedBehaviorSanitizer
checks over perft, errors, repetition and 128 trajectories. The owning work item
records lint, documentation, catalog and cleanup verification. No production
runtime or shared contract changed; the full application gate was not rerun.

## Imported-binding diagnostic

A separate, post-hoc cProfile run used four development games capped at 96 plies.
The native `legal_moves` and `get_fen` calls accounted for 96.4% of measured time.
This diagnostic is separate from the three comparison rounds.

Current upstream [binding source](https://github.com/fairy-stockfish/Fairy-Stockfish/blob/master/src/pyffish.cpp)
rebuilds a position and initializes the variant for these operations;
[variant initialization](https://github.com/fairy-stockfish/Fairy-Stockfish/blob/master/src/ucioption.cpp)
initializes piece and bitboard structures. Repeated initialization is a plausible
explanation, not proven attribution inside the measured binary: we did not
profile native internal symbols or verify the current upstream source against
the published wheel's build. This result does not establish that Fairy-Stockfish's
native move generator is slow.

## Decision and limits

The minimal coarse loop passes the predeclared 2x advancement threshold in every
round. Scalar calls fall below that threshold; direct import falls outside the
within-20%-of-best reuse preference. Advance the minimal core to a realistic
generation integration study, retaining Python as the oracle and preserving
current defaults. Revisit reuse with a persistent, coarse engine-core binding.

Before production adoption, measure actor, observation, teacher, validation and
persistence costs and complete platform/lifecycle checks. This study covers
Apple Silicon macOS, short native timing windows and three local rounds with
uncontrolled desktop contention. Linux x86_64, threading, learned actors, native
search and production retained-examples/s remain untested. It establishes no
playing-strength or learning-quality improvement.

## Evidence and reproduction

- [Compact measured results](../../data/evaluation/native-backends-20260921.json).
- [Study sources and reproduction](../../data/experiments/native_backends_v1/README.md).
- [Raw timing summary](../../artifacts/native-backends-20260921/confirmation-01/summary.json).
- [Source, binary and toolchain manifest](../../artifacts/native-backends-20260921/confirmation-01/manifest.json).
- [Conformance counts](../../artifacts/native-backends-20260921/confirmation-01/validation.json).
- [Post-hoc imported-binding profile](../../artifacts/native-backends-20260921/import-diagnostic.txt).

The local ignored run directory retains the executed source/dependency tree,
complete per-worker trajectories, exact inputs, binary identities and validation
attempt record. Tracked sources, compact results and the catalog owner provide
the portable result; reproduce exact native bytes only with the retained binary
and its compatible host environment.
