---
description: Bound collection-page work while preserving cohort and snapshot semantics.
scope: backlog item
status: experimental
last_update: 2026-09-12
document_class: work_record
work_id: AB-UI-004
work_status: done
work_kind: build
added: 2026-09-11
tags: frontend, training-data
depends_on: AB-UI-003
residual_of: none
residual_items: none
---

# AB-UI-004 — Bound collection reads

## Intent

Make page reads scale with returned games rather than constructing every game
projection for each filter or page change. The [collection reader](../../../src/qi/collection_view.py)
at `3237739` loaded every game, filtered/sorted in Python, and scanned the full
list again for each run's statistics. The implemented SQL reader retains the
same response while materializing only the requested page.

## Acceptance Criteria

- Keep the [review contract](../../../docs/interface.md#generated-game-review):
  one read-only SQLite snapshot, finite query deadline, explicit denominators,
  continuation ownership, and deterministic ordering.
- Put cohort filtering, pagination and aggregate queries behind one reader owner;
  materialize only the requested game page. Retain existing HTTP shapes.
- Compare all filters, sorts, overall/run/cohort counts, and phase totals against
  fixed fixtures containing rejected, unfinished and continued games.
- Record time and peak memory on a fixed input before/after. Do not introduce
  cached counts without an explicit freshness contract or change training eligibility.

## Context and Trade-offs

Start with collection-page reads. Replay, raw-analysis verification and the separate
whole-collection quality audit have different obligations and need not move together.
Choose the SQL/query decomposition before implementation; a schema migration or new
indexes require a separate decision because this UI does not own collection writes.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | deferred | Survey found full-list materialization beneath a paginated API; propose a separate refactor after branch integration. |
| 2026-09-12 | User/Codex | deferred | wip | Accepted SQL filtering, pagination and aggregates in the AB-MAINT-001 grill; no schema, indexes or cached counts. |
| 2026-09-12 | Codex | wip | done | Fixed-cohort parity, bounded materialization, read-only checks and before/after measurements complete. |

## Implementation Ledger

- **Decision:** Keep one SQL projection for cohort predicates, overall/run/cohort
  aggregates and deterministic page ordering inside the existing read transaction
  and ten-second deadline. SQLite still scans the collection for exact aggregates.
  **Evidence:** `src/qi/collection_view.py`; no collection schema or writer changes.
  **Consequence:** Python creates only returned game objects; aggregate work is not
  constant-time. Replay and the separate quality audit retain their own paths.
  **Follow-up:** Revisit query decomposition if representative live workloads miss
  the deadline; do not introduce caching without a freshness decision.
  **Review:** ratified.

- **Verification:** All 48 collection-reader tests pass. Forty fixed-cohort cases
  also pass against the reader from `3237739`, covering every filter/sort, accepted
  denominators, both rejection forms, continuation/run ownership, phase totals,
  empty cohorts, length buckets, Unicode lowercase and literal substring searches.
  **Evidence:** `src/qi/test_collection_view.py`; read-only and live-writer regressions.
  **Consequence:** Existing HTTP meanings and page totals are preserved, including
  an empty page beyond the cohort's final row.
  **Follow-up:** Retain these contract regressions when changing query structure.
  **Review:** verified.

### Fixed-input resource comparison

[Raw observations](../../reports/collection-reader-refinement-20260912.json) retain
all 48 measurements, queries, source hashes and environment details. The local
fixture and executed script/source copies are retained under
`artifacts/maintenance/collection-reader-20260912/`. Original source is also
recoverable from Git `3237739:src/qi/collection_view.py`.

The 15,032,320-byte fixture repeats the five-row review fixture 2,000 times with
unique attempt/logical keys: 4,000 accepted, 2,000 rejected, 2,000 failed and 2,000
running metadata rows across two runs. Occurrences/analyses are not multiplied;
this measures indexed summaries, not 10,000 independently generated games.
Integrity/foreign-key checks passed. The fixed SQLite SHA-256 before and after was
`a594934428cc2c2d27c1ff9244ee3a4aa01433c337b3b85ab1ce79cd9a9bcfb0`.

Fresh subprocesses alternate old/new order for five uninstrumented timing samples
and three separate allocation samples per query/version. Timings cover
`collection_page` only; `tracemalloc` covers Python allocations; macOS `ru_maxrss`
includes imports and SQLite. Python 3.12.13, SQLite 3.50.4, macOS ARM64, warm local
filesystem. Full response JSON matched except the observation timestamp.

| Query (30 returned games) | Median old → new time | Median Python peak old → new | Median process peak RSS old → new |
| --- | --- | --- | --- |
| Newest, all 10,000 attempts | 86.06 → 131.91 ms | 35.742 → 0.137 MiB | 85.50 → 58.83 MiB |
| Accepted validation, longest, offset 30 | 77.99 → 109.08 ms | 35.266 → 0.139 MiB | 85.00 → 57.30 MiB |
| Opening shortfall, descending shortfall | 80.73 → 137.74 ms | 35.326 → 0.140 MiB | 85.05 → 58.13 MiB |

All measured requests materialized 10,000 → 30 game objects. The result supports
lower memory use with increased latency on this fixture. It establishes neither
a speedup nor production/cold-cache/concurrent-reader scaling.
