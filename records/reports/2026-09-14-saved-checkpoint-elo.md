---
description: Development-selected saved MLP evaluated against six frozen strategies with replayable local Elo evidence.
scope: saved checkpoint playing-strength evaluation
status: experimental
last_update: 2026-09-14
document_class: report
report_outcome: inconclusive
inconclusive_reason: Development imitation selection cannot establish the strongest saved checkpoint; bootstrap failures prevent a reported interval.
review_trigger: A new supported checkpoint or a predeclared direct checkpoint comparison with fresh starts.
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-14"
---

# Saved checkpoint versus six strategies

The selected greedy MLP scored **298.1 local Elo**, sixth of
seven entrants, with alpha-beta fixed at 1000. Its observed result against random
was **6 wins / 22 draws / 4 losses** (53.125% score). Every search strategy scored
better against it. This is a useful weak-policy baseline, not evidence of a strong
player or proof that it is the strongest saved model.

## Checkpoint selection

Selected [natural-mixture block 1, seed 27, 200 updates](../../artifacts/learning/generated-followups-v1/semantic/study-retry-1/block-1-natural-updates-200-seed-27/policy.pt).
Its weights exactly match the earlier source-mixing `block-1-both-seed-27` model.
The saved recipe uses 4000 examples, a 64-unit absolute-coordinate MLP, Adam 0.01,
and one CPU thread. Checkpoint SHA-256: `c38fa6c9f38ec74ff02a90f04de02e2451158b6c35431f82bb69f8188ec32388`.

The predeclared rule ranked six-cell macro teacher agreement on the same 373
inspected development inputs; ties used lower cross-entropy, then path. The scan
found 322 files: 151 distinct compatible weight states scored, 28 compatible
duplicates, and 143 excluded prototype-format files. No scored checkpoint had
exact training-input overlap with these development inputs. The exclusions cover
30 architecture-screen checkpoints, 5 architecture smoke checkpoints, 45
perspective-tuning checkpoints and 63 other tuning checkpoints. The current
production player requires its versioned metadata/state-dictionary format.
Those exclusions limit the meaning of “best saved”: it is the best compatible MLP
under this imitation criterion, not the best of all research architectures.

The winner's balanced agreement was **19.300%**; its ordinary agreement was
**71/373 = 19.035%**. All 373 batch choices matched both fresh single-position
production inference and the original saved training predictions. The 0.260
percentage-point margin over the next checkpoint is small and is not a
statistically established strength difference.

| Saved checkpoint | Balanced agreement | Cross-entropy |
| --- | ---: | ---: |
| `artifacts/learning/generated-followups-v1/semantic/study-retry-1/block-1-natural-updates-200-seed-27/policy.pt` | 19.300% | 9.411 |
| `artifacts/learning/generated-followups-v1/scaling/study/mixed-16000-updates-50-seed-27/policy.pt` | 19.040% | 5.480 |
| `artifacts/learning/generated-source-mixing-v1-run3/study/block-1-intervention-seed-27/policy.pt` | 18.725% | 9.816 |
| `artifacts/learning/generated-followups-v1/scaling/study/mixed-16000-updates-200-seed-7/policy.pt` | 18.563% | 9.501 |
| `artifacts/learning/generated-followups-v1/scaling/study/resource-pilot/policy.pt` | 18.465% | 9.135 |

## Playing results

Each row contains 32 rated games: 16 short human-opening prefixes from 11 families,
with colors swapped. W/D/L and score are from the selected checkpoint's perspective.
A win scores 1 and a draw 0.5.

| Opponent | Local Elo | Checkpoint W / D / L | Checkpoint score |
| --- | ---: | ---: | ---: |
| Random | 213.1 | 6 / 22 / 4 | 53.12% |
| MCTS · 128 visits / depth 2 | 782.8 | 1 / 4 / 27 | 9.38% |
| Alpha-beta · 128 visits / depth 2 | 1000.0 | 0 / 15 / 17 | 23.44% |
| Enhanced alpha-beta · 128 visits / depth 2 | 1775.1 | 0 / 1 / 31 | 1.56% |
| Pikafish · 1k-node / depth-3 caps | 2907.6 | 0 / 0 / 32 | 0.00% |
| Pikafish · 100k-node / depth-8 caps | 4151.3 | 0 / 0 / 32 | 0.00% |

Across rated opponents the checkpoint recorded **7 wins / 42 draws / 143 losses**
in 192 games, or 14.583% score. Its 15 draws against alpha-beta were repetitions;
20 of its 22 draws against random hit the ply limit. These raw outcomes matter
alongside the scalar Elo estimate. The policy's mean measured choice time was
0.249 ms over 8377 rated-game decisions,
with one model call per choice and no tree search.

The [frozen benchmark method](../../docs/benchmark.md) fitted a Davidson MAP
estimate with explicit priors, draw propensity and color effect. There were
**195 successful / 5 failed family-bootstrap fits** out of 200. The required
95% interval is therefore **unavailable**; failed replicates were not silently
removed to print an interval. Pikafish-large's one-sided results also make its
finite rating gap dependent on the prior. These are local, regularized ratings;
resources are heterogeneous and the scale has no human or tournament meaning.

## Standard-start diagnostics

These 12 games are separate and excluded from the Elo fit.

| Opponent | Checkpoint W / D / L |
| --- | ---: |
| Alpha-beta · 128 visits / depth 2 | 0 / 2 / 0 |
| Enhanced alpha-beta · 128 visits / depth 2 | 0 / 0 / 2 |
| MCTS · 128 visits / depth 2 | 0 / 0 / 2 |
| Pikafish · 100k-node / depth-8 caps | 0 / 0 / 2 |
| Pikafish · 1k-node / depth-3 caps | 0 / 0 / 2 |
| Random | 1 / 1 / 0 |

## Execution and retained evidence

The reference panel completed 510/510 games, including 60 compatible pilot games
reused with source digests. The candidate completed 204/204 new games and reused
all 510 reference slots. Thus the combined evidence has 714 games: 672 rated and
42 standard-start diagnostics. This request executed 654 new games; none failed
or required a restart. New-game execution time was
31.61 minutes across both stages, excluding selection,
replay/summary overhead and idle time. All games were replay-validated; the final
immutable snapshot was independently read and its full projection matched the
runner's result. Its evidence digest is `486756a88706ca97fba7cc94ea77e1709456b84565f7fe4de3fbf4a9081b9eb4`.

- [Compact result and receipts](../../data/evaluation/saved-checkpoint-elo-20260914.json).
- [Predeclared protocol and selected identity](../../artifacts/benchmark-checkpoint-20260914/protocol.json).
- [Complete selection inventory and predictions](../../artifacts/benchmark-checkpoint-20260914/selection.json).
- [Selected-model inference verification](../../artifacts/benchmark-checkpoint-20260914/selection-verification.json).
- [Reference spec](../../artifacts/benchmark-checkpoint-20260914/reference-spec.json) and [candidate spec](../../artifacts/benchmark-checkpoint-20260914/candidate-spec.json).
- [Named player resources](../../artifacts/benchmark-checkpoint-20260914/players.json).
- [Reference run](../../artifacts/benchmarks/reference-development-20260914/manifest.json) and [candidate run](../../artifacts/benchmarks/checkpoint-development-20260914/manifest.json).
- [Verified immutable snapshot](../../artifacts/benchmarks/checkpoint-development-20260914/reports/486756a88706ca97fba7cc94ea77e1709456b84565f7fe4de3fbf4a9081b9eb4.json).
- [Selection script](../../data/evaluation/select_saved_checkpoint.py).
- [Owning work item and experiment ledger](../work-items/items/AB-EVAL-005-local-elo-benchmark.md).

No sealed pool was scored. The opening book has not been certified disjoint from
all entrant training sources. This evaluation supports the configured-player
comparison on these development starts; it does not confirm a globally strongest
checkpoint. Retain the measured baseline and revisit when another checkpoint or
supported architecture is ready for a predeclared direct comparison.

Recompute the native result without playing games:

```bash
.venv/bin/qi bench summarize --run artifacts/benchmarks/checkpoint-development-20260914
```
