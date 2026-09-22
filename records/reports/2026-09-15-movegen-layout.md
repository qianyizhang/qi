---
description: Measured NumPy versus occupancy-mask move generation and equivalent faster positional attack queries.
scope: referee and positional evaluation performance
status: stable
last_update: 2026-09-22
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15"
---

# Further move-generation optimization

**Complete PVS decisions are another 2.65× faster at 1024 visits and 2.47×
faster at 4096 visits**, relative to the already optimized
[previous implementation](2026-09-15-move-generation.md). All measured decisions,
evaluation terms, depths and search counters match. Adopted: integer occupancy
masks and shared attack lookups. The tested batched NumPy prototype was about
9% slower than the baseline legal generator and was rejected.

## Answer to the review comments

The nested `_movement_tables()` loops run **once at import**, not at every search
node. The original 100-build diagnostic measured a median **0.524 ms**. Replacing
these loops with tensor operations would target a small startup cost. Ray creation
now uses direct `range` expressions; piece-specific setup retains straightforward
loops and builds immutable tuples. Temporary lists accommodate different numbers
of destinations per square. Small dictionaries select piece/side tables; neither
those dictionaries nor the setup appends were the main per-move cost.

The useful representation change is in **candidate king safety**. Occupancy is a
90-bit Python integer. A hypothetical move clears its source bit and sets its
destination bit. For each potential attacker, integer `bit_count()` counts
occupied squares along its path: zero for a rook, one for a cannon, and an empty
leg/eye for a horse/elephant. Captured attackers are excluded. Enemy pieces are
matched once per king destination, eliminating repeated board copies and attack
scans for each candidate move. Move ordering and referee semantics stay intact.

The follow-up profile also found that positional `king_safety` still scanned all
90 squares for each palace-zone target. It accounted for 56.5% of one instrumented
PVS decision. The evaluator now asks the referee's `is_attacked` lookup, with the
same geometric semantics and unchanged coefficients. Empty targets, occupied
targets, cannon screens, flying kings and pinned attackers retain their existing
meaning. This is an execution change, not a new evaluation formula.

## NumPy screen

Both prototypes shared the existing pseudo-legal candidate generator. NumPy
converted the board once, materialized all candidate boards together, gathered
precomputed padded step/ray arrays, and checked attackers using array comparisons
and cumulative occupancy counts. Thus this was a batch per position, not repeated
scalar calls disguised as vectorization. Timings include conversion, candidate
materialization and returning ordered move strings; NumPy import/setup is separate.

| Prototype | Mean cold legal query, three rounds | Outcome |
| --- | ---: | --- |
| Existing tuples and per-candidate board checks | 39.56 µs | Control |
| Batched NumPy 2.5.3 | 43.11 µs | 9.0% slower |
| Integer masks | 15.34 µs | 2.58× faster |

Each prototype matched all **7292** inherited board/side queries before timing.
Each round used the same 256 boards, both sides, with reversed order in the middle
round. This screen was in one process with uncached calls; the adoption experiment
below used isolated processes. One fresh NumPy import took **45.7 ms**; its array
setup took **0.37 ms**. These startup observations are diagnostics, not a repeated
framework-startup comparison. Torch/GPU was not tested because NumPy failed the
predeclared screen. This does not establish how arrays perform on large training
batches or a different vectorized design.

## Isolated end-to-end comparison

Three rounds, alternating baseline/final order, separate processes and cold
referee caches per decision. Each source received 512 legal queries and 12 PVS
starts at each of 1024 and 4096 visits, depth four, seed seven. The intermediate
source uses masks with the original evaluator, separating the two contributions.

| Workload | Baseline mean | Masks only | Masks + attack lookup | Final speedup |
| --- | ---: | ---: | ---: | ---: |
| Legal query | 45.53 µs | 18.11 µs | 17.58 µs | 2.59× |
| PVS, 1024 visits | 170.15 ms | 121.25 ms | 64.15 ms | 2.65× |
| PVS, 4096 visits | 627.19 ms | 476.00 ms | 254.25 ms | 2.47× |

Final speedups by round: **2.73 / 2.64 / 2.58×** at 1024 visits and
**2.58 / 2.40 / 2.42×** at 4096. Every round reduced median latency at both caps;
pooled mean improvements exceeded the required 5%. Absolute times varied across
rounds, so these paired measurements support the claim; multiplying speedups from
separate historical runs would not be a fresh measurement.

The setup trade-off is small but explicit: in the final 100-build comparison,
baseline table construction took **0.554 ms**, final **1.183 ms**. Reachable Python
table objects increased from **309,000 to 1,227,760 bytes**, deduplicating shared
objects. This is roughly 0.9 MB extra table storage, not a measurement of process
RSS. Additional precomputation saves repeated work during play.

## Behavioral controls

- **7292** board/side queries: all ordered moves, check results and complete
  evaluation breakdowns equal to the frozen baseline.
- **180,000** arbitrary-target attack queries: 1000 arbitrary boards × both
  sides × every square, equal to independent exhaustive `reaches` scans.
- **112** recorded games: replayed with matching boards, side to move and
  terminal outcomes under both sources. These are existing games, not new matches.
- Initial depth-three move-sequence count: **79,666** under both sources.
- **24** distinct PVS start/budget cases × three rounds × three implementations:
  all Choice fields match except elapsed time, including evaluation and counters.
- Focused tests cover creating/removing cannon screens, captured attackers,
  blocked horse legs and moving the king into an attacked file.

Finite regression controls are not a proof over every board. Inputs are reused
development positions: 2646 distinct prior-game boards plus 1000 arbitrary boards.
Search caps and default recipes remain unchanged. The profile-driven evaluator
refinement was recorded before its implementation and final timings; it was an
adaptive follow-up, not an independently predeclared hypothesis.

## What this establishes about Pikafish

More search is now affordable, but this study establishes execution speed only.
At unchanged node caps the decisions stayed identical. No new matches or node
calibration were run. The last playing evidence remains **0 wins / 3 draws / 13
losses** versus small Pikafish and **0 / 0 / 16** versus large at PVS 4096.
Closing that gap still needs a measured search/evaluation strength improvement or
a new timing-calibrated match study. This change alone is not evidence of parity.

## Evidence and reproduction

- [Protocol and experiment catalog owner](../work-items/items/AB-EVAL-008-movegen-layout.md)
- [Compact results](../../data/evaluation/movegen-layout-20260915.json)
- [NumPy and mask prototypes](../../data/experiments/movegen_layout.py)
- [Equivalence and isolated timing controller](../../data/experiments/movegen_layout_validation.py)
- Local-only raw evidence under `artifacts/experiments/movegen-layout-20260915/`:
  `screen.json`, `equivalence.json`, `performance.json` and `verification.json`.

The local ignored run directory retains `before/`, `masks-only/`, `after/`, their
hashes, dependency lock, exact inputs, source copies of the runners, individual
timing rows and replay histories. Compact results and scripts are retained in the
repository alongside the code. The existing timing worker verifies its imported source path. To repeat
timing against these exact three snapshots without overwriting original results:

```bash
study_run=artifacts/experiments/movegen-layout-rerun
mkdir "$study_run"
cp -R artifacts/experiments/movegen-layout-20260915/before "$study_run/"
cp -R artifacts/experiments/movegen-layout-20260915/masks-only "$study_run/"
cp -R artifacts/experiments/movegen-layout-20260915/after "$study_run/"
cp artifacts/experiments/movegen-layout-20260915/timing-boards.json "$study_run/"
cp artifacts/experiments/movegen-layout-20260915/probe-starts.json "$study_run/"
.venv/bin/python data/experiments/movegen_layout_validation.py --run "$study_run" --measure
```

Prototype reproduction requires the same `before/` plus the retained
`positions.json` and `timing-boards.json`, optional NumPy installed, and a fresh
output directory. Run `movegen_layout.py --run <directory>`. The production referee
adds no NumPy, Torch or other dependency.

## Verification

`make check` passed: **752 Python tests, one skipped**, five browser tests,
Ruff lint/format, documentation/catalog validation, API/type checks and production
browser build. Both new experiment scripts passed separate Ruff checks. The first
gate attempt found two missing work-item headings and the not-yet-written receipt;
both were corrected before the successful run, and both logs are retained.
All frozen source/input hashes match; current runtime source matches the measured
final snapshot. Reported timing means were re-derived from the individual raw
rows. The verification receipt retains these checks and measurement hashes.
