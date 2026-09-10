---
description: Non-conclusive teacher generation pilots and documentation reconciliation.
scope: dataset generation evidence and advisory
status: experimental
last_update: 2026-09-10
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


```experiment
{
  "schema_version": 1,
  "id": "teacher-budget-20260909",
  "title": "Teacher search budget and depth-cap pilot",
  "question": "Does removing depth 6 or raising search nodes improve agreement with a stronger teacher reference?",
  "kind": "teacher",
  "topics": [
    "teacher quality",
    "stronger teacher",
    "1M reference",
    "depth cap",
    "node budget",
    "top-1 agreement"
  ],
  "execution": "complete",
  "conclusion": "inconclusive",
  "finding": "Agreement with the single-PV 1M-node reference was 24/36 at 10k/depth 6, 26/36 at uncapped 10k, and 31/36 at uncapped 100k. Removing the depth cap reduced throughput by 46–58% in the separate 12-position timing set.",
  "conditions": "Pikafish 2026-01-02, macOS arm64, Threads=1 and Hash=16 MiB for quality; 12 evaluation positions plus 24 related history prefixes (36 observations). September 9, 2026 exploratory pilot.",
  "limitations": "Small correlated corpus; reference answers are estimates, not ground truth or a proven upper bound. No student training or playing-strength measurement.",
  "decision": "Keep production defaults; use this evidence when designing a broader teacher audit or downstream student comparison.",
  "revisit": "Independent held-out positions, equal preparation cost, stronger-reference stability, or downstream student results.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/teacher-generation-pilot-v1.json",
      "role": "results",
      "sha256": "72a28c2a44176a7d289b66983d3fe05b7d0073ab1869d5c4e26892a5ad8dbabf"
    },
    {
      "path": "artifacts/pikafish-depth-cap-20260909/summary.json",
      "role": "results",
      "sha256": "71dc1b7dbc958b71cc1e77f9f013fee213df29e71fa9af45cec07a9954048663"
    },
    {
      "path": "artifacts/pikafish-depth-cap-20260909/report.md",
      "role": "report",
      "sha256": null
    },
    {
      "path": "artifacts/pikafish-depth-cap-20260909/run.py",
      "role": "source",
      "sha256": null
    }
  ],
  "prior_work": [],
  "novelty": "Retrospective registration of the original study; no new execution or historical priority claim."
}
```


```experiment
{
  "schema_version": 1,
  "id": "teacher-multipv-20260909",
  "title": "All-move MultiPV and WDL pilot",
  "question": "How do candidate distributions converge toward an all-move 1M reference, and what do MultiPV/WDL cost?",
  "kind": "teacher",
  "topics": [
    "teacher quality",
    "stronger teacher",
    "1M reference",
    "MultiPV",
    "WDL",
    "candidate ranking",
    "JSD",
    "tau-b"
  ],
  "execution": "complete",
  "conclusion": "inconclusive",
  "finding": "Uncapped 10k to 100k reduced mean WDL JSD from 0.0332 to 0.0133 over 36 positions and raised tau-b from 0.671 to 0.776 over 35 comparable rankings. At depth 6, MultiPV 1/5/all throughput was 441/316/157 queries per second.",
  "conditions": "Pikafish 2026-01-02, macOS arm64, Threads=1 and Hash=16 MiB for quality; 12 evaluation positions plus 24 related history prefixes (36 observations). September 9, 2026 exploratory pilot. Quality uses last complete same-depth exact all-move sets; timing uses the 12-position set.",
  "limitations": "Small correlated corpus; reference answers are estimates, not ground truth or a proven upper bound. No student training or playing-strength measurement. MultiPV reallocates search effort; median complete depth at 10k was only 2. WDL is per-candidate, not a move-probability distribution.",
  "decision": "Do not adopt all-move targets from this pilot alone.",
  "revisit": "Broader matched-cost study with downstream students and reference stability.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/teacher-generation-pilot-v1.json",
      "role": "results",
      "sha256": "72a28c2a44176a7d289b66983d3fe05b7d0073ab1869d5c4e26892a5ad8dbabf"
    },
    {
      "path": "artifacts/pikafish-multipv-20260909/summary.json",
      "role": "results",
      "sha256": "2336ac4b09478d522813576adc83a26cefd0f44af1e94a28918fea5187c55aa8"
    },
    {
      "path": "artifacts/pikafish-multipv-20260909/report.md",
      "role": "report",
      "sha256": null
    },
    {
      "path": "artifacts/pikafish-multipv-20260909/run.py",
      "role": "source",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "teacher-budget-20260909",
      "relationship": "extends",
      "contribution": "Adds all-move distribution and ranking stability plus MultiPV/WDL cost to the single-PV budget audit; does not train students."
    }
  ],
  "novelty": "Adds all-move distribution and ranking stability plus MultiPV/WDL cost to the single-PV budget audit; does not train students."
}
```


```experiment
{
  "schema_version": 1,
  "id": "teacher-throughput-20260909",
  "title": "Persistent teacher worker throughput pilot",
  "question": "Can persistent workers improve local query throughput?",
  "kind": "performance",
  "topics": [
    "teacher",
    "persistent workers",
    "throughput",
    "preparation cost"
  ],
  "execution": "complete",
  "conclusion": "inconclusive",
  "finding": "At 10k/depth 6, sustained medians were 289/497/825/1121 queries per second for 1/2/4/8 single-thread workers.",
  "conditions": "September 9, 2026; pinned Pikafish; repeated 12-position workload with fresh and persistent processes, worker/thread/hash variants.",
  "limitations": "Warm caches, uncontrolled desktop load and a query prototype omitting production analysis-payload construction; not retained examples per second or teacher quality.",
  "decision": "Promising implementation candidate; later full-preparation evidence is recorded under persistent-teacher-v1.",
  "revisit": "Representative full preparation at stronger budgets and larger distinct-position batches.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/teacher-generation-pilot-v1.json",
      "role": "results",
      "sha256": "72a28c2a44176a7d289b66983d3fe05b7d0073ab1869d5c4e26892a5ad8dbabf"
    },
    {
      "path": "artifacts/pikafish-throughput-20260909/results.json",
      "role": "results",
      "sha256": "23e223c5e9b9f6902e86227d0b9ae9365664d35fd68d5885695b4cd649fffb1c"
    },
    {
      "path": "artifacts/pikafish-throughput-20260909/sustained.json",
      "role": "results",
      "sha256": "96d3594697c0f30b975327c12902259c1e4b90c3bcdadfb76a81546f57dd16eb"
    }
  ],
  "prior_work": [],
  "novelty": "Retrospective registration of the original study; no new execution or historical priority claim."
}
```


```experiment
{
  "schema_version": 1,
  "id": "teacher-root-trace-20260909",
  "title": "Observational root trace pilot",
  "question": "Can root observations supply useful diagnostics without changing search decisions?",
  "kind": "teacher",
  "topics": [
    "teacher quality",
    "root trace",
    "candidate ranking",
    "bounds",
    "diagnostics"
  ],
  "execution": "complete",
  "conclusion": "inconclusive",
  "finding": "Moves and nodes matched on 36 positions and 720 timed repeats. Of 1412 latest root returns, 1391 were upper bounds; only 152 moves had an earlier exact score, at median depth 2.5. Effort shortlist recovered 64% of a depth-matched top-five reference.",
  "conditions": "Pikafish 2026-01-02, macOS arm64, Threads=1 and Hash=16 MiB for quality; 12 evaluation positions plus 24 related history prefixes (36 observations). September 9, 2026 exploratory pilot. Uses patched/control/release comparisons and MultiPV=5 references.",
  "limitations": "Mostly bounds or stale shallow exact scores; depth matching does not match per-candidate exploration. No full precise ranking or WDL distribution.",
  "decision": "Retain as diagnostics only; never turn missing or bounded values into precise targets.",
  "revisit": "An integrated trace consumer with preserved invariance and explicit bound semantics.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/teacher-generation-pilot-v1.json",
      "role": "results",
      "sha256": "72a28c2a44176a7d289b66983d3fe05b7d0073ab1869d5c4e26892a5ad8dbabf"
    },
    {
      "path": "artifacts/pikafish-root-trace-20260909/summary.json",
      "role": "results",
      "sha256": "346bb27b2df2498d71cfc420ac65e9bf22acb1091a2bcba4038b037ffbf3286a"
    }
  ],
  "prior_work": [
    {
      "id": "teacher-multipv-20260909",
      "relationship": "extends",
      "contribution": "Investigates an observational alternative to MultiPV and exposes its incomplete score support."
    }
  ],
  "novelty": "Investigates an observational alternative to MultiPV and exposes its incomplete score support."
}
```
