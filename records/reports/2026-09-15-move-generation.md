---
description: Exact move-generation optimization with isolated timing controls and a calibrated search-budget follow-up.
scope: referee performance and alpha-beta playing strength
status: experimental
last_update: 2026-09-22
document_class: report
report_outcome: inconclusive
inconclusive_reason: The optimization and budget control passed, but the small development sample does not establish general playing strength or competitiveness with Pikafish.
review_trigger: A stronger evaluator or search recipe tested on fresh frozen development families against the same capped Pikafish profiles.
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15"
---

# Faster legal move generation

**Legal move generation is about 10.4× faster; complete PVS decisions at the same
1024-node budget are about 5.5× faster, with identical outputs on the fixed
controls.** The optimization passes the predeclared speed and equivalence gates.
The selected 4096-node setting beat 1024-node PVS **8–0**. Against Pikafish it
scored **0 wins / 3 draws / 13 losses** versus small and **0 / 0 / 16** versus
large. All **40/40 games** completed in **11.6 minutes**, with no failures or
interruptions. The speed optimization is adopted; the Pikafish strength target
remains unmet.

## What changed

The old generator considered all 90 target squares for every piece. For each
candidate it checked attacks by scanning all pieces again. The optimized referee
uses precomputed step destinations for horses, elephants, advisors, soldiers and
kings, scans occupancy along rook/cannon rays, and looks outward from the king
for attackers. Occupancy still controls horse legs, elephant eyes and cannon
screens; king safety is checked after each candidate move.

Legal moves retain their original source-square then target-square ordering.
The direct `reaches` geometry function remains unchanged. Ruleset identity,
repetition, ply limits, search recipes, node accounting and player versions remain
unchanged. The optimization benefits all consumers of the shared referee.

The [previous study](2026-09-15-enhanced-alpha-beta.md) found a large gap to
Pikafish and attributed 89.3% of one instrumented decision to legal generation.
That was a diagnostic; the repeated comparisons below establish the measured
speedup on a broader fixed workload.
[AB-EVAL-007](../work-items/items/AB-EVAL-007-move-generation.md) fixes the protocol.

## Correctness controls

- **7,292 board/side comparisons:** 2,646 distinct boards from the previous
  72 games and 1,000 seeded arbitrary boards, each checked for both sides.
  Every ordered legal-move tuple and check result matched the frozen old code.
- **72 complete games:** replay and terminal outcomes matched both referees.
- **Initial-position depth-three perft:** both counted **79,666** legal move
  sequences. This is a move-generation regression count, not a strength metric.
- **24 start/budget cases:** PVS decisions on the 12 previous starts at 128 and
  1024 visits, depth 4, matched across every field except elapsed time. The
  1024-visit cases were repeated in each timing round.
- Colocated independent exhaustive-oracle tests cover arbitrary placements,
  eight reachable trajectories, cannon screens and missing kings. Existing tests
  cover pinned pieces, facing generals, palace/river restrictions and adjudication.

These finite controls provide regression evidence, not a formal proof over every
possible position or history. Sample/source files and hashes are retained.

## Repeated timings

Three rounds, isolated old/new Python processes, alternating process order.
Legal-generation timings use 256 distinct prior-game boards, both sides (512
cold queries per implementation per round). Search timings use 12 prior opening
starts, cold referee caches per decision, PVS at 1024 visits/depth 4. Other local
tests were finished before measurement. Fixed geometry tables are initialized
before timing; these measurements cover steady-state decision work.

| Round | Mean legal query, old → new | Total-work speedup | Mean PVS decision, old → new | Total-work speedup |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.409 → 0.040 ms | 10.23× | 777.1 → 140.4 ms | 5.53× |
| 2 | 0.414 → 0.040 ms | 10.49× | 785.4 → 140.0 ms | 5.61× |
| 3 | 0.417 → 0.040 ms | 10.42× | 786.1 → 142.2 ms | 5.53× |

The required median decision-latency improvement passed in all three rounds
(5.51×, 5.57× and 5.52×). The narrow range describes these repeated runs, not
uncertainty over all possible workloads or hardware.

## Timing-only budget calibration

Each new budget received 36 decisions: the same 12 starts × three repeats.
The largest tested cap whose mean stayed below old PVS 1024 was selected before
any new game results. Search depth cap stays four.

| Implementation / visits | Mean decision ms | Mean completed depth |
| --- | ---: | ---: |
| Old / 1024 | 782.9 | 1.25 |
| Optimized / 2048 | 285.3 | 1.42 |
| Optimized / 4096 | 573.7 | 2.00 |
| Optimized / 8192 | 1181.5 | 2.75 |

**Selected: 4096 visits.** It uses four times the old node budget at 26.7% lower
mean latency on these starts. This is a coarse, timing-calibrated node cap, not a
per-move clock or a guarantee of matched latency on game trajectories.

## Frozen playing-strength follow-up

Eight next distinct development opening families after the 12 previously used
families, both colors against each Pikafish profile; first four families also
compare optimized PVS 4096 with optimized PVS 1024. Forty planned games.
No reserved test pool or training data is used; these are fresh-to-selection
families from the existing development book, not certified held-out data.

Pikafish keeps the pinned January 2, 2026 binary/network, one thread and 16 MiB
hash. Small: 1000 native nodes/depth 3. Large: 100000 native nodes/depth 8.
Seed 7, the same referee and automatic terminal conditions. A 30-minute execution
budget is checked before each game; a started game finishes. Only complete color
pairs score; failures and pending games remain explicit. No custom adjudication.

| Opponent | PVS 4096 W / D / L | Score | Candidate mean ms/move | Mean completed depth |
| --- | --- | ---: | ---: | ---: |
| PVS 1024 | 8 / 0 / 0 | 100% | 469.7 | 2.66 |
| Pikafish-small | 0 / 3 / 13 | 9.375% | 480.2 | 2.80 |
| Pikafish-large | 0 / 0 / 16 | 0% | 446.2 | 2.90 |

The three draws against small ended by repetition; all Pikafish losses ended
by checkmate. The control had seven checkmate wins and one stalemate win.
Candidate fallback occurred on only 1/386 decisions against small, 0/465 against
large and 0/289 against PVS 1024.

The practical strength criterion required at least 25% versus small **and** above
50% versus PVS 1024. Only the control criterion passed. The 40% closeness threshold
failed for both Pikafish profiles. More completed search depth alone does not
satisfy those criteria.

The 8–0 control directly compares search budgets on the same four families,
using the optimized referee for both players. It supports more search on this
sample, not broad superiority or equal-compute play. Comparing the three draws
with the previous study's zero score does not isolate a gain: the opening
families differ between studies.

## Decision

Adopt the faster shared referee: ordered outputs and fixed-budget decisions
passed the exact controls, and every timing round improved. Default node budgets
stay unchanged, so existing player configurations receive lower latency rather
than a silent behavior change. The measured stronger option is explicit:

```bash
.venv/bin/qi choose --state game.json --player alphabeta-pvs --nodes 4096 --depth 4
```

The saved CPU time makes this larger search affordable, but the evidence does
not establish a Pikafish competitor. Further strength work needs a stronger
evaluator or search recipe and a fresh frozen game comparison; no such additional
change is adopted by this experiment.

## Evidence and reproduction

- [Compact complete results](../../data/evaluation/movegen-20260915.json)
- [Timing/equivalence runner](../../data/experiments/movegen_optimization.py)
- [Shared-runner game orchestration and verifier](../../data/experiments/movegen_games.py)
- Local-only raw evidence under `artifacts/experiments/movegen-20260915/`:
  `games-summary.json`, `verification.json`, `equivalence.json`,
  `performance.json`, `games-manifest.json`, `before-hashes.json` and
  `after-hashes.json`.

The run directory retains `before/` and `after/` source trees, the dependency lock,
exact inputs, individual timing rows, script copies, frozen game specs and game
records. These detailed artifacts are local and ignored by Git. Tracked source,
scripts and compact findings remain in the repository. Re-measurement needs fresh
output paths and the retained old source; do not overwrite original measurements.
The worker verifies that it imported the explicitly selected source tree.

To verify existing game evidence without invoking players:

```bash
.venv/bin/python data/experiments/movegen_games.py \
  --run artifacts/experiments/movegen-20260915 --verify
```

To repeat with fresh output while retaining the same old-code control (the
source and prior 72-game artifacts must still be present):

```bash
study_run=artifacts/experiments/movegen-rerun
mkdir "$study_run"
cp -R artifacts/experiments/movegen-20260915/before "$study_run/before"
cp artifacts/experiments/movegen-20260915/before-hashes.json "$study_run/"
.venv/bin/python data/experiments/movegen_optimization.py --run "$study_run" --prepare
.venv/bin/python data/experiments/movegen_optimization.py --run "$study_run" --measure
QI_PLAYERS_CONFIG=artifacts/benchmark-checkpoint-20260914/players.json \
  .venv/bin/python data/experiments/movegen_games.py --run "$study_run"
```

A rerun measures the current checkout against the retained old source. It is a
new execution; original timings and game evidence remain unchanged.

## Verification

`make check` passed: **745 Python tests passed, one skipped**, five browser unit
tests passed, plus lint, documentation/catalog, OpenAPI/type checks and production
browser build. Both experiment scripts passed separate Ruff checks. The game
verifier checked frozen source/input/game hashes and replayed all games with the
shared evaluator. All 40 new games also replayed successfully under the frozen
**old** referee, with identical terminal outcomes. Timing aggregates and the
4096-node selection were independently re-derived from retained raw rows; every
current source/dependency file in the measured snapshot still matches its hash.
