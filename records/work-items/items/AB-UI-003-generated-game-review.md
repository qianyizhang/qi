---
description: Data workspace for generated-game quality, coverage, replay and browser review.
scope: backlog item
status: stable
last_update: 2026-09-11
document_class: work_record
work_id: AB-UI-003
work_status: done
work_kind: build
added: 2026-09-11
tags: frontend, training-data
depends_on: AB-DATA-008, AB-UI-002
residual_of: none
residual_items: none
---

# AB-UI-003 — Generated game review

## Intent

Help the user understand recent generated batches and curate examples, prioritizing
data quality and coverage. Reuse collection evidence, the referee and the shared
lab. The [interface guide](../../../docs/interface.md#generated-game-review) owns
implemented behavior; collection and Training Data remain source/selection owners.

## Acceptance Criteria

- Discover local collections safely; inspect current evidence while a writer runs.
- Filter/paginate games and compare run, policy, split, outcome and phase coverage
  with explicit denominators and continuation/rejection semantics.
- Audit selected learner-input repetition and cross-split overlap; link examples
  and expose successful analysis coverage without claiming training eligibility.
- Replay recorded games, navigate selected positions, compare teacher evidence
  and preserve score perspective/bounds and first-success resolution.
- Save browser review suggestions/notes with source identities and export JSON.
- Verify Python contracts, browser workflows, narrow-screen usability and repo gates.

## Context and Trade-offs

An active batch fingerprints Python source. Initial development uses an isolated
checkout to preserve that run's provenance. There is no collection writer, training
launcher, schema migration or exclusion-policy change in this slice. Browser review
is intentionally independent of frozen dataset composition. Quality audit timestamps
and cohort timestamps are distinct; refreshing is explicit.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | wip | User requested implementation and prioritized data quality/coverage. |
| 2026-09-11 | Codex | wip | done | Read-only Data workspace verified against fixtures and the live collection. |

## Implementation Ledger

- **Decision:** Extend the existing shared lab with Python-owned read projections
  and a browser-owned review shortlist. No cross-context authority changes.
  **Evidence:** [interface](../../../docs/interface.md#generated-game-review),
  [reader](../../../src/qi/collection_view.py).
  **Consequence:** Review tags cannot silently become training exclusions.
  **Follow-up:** None for this accepted slice.
  **Review:** not-required.

- **Verification:** `make check` passed: 568 Python tests, one optional skip,
  five request-lifecycle tests, lint/docs/catalog and production builds. All 52
  desktop/mobile browser cases passed, including eight collection cases. The final
  teacher-overlay refinement was rechecked through the eight collection cases.
  Live collection reads and screenshots verified the quality audit, phase gaps,
  selected-position navigation and narrow-screen layout.
  **Evidence:** [reader tests](../../../src/qi/test_collection_view.py),
  [browser cases](../../../web/e2e/data.spec.ts).
  **Consequence:** UI suggestions remain independent of source evidence and frozen
  selection. No generation or training settings changed.
  **Follow-up:** Integration completed below after generator exit and final accounting.
  **Review:** not-required.

- **Integration:** Fast-forwarded `main` through `615a808` and `4fca9fa` after the
  generation ledger reported paused/no further dispatch and process inspection
  confirmed no generator. Data review and the generation walkthrough are integrated.
  **Verification:** `make check` passed with 573 Python tests, one optional MPS skip
  and five request-lifecycle tests; all 68 desktop/mobile browser cases passed after
  settings-cancellation fixes and deferred Data-page loading. Existing dependency
  deprecation and bundler directive warnings remain non-failing.
  **Consequence:** The preview now runs from `main` on port 18766 with the same
  collection source; ignored evidence was checked or preserved before worktree removal.
  **Follow-up:** [AB-UI-004](AB-UI-004-bounded-collection-reads.md) proposes bounded
  collection-page reads; no reader or training contract changed during integration.
  **Review:** not-required.
