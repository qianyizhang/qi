---
description: Plan a bounded untuned LLM baseline and frozen-data SFT comparison.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-LLM-001
work_status: deferred
work_kind: research
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-LLM-001 — LLM baseline and SFT comparison

## Intent

Plan one pretrained model's untuned move-selection baseline, then compare it with
SFT on frozen data. Planned and unscheduled; the [Campaign](../../campaigns/llm-move-selection.md)
holds the evolving question and learning across stages.

## Acceptance Criteria

- Before execution, select one model and lock representation, legal-move ordering,
  coordinate-only output, decoding, inference/training budgets and evaluation data.
- Establish feasibility and retain raw attempts, parsing/legality outcomes, usage,
  timing and model/prompt identities for the untuned baseline.
- Compare base and SFT under the same protocol, with frozen training data and
  untouched evaluation inputs; retain failures in metric denominators.
- Report formatting, legality and teacher agreement, plus a bounded stronger-reference
  audit of disagreements with explicit score perspective and mate semantics.
- Record partial work, findings and the next decision. Introduce independent
  participant bindings when extending the comparison to paired games.

## Context and Trade-offs

Follow the [experiment method](../../../docs/experiments.md). Model, hardware,
budget and exact protocol remain open for a later discussion. This record does
not schedule training or require value learning, PUCT or self-play first.
Reasoning/tool-use comparisons and RL remain outside this bounded comparison.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | User requested a short backlog preserving the baseline/SFT direction as planned work. |

## Implementation Ledger

No implementation events yet.
