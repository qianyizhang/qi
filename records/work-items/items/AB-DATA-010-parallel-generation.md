---
description: Opt-in two-worker policy generation with durable shards and validated collection publication.
scope: training data generation
status: experimental
last_update: 2026-09-22
document_class: work_record
work_id: AB-DATA-010
work_status: done
work_kind: build
added: 2026-09-22
tags: domain, performance
depends_on: AB-DATA-009
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-22"
---

# AB-DATA-010 — Supported parallel generation

## Intent

Integrate the [two-worker result](../../reports/2026-09-21-generation-optimization.md)
into the policy generation runner. Its 1.770x throughput excludes production
combination; this slice adds durable ownership, recovery and validated publication.

## Context and Trade-offs

The user accepted both recommendations on 2026-09-22: retained worker shards plus
one combined SQLite collection; stop the pool on failure and require explicit
resume. Serial remains the default; two workers are opt-in.

Whole sources are scheduled in frozen order into two slots. Each source keeps
its original ID, indices and RNG streams, one collection and independent teacher
sessions. All attempts remain in shards. Only after every source completes does
bounded replay/identity validation build and atomically publish the combined file.
A cross-shard split/family/trajectory conflict prevents publication and retains
all evidence; it never relabels or silently excludes a completed game.

The initial boundary requires independent sources and a fresh owned output.
External collections, generated-parent lineage and implementation-repair
continuations remain serial. Resume requires the exact recipe, runtime and
implementation; changed implementations require a new output and explicit future
reconciliation. A published collection is reused, never regenerated or overwritten.

## Acceptance Criteria

- Serial defaults, teacher budgets, RNG/portable identities and WAL/FULL per-move
  durability remain unchanged. No training or overnight batch is authorized.
- Real process tests show overlap, pool cancellation/child cleanup, failure
  evidence, explicit resume, completed-game reuse and combined-output equality.
- Preserve attempt and occurrence identities and first successful label ordering.
  Validate replay, outcome, occurrence indexes, teacher requests and source ownership.
- One coordinator owns each output; shard writes are exclusive. No incomplete
  combined file is published. Existing exports and independent verification work.
- Shared wall allowance covers queued jobs and combination. RSS/free-space guards
  cover the pool; unsupported aggregate OS-write guards fail before output creation.
- Keep code in the Training Data package, with a thin existing CLI-script entry.
  Run affected integration tests and `make check`.

## Bounded confirmation protocol

Extend `generation-workers-20260921`, holding its pinned 16-game, four-development-
family recipe, seed, single-thread teachers and budgets fixed. Three alternating
fresh serial/two-worker production invocations, at most 180 seconds per invocation
and 20 minutes total. Time complete CLI invocations including archive/startup and
combination. Independently compare normalized trajectories, selections and labels
against serial and verify SQLite integrity. Do not overlap builds/tests or discard
slow rounds. Report all pairs and peak sampled RSS with its shared-page/sampling
limits. Expect at least 1.3x median throughput and exact equality; a miss means
retain opt-in functionality without claiming the experimental gain survived
integration, and profile the added overhead. No playing-strength inference.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-22 | GPT-6 | — | wip | User locked output and stop/resume decisions and authorized implementation. |
| 2026-09-22 | GPT-6 | wip | done | Lifecycle/export tests, full repository gate and three exact-output production comparisons pass. |


```experiment
{
  "schema_version": 1,
  "id": "parallel-generation-20260922",
  "title": "Supported parallel policy generation",
  "question": "Does the two-worker throughput gain survive validated combined collection publication?",
  "kind": "performance",
  "topics": [
    "generation",
    "workers",
    "collection",
    "recovery"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Three alternating fresh serial/two-worker production CLI pairs with the previous 16-game development-family recipe, pinned teachers, seed and budgets. Include startup/archive/validation/combination in wall time. Bound each invocation to 180 seconds and all comparisons to 20 minutes. Require exact normalized outputs and median throughput >=1.3x; retain every repeat and failure.",
  "limitations": "",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "generation-workers-20260921",
      "relationship": "extends",
      "contribution": "Adds production pool lifecycle, durable recovery and verified combined collection publication to the isolated-worker experiment."
    }
  ],
  "novelty": "Measures complete supported parallel execution including source archiving and combined collection validation/publication."
}
```

## Implementation Ledger

- **2026-09-22 — implementation:** Two whole-source worker slots, retained failure
  attempts, explicit resume, bounded combination and atomic publication are
  implemented in Training Data. Hermetic process/replay/export tests pass.
  Full repository gates and confirmation pass. **Review:** self-review.

- **2026-09-22 — finding:** Production parallel execution reaches 1.704x median
  paired throughput (1.741x, 1.672x, 1.704x), including 0.550-second median
  combination. All six cells match 16 games/1,402 plies/169 selections/545 analyses.
  RSS medians are 652.8/1,241.7 MiB. Real publication resume preserves the file hash.
  See the [report](../../reports/2026-09-22-parallel-generation.md) and
  [compact evidence](../../../data/evaluation/parallel-generation-20260922.json).
  `make check`: 837 passed, one optional MPS skip, five web tests; 15 focused
  integration tests after adding three final checks. **Review:** self-review.



```experiment
{
  "schema_version": 1,
  "id": "parallel-generation-20260922",
  "title": "Supported parallel policy generation",
  "question": "Does the two-worker throughput gain survive validated combined collection publication?",
  "kind": "performance",
  "topics": [
    "generation",
    "workers",
    "collection",
    "recovery"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Three complete production CLI comparisons give 1.741x, 1.672x and 1.704x throughput, median 1.704x, with identical 16 games/1402 plies/169 selections/545 retained analyses. Combination costs 0.550 seconds median; summed sampled RSS medians are 652.8 and 1241.7 MiB. Real publication resume reuses 16 games without changing the combined file hash.",
  "conditions": "Three alternating fresh serial/two-worker production CLI pairs with the previous 16-game development-family recipe, pinned teachers, seed and budgets. Include startup/archive/validation/combination in wall time. Bound each invocation to 180 seconds and all comparisons to 20 minutes. Require exact normalized outputs and median throughput >=1.3x; retain every repeat and failure.",
  "limitations": "One local macOS machine, fixed development-family workload, three timing repetitions. Sampled summed RSS can double count shared pages and miss peaks. No Linux or overnight execution. Independent canonical audit follows timing. Parallel supports independent whole sources and fixed-implementation resume; aggregate OS-write limits remain serial.",
  "decision": "Adopt opt-in --workers 2 with retained source shards, failure cancellation, explicit resume and verified atomic combined publication. Keep serial/Python defaults and teacher/durability semantics unchanged.",
  "revisit": "Measure broader source/work imbalance and worker counts before changing limits/defaults; design aggregate OS-write accounting and cross-version recovery separately.",
  "evidence": [
    {
      "path": "records/reports/2026-09-22-parallel-generation.md",
      "role": "report",
      "sha256": "fda1072863c776cf9faf726e307d04d9621a3e98767ea12d71a44f991c5ebd23"
    },
    {
      "path": "data/evaluation/parallel-generation-20260922.json",
      "role": "results",
      "sha256": "8030574628cc106a65fceac7b11422b26455f34076f6373e39763397e74fcf87"
    },
    {
      "path": "artifacts/parallel-generation-20260922/verification.json",
      "role": "results",
      "sha256": "2c8571509199474ad0f4ef566b02bb644b35ce71f604b855f6c6c8e60fb393a8"
    },
    {
      "path": "artifacts/parallel-generation-20260922/confirmation-01/summary.json",
      "role": "results",
      "sha256": "5ea9f25a8bf1e1663ea94335464f80d6a3699d41ca73b7230b6c021a8f4fa000"
    },
    {
      "path": "artifacts/parallel-generation-20260922/confirmation-01/runtime.json",
      "role": "source",
      "sha256": "927c20842c4367cfd00e4a46b90b1ef1d1535cc85e003aa38427ff6d232ff7c7"
    },
    {
      "path": "artifacts/parallel-generation-20260922/confirmation-01/config.json",
      "role": "config",
      "sha256": "d3f0fc6394b9d1ae6237337431a93154809e6b223c214a982ab87dc04ad2d6d6"
    },
    {
      "path": "artifacts/parallel-generation-20260922/confirmation-01/study.py",
      "role": "source",
      "sha256": "426a78a5dfb37a8af61f5f331a8eace56fdd6f0da220a8d749293c6438fde150"
    },
    {
      "path": "artifacts/parallel-generation-20260922/confirmation-01/checks.py",
      "role": "source",
      "sha256": "12a6a1679386b47c68ee847973be26579e147db7c5abfcd125640a6fa0149b68"
    },
    {
      "path": "artifacts/parallel-generation-20260922/real-resume.json",
      "role": "results",
      "sha256": "a3215be97eae3b97b22971bd5dc03e36cee990a70ee5385584a0e64683f8edcf"
    },
    {
      "path": "artifacts/parallel-generation-20260922/make-check.log",
      "role": "results",
      "sha256": "45af9192c82979b2644053ac57c5230b0d544e300adf1ae1d4e3f02f9387a947"
    },
    {
      "path": "artifacts/parallel-generation-20260922/focused-tests.log",
      "role": "results",
      "sha256": "98d7113fedf196565bb7dcc35baf28c34485887328cff59846ae4c50971be219"
    }
  ],
  "prior_work": [
    {
      "id": "generation-workers-20260921",
      "relationship": "extends",
      "contribution": "Adds production pool lifecycle, durable recovery and verified combined collection publication to the isolated-worker experiment."
    }
  ],
  "novelty": "Measures complete supported parallel execution including source archiving and combined collection validation/publication."
}
```
