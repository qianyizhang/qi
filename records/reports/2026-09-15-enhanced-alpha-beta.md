---
description: Bounded budget, component-ablation and PVS experiments against two pinned Pikafish profiles.
scope: enhanced alpha-beta optimization evidence
status: experimental
last_update: 2026-09-22
document_class: report
report_outcome: inconclusive
inconclusive_reason: This small exploratory study cannot establish long-term potential or isolate a PVS strength gain from the larger search budget.
review_trigger: A faster search or stronger evaluator, frozen before a new paired-game comparison against the same Pikafish profiles.
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15"
---

# Enhanced alpha-beta: budget and search efficiency

**The larger-budget PVS variant beats the old Qi setting, but these small changes
do not bring it close to either tested Pikafish profile.** It scored 8 wins in
8 games against original enhanced, and lost all 16 games against each Pikafish
profile in the follow-up. All **72/72 planned games** completed in **18.1 minutes**,
with no failed or interrupted attempts; every game replay-validated.

The 8–0 improvement combines an eightfold visit budget with recipe changes.
At equal 1024-visit caps, scaled enhanced, lean and PVS all scored zero against
small Pikafish in screening. The evidence does **not** establish a PVS-specific
playing-strength gain.

## Question and prior evidence

The [previous panel](2026-09-14-saved-checkpoint-elo.md) gave enhanced alpha-beta
26 wins / 6 draws / 0 losses against basic alpha-beta, but 0/0/32 against each
Pikafish profile. Enhanced had only 128 Qi visits and a depth cap of two.

This experiment separates increasing that budget from removing costly components
and adding principal variation search (PVS). PVS probes later moves using a
narrow score window and fully re-searches those that can improve the best score.
The [preregistered protocol](../work-items/items/AB-EVAL-006-enhanced-potential.md)
fixes selection, follow-up families, budgets, stopping and decision thresholds.

## Implemented comparisons

| Profile | Qi visits / depth cap | Change from original enhanced |
| --- | --- | --- |
| Original | 128 / 2 | Existing recipe |
| Scaled | 1024 / 4 | Larger budget |
| Lean | 1024 / 4 | Remove exchange ordering and check extensions |
| PVS | 1024 / 4 | Lean plus principal variation search |

All retain positional evaluation, legal quiescence, move ordering and a 2048-entry
history-aware transposition table. Quiescence still searches legal check evasions.
Original recipe IDs/versions remain unchanged; lean and PVS have separate IDs.
Each re-search counts against the same node budget. Only finished iterations
supply the chosen search result; depth zero explicitly means fallback.

## Position probes

Twelve distinct development opening families, one start per family. Depth cap
four, cold referee caches per decision, rotating profile order. Each row has
12 observations; timings are descriptive local measurements, without repeats.

| Profile | Visits | Mean completed depth | Fallbacks | Mean ms/move |
| --- | ---: | ---: | ---: | ---: |
| Enhanced | 128 | 0.58 | 5/12 | 115.2 |
| Enhanced | 512 | 1.00 | 0/12 | 428.8 |
| Enhanced | 2048 | 1.42 | 0/12 | 1618.9 |
| Lean | 512 | 1.00 | 0/12 | 431.0 |
| Lean | 2048 | 1.42 | 0/12 | 1681.3 |
| PVS | 512 | 1.00 | 0/12 | 389.4 |
| PVS | 2048 | 1.42 | 0/12 | 1572.5 |

Increasing visits removes these fallback decisions. At 2048 visits, all three
recipes have the same mean completed ordinary depth. Removing SEE did not
produce a visible depth gain here: its charged work was only 6.9–9.5% of enhanced
visits. Quiescence work is included in the budget and extends beyond ordinary depth.

## Game conditions

First four distinct development families form the screen: all four profiles
play both colors against Pikafish-small. Highest score among scaled/lean/PVS
selects the follow-up entrant; ties use lower mean move latency, then ID.
The next eight families are fixed in advance for both Pikafish opponents;
the first four of those also compare the selected entrant with original enhanced.
This schedules 32 screen + 40 follow-up games.

Pikafish uses the pinned January 2, 2026 binary and NNUE network, one thread and
16 MiB hash. Small is capped at 1000 native nodes **and** depth 3; large at
100000 native nodes **and** depth 8. Actual reported work can be much less than
the node cap. Each move starts a fresh process, and latency includes that overhead.
Qi visits and native engine nodes are different units; compute is unequal.

Games use seed 7, both colors and the unchanged `xiangqi-training-v1` referee.
Only complete color pairs score. Checkmate, stalemate, repetition and the referee's
300-ply cap decide outcomes. No custom early adjudication is used. The 30-minute
game budget is checked before each game; a started game finishes and pending slots
remain visible if the bound is reached.

## Screening result

| Profile | W / D / L vs small | Score | Mean ms/move |
| --- | --- | ---: | ---: |
| Original | 0 / 0 / 8 | 0% | 83.7 |
| Scaled | 0 / 0 / 8 | 0% | 634.2 |
| Lean | 0 / 0 / 8 | 0% | 616.6 |
| PVS | 0 / 0 / 8 | 0% | 605.5 |

All 16 color pairs completed. PVS advances **only by the predeclared latency
tie-break**; the screen provides no strength advantage among the three variants.
The small timing differences are observations over their different game paths,
not an isolated speedup claim.

## Follow-up result

All entrants in this table face the selected PVS profile at 1024 visits/depth 4.
Eight fresh-to-selection development families face each Pikafish profile, with
both colors; four of these families form the original-enhanced control.

| Opponent | PVS W / D / L | PVS score | PVS ms/move | Mean PVS completed depth |
| --- | --- | ---: | ---: | ---: |
| Original enhanced, 128 / 2 | 8 / 0 / 0 | 100% | 484.9 | 2.01 |
| Pikafish-small, 1000 / 3 | 0 / 0 / 16 | 0% | 593.8 | 1.76 |
| Pikafish-large, 100000 / 8 | 0 / 0 / 16 | 0% | 603.2 | 1.92 |

PVS still used fallback on 17/367 decisions against small and 11/328 against
large; the 1024-visit budget does not always finish even the first iteration.
All 32 Pikafish follow-up losses ended by checkmate. The control wins were six
checkmates and two stalemates.

Small Pikafish actually reported a mean **208.4 nodes/move**, reaching depth 3
on all 375 decisions. Large reported **2729.9 nodes/move**, reaching depth 8
on all 336 decisions. Their mean latencies were 141.1 and 143.6 ms/move,
including process startup, versus roughly 600 ms for PVS. These are bounded
profiles, not unrestricted Pikafish.
The recorded binary/network hashes, native work and costs are in the compact
results and raw game choices.

The predeclared practical signal required at least 25% against small **and**
beating original enhanced. Only the second part passed. The 40% score criterion
for being close to each tested profile failed for both.

## Cost diagnosis and decision

A separately instrumented, cold-cache PVS decision on the first frozen opening
used 1024 visits and generated 33.9 million Python function calls. Legal move
generation consumed **89.3% of cumulative profiled time** (2.974 of 3.329 seconds).
Its geometry checks called `reaches` 2.78 million times. Quiescence occupied
92.2% and positional evaluation 51.8% of cumulative time; these are **overlapping
call stacks**, so the percentages must not be added. Instrumentation inflates
timing; this one decision diagnoses cost, not general speed or strength.

**Decision:** retain lean/PVS as explicit experimental recipes; do not promote
these results as a Pikafish competitor. If pursuing this direction, the next
useful engineering study is faster legal-move generation with output-equivalence
checks, followed by a fresh game comparison at matched elapsed-time budgets.
A faster implementation alone would not establish a stronger evaluator or
predict parity. Revisit after a materially faster search or a stronger evaluator
exists; freeze its profile and new development-family comparison before play.

## Evidence and reproduction

- [Compact verified results](../../data/evaluation/enhanced-potential-20260915.json)
- [Diagnostic runner](../../data/experiments/enhanced_diagnostics.py)
- [Resolved recipe](../../data/experiments/enhanced-potential-20260915.json)
- [Study runner and verifier](../../data/experiments/enhanced_potential.py)
- Local-only raw evidence under `artifacts/experiments/enhanced-potential-20260915/`:
  `summary.json`, `diagnostics.json`, `manifest.json`, `probes.json` and `starts.json`.

```bash
QI_PLAYERS_CONFIG=artifacts/benchmark-checkpoint-20260914/players.json \
  .venv/bin/python data/experiments/enhanced_potential.py \
  --config data/experiments/enhanced-potential-20260915.json \
  --output artifacts/experiments/enhanced-potential-rerun
.venv/bin/python data/experiments/enhanced_potential.py \
  --verify artifacts/experiments/enhanced-potential-20260915
.venv/bin/python data/experiments/enhanced_diagnostics.py \
  --run artifacts/experiments/enhanced-potential-20260915
```

Execution saves the exact Python source, dependency lock and experiment script in
`source.tar.gz`, with its hash in the manifest. This preserves the dirty execution
source without relying on a Git commit alone. Full game choices, timing, resource
identities and terminal snapshots stay in per-comparison JSON files. The verifier
uses the shared evaluator's replay and paired scorer, without invoking players.
Detailed artifacts and the source archive are local and ignored by Git; tracked
code, recipe and compact findings remain available in the repository.

## Verification

The shared `EvalRun` validator replayed every move, checked frozen participants,
full-history hashes, player diagnostics/budgets and final referee outcomes.
The study verifier checked frozen source/config/game file hashes and reconstructed
all paired scores. Original enhanced matched the pre-change implementation on
all 12 frozen probe starts, across every `Decision` field.

`make check` passed: **731 Python tests passed, one skipped**, five browser
request-lifecycle tests passed, plus lint, docs/catalog, OpenAPI/type checks and
the production browser build. Added coverage checks PVS against exhaustive
minimax, quiescence score parity, real re-searches, interruption and trace/work
accounting. Source snapshots predate the additional tests; all 94 runtime Python
files match the executed archive exactly. The local-only receipt is
`artifacts/experiments/enhanced-potential-20260915/verification.json`.

## Interpretation limits

The screen is exploratory selection; the follow-up families were fixed before
selection but come from an already-used development book. No certified held-out
claim, training-disjoint claim or locked-pool evaluation is made. These small
samples cannot establish equality with either profile, much less unrestricted
Pikafish. Longer survival, teacher agreement, completed search depth and a finite
regularized Elo estimate would not substitute for the paired game scores.
