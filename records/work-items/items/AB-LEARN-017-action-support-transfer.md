---
description: Separate positive action coverage from transfer through shared policy representations.
scope: backlog item
status: experimental
last_update: 2026-09-12
document_class: work_record
work_id: AB-LEARN-017
work_status: deferred
work_kind: research
added: 2026-09-12
tags: domain
depends_on: AB-LEARN-016
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-12"
---

# AB-LEARN-017 — Positive action support and representation transfer

## Intent

Explain whether dense-head failures on unseen action labels are driven by missing
positive supervision, and whether spatial sharing transfers to combinations still
lacking positive examples. This is the recommended follow-up to the
[architecture screen](AB-LEARN-016-architecture-surfaces.md), not authorization
to launch another run. Freeze the matching procedure, fresh evaluation and budget
before execution; no architecture default has been selected.

## Acceptance Criteria

- Use two prespecified models: mover-relative dense MLP64 and spatial pair CNN32.
  Select action groups from training data only, before inspecting fresh evaluation.
- Construct matched positive-support and withheld-positive training conditions.
  Keep total rows, source/phase and trajectory contribution comparable, retaining
  legal negative exposure. Verify feasibility before fitting and quantify every
  unavoidable matching difference. Do not select a cohort from favorable dev errors.
- Use fresh source games and input-isolated evaluation; preserve existing sealed
  boundaries unless a separate confirmation decision explicitly opens them.
- Predeclare tests of selective recovery on supplied-positive groups and transfer
  on still-withheld groups. Report target rank/probability, non-forced agreement,
  matched seen/unseen slices, confidence, training fit and resource cost.
- Treat the 50/200 update behavior and optimizer scale as a declared nuisance
  variable, not a hidden architecture-specific tuning opportunity. Resolve whether
  matched fit or matched updates best answers the hypothesis before execution.
- Keep teacher preference and estimated mistake severity separate. Use the
  [metric-comparison owner](AB-LEARN-015-evaluation-metric-comparison.md) for any
  broader game-outcome validity study; teacher WDL saturation cannot certify ties.
- Retain frozen selections, source identities, failures, all checkpoints and
  independent verification. Record the result and competing explanations in the
  catalog without treating initialization seeds as independent datasets.

## Context and Trade-offs

In the 4k screen, 50/373 development labels (47 absolute actions) have no positive
training examples despite their actions being legal in 5–114 training positions.
All 90 source and destination squares have positive support. Thus joint-action
coverage can change independently of square coverage. The existing 16k snapshot
reduces missing development labels to 7/373, but also changes many other data
properties; its scaling gain cannot isolate this mechanism.

A controlled support intervention is more informative than another width sweep.
It still changes examples and may be hard to match perfectly. Positive support
can repair an output-frequency problem without learning transferable board
reasoning, so both supplied and still-withheld action groups are needed.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-12 | Codex | — | deferred | Capture the next explanatory comparison; matching, evaluation and resource protocol remain to be frozen. |

## Implementation Ledger

### 2026-09-12 — finding: action support as a separable hypothesis

- Evidence: [architecture report](../../reports/2026-09-12-architecture-surfaces.md)
  and its verified data/prediction evidence.
- Consequence: prioritize causal discrimination between coverage and representation
  before a broader architecture ranking or larger training campaign.
- Follow-up: test matching feasibility using training data, then freeze the study.
- Review: pending; no follow-up fits, data generation or sealed evaluation authorized here.
