---
description: Replace full game-payload rewriting with guarded incremental SQLite updates and measure generation.
scope: collection append performance and integrity
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-007
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, storage, performance
depends_on: AB-ARCH-006
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-007 — Incremental collection append

## Intent

Implement the authorized next slice from [AB-ARCH-006](AB-ARCH-006-compact-native-observations.md):
let SQLite update only move history and actor counters, avoiding full growing
payload decoding and serialization on every append. Existing decisions settle
the schema, exact history/identity, corruption rejection and every-move durability.
No material owner choice blocks the bounded experiment.

## Acceptance Criteria

- Keep schema version 1 and public collection formats; use no migration or new
  tables. Both Python and native callers use the same write path.
- Full payload validation remains mandatory for uncached or changed data. One
  private bounded cache can reuse validation only on exact persisted payload and
  indexed-identity equality; mutable caller objects cannot change cached state.
- Update only history and counters, guarded by the observed persisted payload,
  identity and running lifecycle. Retain family/split and exact-prefix checks.
- A cache update happens after successful commit. Aborts, commit failures, stale
  reads, direct SQL changes, same-prefix accounting, switching games and reopening
  remain correct. WAL/FULL and every-move commits stay unchanged.
- Exact differential outputs and independent replay/SQLite verification pass;
  affected store/export/generation consumers and the full application gate pass.
- Freeze controls and retain configs, sources, raw attempts and assessed findings.

## Context and Trade-offs

The previous compact-native comparison measured 1.102x Python throughput, below
its 1.2x backend adoption rule. Median native referee time was 0.333 s versus
1.395 s for collection append. Its profile found repeated payload loading and
serialization alongside durable commit costs. This slice tests the former;
reducing commit frequency would change recovery semantics and is outside scope.

The cache stores only one validated game state and exact JSONB bytes, not a new
semantic identity. Each append reads current bytes and identity columns from
SQLite. Any change invalidates reuse and causes full validation. The guarded SQL
write rejects a row changed after observation. This preserves rejection of
well-formed JSONB containing invalid application data without validating a large
unchanged payload on every move. JSONB updates still copy/write database data;
this is not a zero-copy or reduced-durability claim.

### Predeclared comparison

- Archive the entire `c44e08d` runtime and matching native binary before editing.
  Freeze current source, lock and binary before confirmation.
- Reuse the 64 random-actor games, seed 29, 300-ply cap, phase quotas and legal
  fixture labels. Three alternating four-arm rounds: old Python, old compact
  native, new Python and new compact native. Assert historical runtime imports.
- Two alternating paired real-teacher rounds retain four plausible-actor games,
  32 plies, pinned Pikafish/NNUE, one thread and 1,000 nodes.
- Fresh serial processes/collections, cleared reference caches, no concurrent
  tests/builds during timing; at most 180 seconds per cell and 20 minutes per
  comparison. Development parity precedes confirmation. Retain failed attempts.
- Require exact trajectories, actor decisions, outcomes, occurrences and semantic
  supervision; independently replay and validate SQLite after timing. Remove
  only existing runtime/provenance fields from comparison.
- Record wall/worker CPU, peak RSS, plies/s, selections/s and existing phase
  counters. Separate post-hoc profiling is diagnostic, not primary timing.
- Retain the optimization only with exact correctness, a median within-backend
  throughput improvement of at least 1.1x in one backend and no greater than 5%
  regression in the other. Continue reporting native/new-Python against the
  existing 1.2x/all-round-win backend advancement rule; no automatic default change.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User authorized the proposed incremental-write experiment after an open-decision check. |
| 2026-09-21 | GPT-6 | wip | done | Guarded updates, exact comparisons, integrity/recovery tests and full application gates pass; retention criterion met. |

## Implementation Ledger

- **2026-09-21 — decision:** Preserve current storage and recovery semantics;
  exact stored bytes and indexed identity govern reuse, and commit success
  governs cache advancement. Frozen baseline retained under
  `artifacts/incremental-append-20260921/baseline-c44e08d`. **Review:** not-required.
- **2026-09-21 — finding:** All 12 controlled cells match 64 trajectories,
  17,169 plies and 417 labels. Median paired throughput gains are 1.136x for
  Python and 1.104x for native, with improvements in every round. Retain the
  optimization under the predeclared 1.1x rule. Current native/Python is 1.093x,
  below the separate 1.2x advancement threshold. Four teacher cells match
  128 plies/20 selections; their 1.011x ratio is only a short integration pilot.
  See the [report](../../reports/2026-09-21-incremental-collection-append.md) and
  [compact results](../../../data/evaluation/incremental-append-20260921.json).
  **Review:** not-required.
- **2026-09-21 — verification:** All 57 focused store/generation/export/training
  tests pass. `make check` passes 803 Python tests (one skipped), five browser
  tests and static/build gates. True commit failure, stale observation, direct
  SQL corruption, caller mutation, retry and reopening preserve integrity.
  Both 304-file manifests match frozen and executed sources; independent
  post-timing replay and SQLite checks pass. No timed attempt failed. The
  pre-existing AB-EVAL-005 source-hash discrepancy remains unrelated and unchanged.
  **Review:** not-required.
- **2026-09-21 — handoff:** The Training Data guide owns the adopted write
  behavior. Native append-phase time falls from 1.352 to 1.086 s; the separate
  profile still attributes 0.732 s to SQLite transaction exits. Further work
  needs a representative target workload and a fresh profile; changing commit
  frequency requires a new recovery-contract decision. Native stays opt-in;
  broader migration remains routed through [AB-ARCH-001](AB-ARCH-001-modular-runtime.md).
  **Review:** not-required.


```experiment
{
  "schema_version": 1,
  "id": "incremental-append-20260921",
  "title": "Guarded incremental collection writes",
  "question": "Can incremental SQLite writes reduce full generation cost while preserving per-move durability and payload integrity?",
  "kind": "performance",
  "topics": [
    "storage",
    "generation",
    "SQLite",
    "native",
    "serialization"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "AB-ARCH-007: three alternating four-arm rounds of the fixed 64-game workload against complete c44e08d controls; two paired pinned real-teacher pilot rounds.",
  "limitations": "",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "compact-native-20260921",
      "relationship": "extends",
      "contribution": "Targets repeated collection payload work after native observation costs were reduced."
    }
  ],
  "novelty": "Tests guarded incremental JSONB updates with exact persisted-byte validation reuse and unchanged commit frequency."
}
```


```experiment
{
  "schema_version": 1,
  "id": "incremental-append-20260921",
  "title": "Guarded incremental collection writes",
  "question": "Can incremental SQLite writes reduce full generation cost while preserving per-move durability and payload integrity?",
  "kind": "performance",
  "topics": [
    "storage",
    "generation",
    "SQLite",
    "native",
    "serialization"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "All 12 controlled cells preserve 64 trajectories, 17,169 plies and 417 labels. Median paired throughput gains are 1.136x for Python and 1.104x for native, winning every within-backend round. Native/current-Python is 1.093x; four teacher cells match 128 plies and 20 selections with a 1.011x ratio.",
  "conditions": "AB-ARCH-007: three alternating four-arm rounds of the fixed 64-game workload against complete c44e08d controls; two paired pinned real-teacher pilot rounds.",
  "limitations": "One fixed workload on local macOS ARM64; repeated games are not independent workload diversity. Fixture labels establish equivalence, not quality. The short teacher pilot compares current backends, not historical write paths. JSONB still copies/writes full growing data and every move still commits. Profile categories overlap; no per-step native claim.",
  "decision": "Retain guarded incremental append: exact parity and the predeclared 1.1x within-backend retention criterion pass without regressions. Preserve schema v1 and every-move WAL/FULL commits. Python remains default; native misses the separate 1.2x advancement threshold.",
  "revisit": "Profile a representative target workload before another optimization. Reassess native adoption only under its existing advancement rule; changing commit frequency needs an explicit recovery-contract decision.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-incremental-collection-append.md",
      "role": "report",
      "sha256": "5e7eb63379276fd19d02819fafc2fbac29ba70366d769adb67d8353b2368e128"
    },
    {
      "path": "data/evaluation/incremental-append-20260921.json",
      "role": "results",
      "sha256": "de731c5a8cacccd75ea2fbf210247a918b3e55800c063ecc6d100a7e5cf9d4aa"
    },
    {
      "path": "artifacts/incremental-append-20260921/inputs/controlled.json",
      "role": "config",
      "sha256": "fb53e4dc3242178f6cdb3bcb41e3acc5d7d3fa19b68759081b9c73f04bcd17af"
    },
    {
      "path": "artifacts/incremental-append-20260921/inputs/teacher.json",
      "role": "config",
      "sha256": "e4ab3917652b2ecb44fc1b5737c2bc36d657c13d20c19835879967d8319bd18d"
    },
    {
      "path": "artifacts/incremental-append-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "bdcab02fe1180f5d7b5a118702048c6b3720a0bd4023c8c50035aa2e04b49c03"
    },
    {
      "path": "artifacts/incremental-append-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "16f30a620a0170f8742bd1e97059769ba81f4dcadd04a9fc173bb29bbc034414"
    },
    {
      "path": "artifacts/incremental-append-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "bff6f5144d63636cb197d0f683ab5bdf1c9c37f14a0c837acdb327e4ce33b871"
    },
    {
      "path": "artifacts/incremental-append-20260921/teacher-01/manifest.json",
      "role": "source",
      "sha256": "9adfdc431bcdf34c292b443cfaa0f155c364dd457ded49c1e065db7749e7095c"
    },
    {
      "path": "artifacts/incremental-append-20260921/confirmation-01/frozen/scripts/benchmark_incremental_append.py",
      "role": "source",
      "sha256": "2a51fb06213fc7fede28ea9cc7929b89931b26b6aaaaf0f6fcbe458d457d83cc"
    },
    {
      "path": "artifacts/incremental-append-20260921/confirmation-01/frozen/src/qi/training_data/store.py",
      "role": "source",
      "sha256": "abe674696010208517be9329ae1b7c58df3a0df3207fd67ca0501b41721ca347"
    },
    {
      "path": "artifacts/incremental-append-20260921/confirmation-01/frozen/src/qi/training_data/test_store.py",
      "role": "source",
      "sha256": "e8ad8eb623d1d361f1020afd82b8a197511e4ef31803a40ddff93b9f7fba51dd"
    },
    {
      "path": "artifacts/incremental-append-20260921/development-01/summary.json",
      "role": "results",
      "sha256": "a25b6a1cdf212f34f038077e94bbf6daf324ff44cde43043283ccbc77138ae99"
    },
    {
      "path": "artifacts/incremental-append-20260921/profile-01/result.json",
      "role": "results",
      "sha256": "83111836f21e88ae7a7e5e2fc7add39a41810ccd99208df8f1481200255af011"
    },
    {
      "path": "artifacts/incremental-append-20260921/profile-01/diagnostic.prof",
      "role": "run",
      "sha256": "d521a82eb0fbb5c0fef8912af4d609ff06637d7cbcc240cd46b1ea5d4caf41fd"
    },
    {
      "path": "artifacts/incremental-append-20260921/focused-check.log",
      "role": "run",
      "sha256": "e2343bdf5ac57524e9a7ddfb19343f54a3d4624b49da59c7fb71cac818a57577"
    },
    {
      "path": "artifacts/incremental-append-20260921/make-check.log",
      "role": "run",
      "sha256": "a9ed8d7a272a9b9de4dd00ee66e70926d2fea3892cb9a565a06f099f5922ed83"
    }
  ],
  "prior_work": [
    {
      "id": "compact-native-20260921",
      "relationship": "extends",
      "contribution": "Targets repeated collection payload work after native observation costs were reduced."
    }
  ],
  "novelty": "Tests guarded incremental JSONB updates with exact persisted-byte validation reuse and unchanged commit frequency."
}
```
