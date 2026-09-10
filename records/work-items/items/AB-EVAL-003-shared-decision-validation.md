---
description: Share existing decision-evidence invariants across live play and saved evaluation paths.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-EVAL-003
work_status: deferred
work_kind: build
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-EVAL-003 — Shared decision-evidence validation

## Intent

Give live player decisions, arena evidence and search-experiment evidence the same
definition of valid move and diagnostic accounting. Selected for the next detailed
discussion; implementation is unscheduled.

## Acceptance Criteria

- Extract pure shared checks for legality, common budgets, MCTS diagnostics and
  search counters; call them from all three existing validation paths.
- Keep replay order, expected identities, protocol restrictions, pair completion
  and outcomes with their existing owners.
- Reject inconsistent saved diagnostics without executing players. Cover valid
  round trips and corrupted simulation/root-visit totals and search counters.
- Preserve player behavior, charged-node budget semantics and valid artifact
  meanings; run focused tests and `make check` when implemented.

## Context and Trade-offs

At `47da444`, incrementing a saved MCTS simulation count passed
`EvalRun.validate_match` and summarization, while search-experiment verification
rejected it. This establishes an internal-accounting gap, not an incorrect referee
outcome or proof that an engine actually performed the recorded work.

Owners: [Players](../../../src/qi/players/README.md),
[evaluation](../../../docs/evaluation.md), [search evidence](../../../src/qi/experiments/evidence.py).
Discuss the small extraction and compatibility details before implementation;
new event storage, a general validation framework and LLM attempt formats are outside scope.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | User endorsed the refactor direction and requested general backlogs before selecting an item for detailed discussion. |

## Implementation Ledger

### 2026-09-10 — decision: next discussion and bounded scope

- Evidence: user accepted the four-item core backlog and this item as the next discussion.
- Consequence: scope the shared existing invariants while preserving artifact formats
  and player behavior. Implementation remains unscheduled.
- Follow-up: settle extraction ownership and compatibility details in the item-level interview.
- Review: ratified; user confirmed the proposed direction.
