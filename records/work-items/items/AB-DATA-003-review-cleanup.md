---
description: Review Training Data invariants independently of the original happy-path pilot and remove redundant shims.
scope: backlog item
status: stable
last_update: 2026-09-11
document_class: work_record
work_id: AB-DATA-003
work_status: done
work_kind: build
added: 2026-09-09
tags: hygiene
depends_on: AB-DATA-002
residual_of: none
residual_items: none
---

# AB-DATA-003 — Review and cleanup

## Intent

Review the completed Training Data slice from its contracts and adverse cases,
fix defects, and remove redundant compatibility surfaces. Preserve supported
artifact readers and keep the concurrent source-coverage experiment separate.

## Acceptance Criteria

- Reproduce review findings before fixing them, with regression coverage.
- Keep trajectory randomness independent of sampling/count controls; make the
  experimental generator version change explicit.
- Preserve checkpoint snapshots and count each observation/theme correctly.
- Remove forwarding imports and duplicate training orchestration; migrate callers
  and document replacements without deleting supported v1 data artifacts.
- Pass scoped and repository checks, record results, and commit the reviewed work.

## Context and Trade-offs

The v1 dataset format and flag-based learning-curve commands are still used by
saved experiments. They remain supported. The import-only `qi.learning.data`
module and duplicate `qi data train` command have no independent behavior worth
maintaining. Their callers move to Training Data's v1 reader and the learning CLI.
Old continuation libraries remain readable; new generation requires the explicit
`continuations-v2` random-stream contract.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User requested independent review, fixes, shim cleanup and a commit. |
| 2026-09-09 | Codex | wip | done | Regression fixes, caller migration, preserved artifact checks, full checkout and isolated staged-tree checks passed. |

## Implementation Ledger

Review findings reproduced and fixes implemented with regression tests.

### Review Findings and Fixes

| Finding | Reproduction and fix |
| --- | --- |
| Sampling settings rewrote the game | Changing sample count/window or number of games changed the random actor's moves. Separate actor/sampler streams in `continuations-v2`; source identity includes actor configuration. Old libraries are read-only inputs to reassembly, with no silent v1 regeneration. |
| Checkpoint receipts mutated later | Repeated teacher continuations merged source IDs into examples already handed to the checkpoint callback, making earlier snapshots reference future sources. Return independent snapshots and avoid constructing intermediate libraries when no checkpoint callback needs them. |
| Alternate histories bypassed quota priority | Two replay histories with the same observation could enter different buckets and let a later bucket borrow capacity. Resolve first-bucket ownership over all histories of each observation before filling quotas. |
| Duplicate themes inflated slice counts | Repeating one theme duplicated positions in its diagnostic slice. Reject duplicate/blank themes at the starting-position boundary. |
| Training commands drifted | `qi data train` did not signal partial fits as failure; `qi learn train` referenced a saved report without writing one and only loaded v1 data. Consolidate on `qi learn train`, use the prepared-data loader, save config/report, and preserve partial-fit nonzero exits. |

The first four regression tests failed against the reviewed implementation before
fixes. Further checks cover v1 recipe admission, frozen-data CLI fits, saved
partial reports, and refusal to overwrite existing report artifacts.

## Cleanup

- Removed the import-only `src/qi/learning/data.py`; moved the supported v1 format
  and its tests to `src/qi/training_data/v1.py` and its colocated test module.
- Moved prepared-data loading out of optimization config into Training Data.
- Removed `qi data train`; retained one training CLI and the configured runner.
- Moved shared training-data fixtures into root `conftest.py`, eliminating imports
  between test modules and their unused-import/redefinition suppressions.
- Updated the module/model guides and optional learning-test lane.

## Validation

- `make check` passed on the full checkout, covering Python, browser, lint,
  documentation, type, and production-build checks. A separate isolated export
  passed the Markdown, Ruff, and Python checks, confirming that this change did
  not depend on concurrent source-coverage work.
- Both saved real-engine pilot datasets loaded successfully with their unchanged
  manifest fingerprints, including phase-filtered pilot
  `91c16401c83bff4fd9ea323fc23f91a8ee55e700fb5f377da33268f1ab43ab31`.
  The relocated v1 implementation is byte-for-byte identical to its prior file.
- CPU integration exercises the unified CLI, frozen-data training, report/config
  persistence and checkpoint reload. No optimizer or GPU computation changed;
  no new strength or acceleration claims are made.
- Two existing FastAPI/Starlette deprecation warnings remain; fixing dependency
  APIs is outside this data-boundary review.
