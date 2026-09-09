---
description: Measure the effect of substantially more teacher labels with the policy and optimization recipe fixed.
scope: backlog item
status: stable
last_update: 2026-09-09
document_class: work_record
work_id: AB-LEARN-004
work_status: wip
work_kind: research
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-003
residual_of: none
residual_items: none
---

# AB-LEARN-004 — Scale policy training data

## Intent

Test the user's hypothesis that 768 training positions is too small to assess
policy generalization. Increase data before changing the model or curriculum.

## Acceptance Criteria

- Compare nested 768, 3072 and 12288 position subsets from one fresh dataset,
  with the same held-out source games and initialization seeds 7/17/27.
- Keep the existing 1261-64-8100 float32 MLP, full-batch Adam at LR .01,
  200 updates, 1000-node/depth-3 teacher, and random 32-ply source games fixed.
- Retain replayable datasets, manifests, checkpoint identities, complete-seed
  results and verification; distinguish imitation from playing strength.
- Make bounded larger generation/experiment runs usable through the CLI, test
  parallel selection stability and existing leakage guards, and document results.

## Context and Trade-offs

The earlier width, duration and regularization sweeps only assessed a tiny-data
regime. Their negative findings do not establish that the current model cannot
benefit from substantially more examples. Hold optimization passes constant;
compute grows with data size. No learning-rate or checkpoint selection on the new
holdout. Full-batch training fits this host's scale without changing optimizer
semantics. No architecture, curriculum, value target or search change in this study.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User requested a substantial data-size experiment first. |

## Implementation Ledger

### 2026-09-09 — decision: lock the comparison before generation

- Evidence: `artifacts/learning/data-scaling-v1/selection.json` fixes sizes,
  seeds and recipe before labels are generated. Seed 211, 1056 source games,
  up to 16 sampled positions per game, one-quarter of games held out.
- Consequence: raise bounded dataset capacity to 2048 games/32768 labels and
  generation deadline to 7200 seconds. Add 1-4 workers with fresh single-threaded
  engines and seeded result ordering. Raise explicit fit/matrix deadline maxima
  to 600/7200 seconds; keep all defaults and training semantics unchanged.
- Follow-up: filter previously inspected dataset inputs before fitting; record
  retained input identities and counts. Evaluate all nine locked fits once.
- Review: not-required. Weekly quota at start: 7% used, below the user's 25% stop.
