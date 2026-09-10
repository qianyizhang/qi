---
description: Plan a bounded teacher-quality audit before changing the learning treatment.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-LEARN-009
work_status: deferred
work_kind: research
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-LEARN-009 — Teacher-quality audit

## Intent

Determine whether teacher-label quality merits the next controlled change under
the [policy-generalization campaign](../../campaigns/policy-generalization.md).

## Acceptance Criteria

- Freeze a bounded position set, existing teacher settings and a stronger
  reference budget; define selection, denominators and stop conditions first.
- Retain both teachers' raw evidence and report agreement/disagreements with
  score semantics and uncertainty limits. A stronger reference is not ground truth.
- Recommend whether a controlled label-quality comparison is warranted. Keep
  source coverage, phase distribution, representation and training recipe fixed
  if advancing that comparison; capture its precise execution slice separately.
- Keep imitation agreement distinct from playing strength and avoid attributing
  existing generalization limits to label quality without evidence.

## Context and Trade-offs

The campaign already names teacher quality, curriculum, representation and match
strength as open questions. This item preserves one bounded candidate frontier;
it does not schedule runs or combine all those variables into one study.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture the larger teacher-quality review proposal for later selection. |

## Implementation Ledger

No implementation events yet.
