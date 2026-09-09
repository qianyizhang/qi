---
description: Non-conclusive teacher generation pilots and documentation reconciliation.
scope: dataset generation evidence and advisory
status: experimental
last_update: 2026-09-09
document_class: report
report_outcome: inconclusive
inconclusive_reason: Small correlated corpora and query prototypes do not establish downstream learning benefit or production defaults.
review_trigger: Evaluate an integrated generator on independent held-out positions at equal preparation cost, including stronger-reference stability and downstream student results.
produced_by: doc-hygiene-audit@1.3.0
---

# Teacher generation pilot and session closeout

The [Training Data guide](../../src/qi/training_data/README.md#dataset-generation-advisory-non-conclusive)
owns the advisory. No production defaults, training targets or authority boundaries
changed. Persistent workers are a promising next implementation experiment;
search budget, candidate distribution and online training choices remain open.

## Evidence

[Saved aggregates](../../data/experiments/learning/history/teacher-generation-pilot-v1.json)
preserve the measurements and hashes of their local evidence files. Detailed
scripts, raw UCI output, source patch and per-position results remain in ignored
`artifacts/pikafish-*-20260909/` directories; they are not bundled with a fresh clone.
The teacher was pinned Pikafish 2026-01-02 on macOS arm64. Position sets were the
12 evaluation positions and, for quality, 24 related history prefixes. These are
not independent or representative training samples. Background load was uncontrolled.

| Experiment | Finding | Interpretation limit |
| :-- | :-- | :-- |
| Persistent workers | At 10k/depth 6, sustained medians were 289 / 497 / 825 / 1,121 queries/s for 1 / 2 / 4 / 8 single-thread workers. Larger hash and more threads did not help this workload. | Repeated positions, warm Python caches, shallow searches; prototype omits production analysis-payload construction. Not retained examples/s. |
| Removing depth 6 | On 12 positions mean work rose from 1,571 to 9,702 nodes; throughput fell 46–58%. On 36 positions agreement with a single-PV 1M reference rose from 24 to 26. | Modest, mixed reference agreement; no quality-optimal budget established. |
| All-move distributions | Against an all-move 1M reference, uncapped 10k to 100k reduced WDL JSD from 0.0332 to 0.0133 and raised tau-b from 0.671 to 0.776. | MultiPV reallocates the budget: median complete depth was only 2 at 10k. This is not the previous single-PV search with richer logging. |
| MultiPV/WDL cost | At depth 6, MultiPV 1 / 5 / all gave 441 / 316 / 157 queries/s; WDL on/off changed medians by -1.33% to +0.65%. | Fixed-node MultiPV can be faster while shallower. WDL output cost was not substantial in this pilot; estimates are not calibrated student outcomes. |
| Observational root trace | Moves and nodes matched release/control on 36 positions and control on 720 timed repeats; throughput difference was +0.10%. Effort shortlist recovered 64% of a depth-matched 50k MultiPV=5 top-five set and its selected move on 33/36 positions. | Of 1,412 latest returns, 1,391 were upper bounds. Only 152 moves had any earlier exact-window score, at median depth 2.5. Useful diagnostics, not a full ranking/probability distribution. |

JSD compares per-move WDL on identical legal support, averaged per position.
Tau-b accounts for ties; one position had no comparable ranking and was excluded.
Quality references are estimates and can themselves change with budget. Never
convert missing or bounded root-trace values into precise WDL targets. Matching
median search depth does not match each candidate's exploration.

## Reconciliation

- Replaced the throughput-only preference table in the active guide with one
  explicitly non-conclusive generation advisory; numerical history lives here.
- Removed the stale statement that no training pipeline exists from the teacher
  guide and linked its current Training Data consumer.
- Clarified node/depth stopping, per-process hash memory versus content hashes,
  per-candidate WDL versus move probabilities, and MultiPV versus observation.
- Preserved prototype availability limits. Node-only queries, persistent pools,
  MultiPV/WDL parsing, root traces and streaming training are not exposed by the
  production preparation config. Existing supported v1 data is not deprecated.

## Open decisions

Defer default changes. Revisit persistent-worker integration with full preparation
throughput and fixed-history/spec identity checks; revisit search quality on a
broader held-out corpus at equal total cost. Concurrent chunk generation/training
needs a separate lifecycle, fixed exclusions and contention/learning evaluation.
These are advisory review triggers, not an approved implementation plan.

## Verification

Aggregates were copied from saved experiment results with source SHA-256 receipts.
`UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed using installed
dependencies (lint, documentation, tests and production web build). The initial
plain invocation was blocked fetching a build dependency. Whitespace review passed;
the authoring checker returned advisory findings only.
