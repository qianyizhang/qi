---
description: Decide and test whether Pikafish move-value estimates provide more useful model evaluation than top-1 agreement.
scope: backlog item
status: experimental
last_update: 2026-09-12
document_class: work_record
work_id: AB-LEARN-015
work_status: deferred
work_kind: research
added: 2026-09-12
tags: domain
depends_on: AB-LEARN-012, AB-LEARN-013, AB-LEARN-014
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-12"
---

# AB-LEARN-015 — Evaluation metric comparison

## Intent

Compare teacher top-1 agreement with Pikafish's assessment of the move a saved
model selects. Resolve whether the two metrics give different model rankings
and training-recipe conclusions, and what evidence would justify calling one
more effective. The user requested a decision interview and next-session
handoff; the protocol and execution allowance are not yet locked.

## Acceptance Criteria

- Settle the purpose, data boundaries, resource ceiling, model cohort, reference
  procedure and decision rule before implementation or scoring. Register a new
  planned experiment after those choices are fixed.
- Preserve the original outcomes of AB-LEARN-009 and AB-LEARN-012 through 014.
  A new metric assessment must not replace their predeclared primary criteria.
- Retain model/input/teacher identities, raw assessments, missing-evidence
  counts, paired comparisons, search stability, costs and failed attempts.
  Treat repeated controls and shared training/evaluation inputs explicitly.
- Distinguish metric correlation, move-error severity and predictive validity
  against game outcomes. Claims must match whichever scope the user selects;
  a higher engine budget or correlation between two teacher-based metrics does
  not alone establish playing strength.
- Independently verify the selected protocol's evidence and record its finding,
  limitations, decision and revisit trigger in this owner and the catalog.

## Context and Trade-offs

[Teacher-quality comparison](AB-LEARN-009-teacher-quality.md) already found
improved supporting expected-score loss in all three training blocks while
top-1 improvements were mixed. Its original conclusion remains inconclusive.
This proposal evaluates the metrics themselves across the broader saved cohort;
it does not repeat the teacher-label treatment.

The [session closeout](../../reports/generated-data-session-closeout-20260912.md)
verifies 89 retained checkpoints, including 84 comparison fits with 75 distinct
weight states. All use 373 inspected development positions. Nine comparison
controls repeat other models exactly. These are correlated model observations,
not 75 independent dataset experiments. All 3900 sealed inputs remain unscored.

The existing [candidate scorer](../../../src/qi/learning/teacher_quality_scores.py)
supports complete, same-depth, all-legal MultiPV/WDL estimates and explicit
unknown results. The [benchmark contract](../../../docs/benchmark.md) provides
paired game outcomes if that validation scope is selected. Neither capability
removes the need for calibration and a frozen comparison.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-12 | Codex | — | deferred | User requested protocol grilling and a next-session handoff; no scoring or fitting started. |

## Implementation Ledger

### 2026-09-12 — handoff: protocol decision interview

- Evidence: [decision packet](../../reports/session-handoff-metric-comparison-20260912.md)
  records the open interview frontier and live code/evidence pointers.
- Consequence: remain in decision mode until material protocol choices settle;
  recommendations in the pending interview are not accepted decisions.
- Follow-up: complete the interview, freeze the selected comparison and record
  the next session's authorized transitions.
- Review: pending; purpose, evaluation-pool policy and runtime allowance are open.
