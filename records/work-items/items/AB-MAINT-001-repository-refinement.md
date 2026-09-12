---
description: Implement the accepted repository audit repairs and bounded simplifications.
scope: backlog item
status: experimental
last_update: 2026-09-12
document_class: work_record
work_id: AB-MAINT-001
work_status: done
work_kind: build
added: 2026-09-12
tags: hygiene, frontend, domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-MAINT-001 — Repository refinement

## Intent

Resolve the evidence-backed documentation, correctness, abstraction and ergonomic
findings from the repository-wide audit at `3237739`. The user accepted all seven
recommended decisions on 2026-09-12. [AB-UI-004](AB-UI-004-bounded-collection-reads.md)
owns the collection-reader acceptance and measurements.

## Acceptance Criteria

- Invalid imports preserve the active session; validation and persistence finish
  before closing the import dialog, with visible pending/error states.
- Review drafts survive game changes during the browser session; concurrent saved
  revisions require an explicit conflict choice instead of discarding or overwriting text.
- Retire `/api/opponent` and its request/result models directly; migrate callers
  and tests to `/api/play/choose`. Normalize HTTP errors into the existing envelope.
- Resolve a requested player coherently once per operation, preserving resource
  mismatch checks between operations. Keep `QI_POLICY_CHECKPOINT` process-pinned;
  advertise its actual identity and a restart requirement after replacement.
- New saved benchmark snapshots retain their exact scoring evidence and verify
  against it after resumes. Older unreconstructable snapshots are visibly unverified;
  altered reconstructable ratings fail validation. Preserve locked-test reveal guards.
- Trace-job metadata updates cannot overwrite another owner's newer records.
- Preserve report scroll, use one board Tab stop with orientation-aware arrow keys,
  retain benchmark run/snapshot in URLs, fix mobile navigation, and poll only current
  unfinished benchmark results. Keep the existing visual design.
- Correct shipped-state documentation, training command routing, and unavailable
  navigation promises. Remove obsolete execution authorization from durable runbooks.
- Give authoring replacement terms an explicit portable contract in repo-kit, then
  selectively sync approved files. Preserve human glossary misconceptions.
- Check generated API freshness without modifying tracked files; add CI coverage
  for data/snapshot-dependent tests. Run repository and browser regression gates.

## Context and Trade-offs

The [snapshot decision](../../../docs/adr/0011-verifiable-rating-snapshots.md)
preserves historical meaning rather than rescoring old projections with expanded
evidence. Routine fixes retain referee, player, Training Data and trainer ownership.
Collection reads use SQL aggregates and pagination without a schema migration,
new indexes or cached counts. User-visible behavior stays within the accepted grill.

Preserve the dirty overnight-generation handoff, AB-DATA-008 and its three untracked
history records. The completed generation claim ledger remains until its reference
in that dirty owner can be reconciled. Raw experiments, catalog revision history,
historical measurements and deferred checkpoint-cache/supervision-constructor work
are outside this repair. No scientific run is authorized by documentation cleanup.

## Ownership

This table is the parallel claim ledger; writers do not stage or commit each other's work.

| Owner | Surfaces | State |
| --- | --- | --- |
| frontend worker | authored `web/src`, browser tests; excludes generated API; trace-owner regressions | complete |
| benchmark worker | `src/qi/benchmark`, tests and snapshot contract; upstream checker; collection measurements | complete |
| player worker | player resolution/runtime and guides; collection and saved-evidence regressions | complete |
| root | API/protocol retirement, integration, trace jobs, collection reader, tooling/CI, docs and closeout | complete |

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-12 | User/Codex | — | ready | User accepted all recommendations in the seven-question grill. |
| 2026-09-12 | Codex | ready | wip | Capture accepted scope and ownership before implementation. |
| 2026-09-12 | Codex | wip | done | All accepted refinements and integrated regression gates complete; protected generation files unchanged. |

## Implementation Ledger

- **Decision:** All seven recommendations are locked, including direct API retirement,
  AB-UI-004, keyboard/URL interactions, preserved drafts, upstream authoring repair,
  verifiable historical snapshots and convenience checkpoint process pinning.
  **Evidence:** User reply “all your rec” after the directly rendered grill.
  **Consequence:** Implement bounded slices with the ownership table above.
  **Follow-up:** Verify each slice and the integrated checkout before closeout.
  **Review:** ratified.

- **Verification:** Baseline at `3237739` passed 598 Python tests (one optional MPS skip),
  five browser lifecycle tests, 70 desktop/mobile E2E tests, 117 governed Markdown
  files, 25 catalog entries, type/style checks and production builds. OpenAPI matched
  live Python definitions. These checks do not remeasure historical scientific claims.
  **Evidence:** Audit outputs and `/tmp/qi-sweep-check-20260912.log` plus
  `/tmp/qi-sweep-e2e-20260912.log` from this local checkout.
  **Consequence:** New regressions must exercise the demonstrated gaps.
  **Follow-up:** Record post-change verification below.
  **Review:** verified.

- **Implementation:** Retired `/api/opponent` directly, generated the shared error
  contract, and consolidated each requested player operation into one resolution.
  Tests count one configuration parse and one hash per selected engine/network,
  retain mismatch rejection between operations, and keep saved-evidence validation
  independent of runtime dispatch. Convenience policy catalog metadata names the
  process-pinned checkpoint and explains replacement/restart requirements.
  **Evidence:** Player/binding tests and migrated CLI/HTTP/evaluation integration tests.
  **Consequence:** No compatibility route or duplicate resource-resolution chain.
  **Follow-up:** Checkpoint-cache bounds and supervision-constructor consolidation
  remain deferred as agreed.
  **Review:** verified.

- **Implementation:** Snapshot envelopes freeze validated manifest/attempt inputs,
  including mutable partial attempts, and rescore them when read. Legacy projections
  with unreconstructable inputs display unverified status. Trace owners reload
  current metadata under the lease; failed launch persistence holds that lease,
  and failed thread startup releases resources safely.
  **Evidence:** 40 benchmark/CLI tests and 31 trace/lab tests, including resumed
  history, altered projections, reveal guards and public two-owner regressions.
  **Consequence:** Historical projection consistency is verified; this is not an
  external authenticity signature. Snapshot evidence duplication is deliberate.
  **Follow-up:** Preserve the contract in ADR-0011 and `docs/benchmark.md`.
  **Review:** verified.

- **Implementation:** Imports validate and persist before dialog closure. Review
  drafts survive route/game changes until page reload; saved-review revisions and
  Web Locks guard cross-tab conflicts. Board arrows follow orientation with one Tab
  stop and visible focus. Benchmark run/history state stays in the URL; polling is
  limited to unfinished current results. Reports preserve scroll and mobile
  navigation wraps.
  **Evidence:** Complete desktop/mobile E2E suite, including import/storage failure,
  cross-tab overwrite races, URL/history/polling and keyboard regression cases.
  **Consequence:** Browser drafts remain tab-local; exports retain portability.
  **Follow-up:** Implemented behavior is owned by `docs/interface.md`.
  **Review:** verified.

- **Implementation:** Reconciled current trainer/data/project guides, removed
  unavailable Human View promises and spent ledger placeholders, and routed
  execution authority out of the reusable generation guide. Portable replacement
  checking now reads only `Replaced terms`; `_Avoid_` and aliases retain human meaning.
  **Evidence:** repo-kit commit `c60fb19`; both checkers, authoring rules and the
  glossary-format reference match qi byte-for-byte. Domain-modeling received only
  the related step/version patch (kit 1.4.3; qi 1.4.2). Copier baseline is unchanged.
  **Consequence:** No TERM001 findings from misconceptions; 16 prose advisories remain.
  **Follow-up:** Generation claim-ledger deletion remains deferred while its
  incoming reference belongs to protected dirty work.
  **Review:** verified.

- **Verification:** Full changed checkout: `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache
  make check` passed 670 Python tests (one optional MPS skip), five lifecycle tests,
  Ruff, TypeScript/format checks, builds, 119 governed Markdown files, 25 catalog
  entries and generated API freshness. The complete desktop/mobile E2E lane passed
  86 tests. `make test-data` passed 36 tests with installed data/learning extras.
  **Evidence:** `/tmp/qi-refinement-check.log`, `/tmp/qi-refinement-e2e.log`,
  `/tmp/qi-refinement-data.log`. Controlled stale-schema and stale-TypeScript copies
  were each rejected without modifying either copy or tracked contracts.
  Repo-kit passed nine tests and Ruff; two optional networked Copier tests were
  skipped because delivery configuration did not change. No CI run is claimed.
  **Consequence:** The integrated checkout passes; SQL memory/latency tradeoffs are
  retained separately in AB-UI-004, without promoting them to production scaling.
  **Follow-up:** Preserve the five pre-existing dirty/untracked generation files;
  their hashes still match the audit baseline. No scientific run or push was performed.
  **Review:** verified.
