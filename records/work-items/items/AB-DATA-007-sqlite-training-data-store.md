---
description: Build incremental generation persistence, reusable analyses and frozen Parquet training snapshots.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-DATA-007
work_status: done
work_kind: build
added: 2026-09-10
tags: domain, MVP
depends_on: none
residual_of: none
residual_items: none
produced_by: "domain-modeling@1.4.1 · agent=GPT-6 · effort=unspecified · 2026-09-10"
---

# AB-DATA-007 — SQLite Training Data collection

## Intent

Implement [ADR-0008](../../../docs/adr/0008-sqlite-collection-parquet-snapshots.md)
so generation can persist incrementally, reopen without duplicating committed
work, analyze retained occurrences under another specification, and freeze a
portable training snapshot. Implemented contracts live in the
[Training Data guide](../../../src/qi/training_data/README.md#incremental-collection-and-parquet-snapshots);
this completed record retains scope, decisions and verification evidence.

## Acceptance Criteria

- Five-table SQLite store with enforced foreign keys, uniqueness, status checks,
  schema migrations and validated, versioned JSONB payloads. Runtime capability
  checks fail clearly if required SQLite features are absent.
- Generation writes new records incrementally with bounded working memory;
  no per-game full-collection reconstruction, validation or rewrite.
- Completed games and their prefixes survive interruption. Recovery never
  rewrites an analyzed prefix or mistakes unfinished work for successful work.
- Preserve unlabeled occurrences and failed analysis attempts; a second teacher
  specification can analyze an existing occurrence without regenerating a game.
- Required indexed board identity supports distinct-position selection and
  reporting; exact replay identity remains separate and verified.
- SQL-selected snapshots enforce source-family, exact-trajectory and model-input
  isolation, explicit duplicate/label selection, quotas and held-out exclusions.
- Freeze exact successful analyses into typed Parquet with a self-contained
  verification/source bundle, a manifest, deterministic order and file hashes.
  Subsequent collection changes do not alter an existing snapshot.
- Backend queries use the store directly. A bounded batch reader consumes the
  snapshot without rebuilding a giant JSON/Pydantic dataset or full-data tensors.
  Completion includes tensor-preparation integration verification; production
  optimizer integration and update/epoch changes are separate follow-up work.
- Existing JSON artifacts remain readable through explicit compatibility paths;
  conversion preserves semantics and identifies unsupported target/format cases.
- Focused tests cover the counterexamples below; run repository checks and a
  representative persistence/read benchmark before claims of scale readiness.

## Context and Trade-offs

The accepted five-table design is implemented under Training Data:

| Concern | Implementation authority |
| --- | --- |
| Schema, canonical identities, writer ownership and recovery | [store.py](../../../src/qi/training_data/store.py) |
| Incremental preparation and reanalysis | [collection_generation.py](../../../src/qi/training_data/collection_generation.py) |
| Recipe compilation, frozen evidence, verification and bounded reads | [snapshots.py](../../../src/qi/training_data/snapshots.py) |
| Partial candidate evidence and explicit legacy conversions | [candidate_evidence.py](../../../src/qi/training_data/candidate_evidence.py), [compatibility.py](../../../src/qi/training_data/compatibility.py) |

[ADR-0008](../../../docs/adr/0008-sqlite-collection-parquet-snapshots.md) records
architectural trade-offs. The module guide owns current behavior and commands;
the original forward specification has been retired after delivery. Production
optimizer integration remains [AB-LEARN-010](AB-LEARN-010-snapshot-training-protocol.md).

### Ownership and related work

- Training Data owns persistence, sampling, supervision selection, export and
  loading; trainer adapters own tensor preparation and optimization.
- [AB-DATA-005](AB-DATA-005-experiment-data-sanity.md) already owns generation and
  evaluation isolation hardening. Enforce its generation-side duplicate-trajectory
  check in the new path and record that contribution there; do not declare its
  independent arena/checkpoint-overlap work complete.
- [AB-DATA-006](AB-DATA-006-observation-contracts.md) owns shared observation
  contracts. Reconcile the new canonical board identity there without inventing
  tensor/text consumers or silently changing old hashes.
- [AB-LEARN-008](AB-LEARN-008-experiment-performance.md) owns broad experiment
  profiling; this slice contributes narrowly scoped persistence/read evidence.
- [AB-DATA-008](AB-DATA-008-generation-scaling-pilot.md) owns pilot settings and
  overnight decisions. Infrastructure can begin before those research knobs lock.

### Required verification

1. Same board at different histories keeps separate occurrences and analyses.
2. Interruption before/after a commit and reopen preserve committed work and
   expose incomplete attempts, without duplicate logical completion.
3. Prefix mutation is rejected; subsequent append preserves earlier replay.
4. Failure followed by success retains both attempts; second-spec reanalysis
   requires no game regeneration.
5. Cross-family/trajectory/observation leakage and unavailable quotas are rejected.
6. Export followed by additional analyses/annotation changes leaves export hashes
   and reread targets unchanged; standalone replay verification succeeds.
7. JSON import/export on representative supported fixtures preserves logical data.
8. Increasing source counts measures wall time, write volume, peak memory and
   records/s without per-insert full-library work. Also measure batch-read rate
   and peak memory; predeclare workload/settings before benchmarking.
9. Multiple successes resolve by success-commit order within one occurrence/spec;
   explicit overrides pin the chosen success, while another spec is independent.
10. Interrupted prefixes remain inspectable/reanalyzable but are excluded by
    default; a completed ply-budget continuation remains eligible.
11. Identical recipe and source state reproduce selection/order, including ties;
    bounded tensor preparation agrees with the existing adapter on a small fixture.

Implementation and bounded synthetic verification are recorded below; no overnight
generation or production optimizer change is part of this item.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | ready | User consolidated architecture and requested ADR/spec capture; core build scope is sufficient, with pilot policy handled separately. |
| 2026-09-10 | Codex | ready | wip | User authorized implementation after locking the readiness frontier. |
| 2026-09-10 | Codex | wip | done | Collection, SQL selection, frozen snapshots, bounded reads and compatibility verified; optimizer protocol remains AB-LEARN-010. |

## Implementation Ledger

### 2026-09-10 — decision: accepted storage and snapshot architecture

- Evidence: user accepted the five-table reduction, requested extensible binary
  JSON payloads and database-native access, then consolidated the SQLite/JSONB
  and SQL-selected Parquet recommendation and requested durable records.
- Consequence: ADR-0008 and this specification govern the first build. Existing
  guides continue to describe implemented JSON behavior until implementation.
- Follow-up: implement bounded persistence and snapshot access; resolve the
  AB-DATA-008 frontier before freezing the generation experiment.
- Review: ratified for architecture and build scope; no claim of execution.

### 2026-09-10 — decision: readiness frontier locked

- Evidence: user accepted the recommendations in the referenced ChatGPT
  conversation "Selection Recipe Design" (conversation ID
  `6aa2a49a-a810-83e9-9200-0e27284f9d8d`) and the proposed completion boundary (#1).
- Decision: versioned recipe compiled into SQL; first committed success per
  occurrence/specification with explicit attempt overrides; completed-game-only
  default selection while preserving interrupted evidence; delivery through
  verified snapshots and bounded tensor-preparation integration.
- Consequence: ready for infrastructure implementation. Production optimizer
  integration requires a separate work item and an explicitly locked training
  protocol; this item does not authorize that change or a generation run.
- Review: accepted decisions captured; application implementation has not begun.

### 2026-09-10 — decision: persistence/read benchmark protocol

- Question: does incremental persistence avoid per-insert full-library work as
  source count increases? Expect roughly proportional write volume, with bounded
  application memory; a superlinear trend or integrity failure requires investigation.
- Prior evidence: `persistent-teacher-v1` measured small shallow full preparation;
  `teacher-throughput-20260909` measured repeated queries. Neither establishes
  collection persistence or Parquet read costs.
- Workload: `scripts/benchmark_collection.py`, fresh processes at 16/64/256 random
  games, seed 7, 16 additional plies and four synthetic legal labels per game,
  equal train/validation source counts. No engine or optimizer is executed.
- Selection: explicitly reserve shared cross-split inputs and their history prefixes
  before export, retaining the resolved corpus. This is an exploratory infrastructure
  workload, not a learning dataset. Fixed quotas are half the game count per split;
  never lower quotas after a failure. Parquet shards 256, reader batches 128.
- Measurements: generation wall time, occurrences/s, serialized SQL write bytes
  (logical traffic, not physical disk write amplification), final disk bytes,
  standalone verified export cost, batch rows/s, writer-process and fresh-reader
  peak RSS. One execution per size; startup/cache noise is not statistical evidence.
- Budget: 600 seconds per size; stop on failure or quota shortfall and preserve
  raw files. Keep configs, source copies, provenance, manifests and results under
  `artifacts/learning/collection-io-v1/`. Do not extrapolate to an overnight run.
- Review: not-required; bounded verification within the authorized build scope.


```experiment
{
  "schema_version": 1,
  "id": "collection-io-v1",
  "title": "Collection persistence and bounded reads",
  "question": "Does collection persistence avoid full-library work as source count grows?",
  "kind": "performance",
  "topics": [
    "sqlite",
    "parquet",
    "persistence",
    "bounded reads",
    "training data"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Fresh processes at 16/64/256 random games, 16 plies, four synthetic legal labels/game, seed 7. Fixed split quotas; explicit shared-input exclusions. Shards 256 and batches 128; one execution/size, 600s cap.",
  "limitations": "Synthetic labels, small exploratory scaling series; no teacher, training or overnight throughput inference. Logical SQL bytes are not physical disk writes.",
  "decision": "Investigate integrity failure or superlinear growth before readiness claims.",
  "revisit": "Representative larger distinct-position workloads and real-teacher preparation.",
  "evidence": [
    {
      "path": "scripts/benchmark_collection.py",
      "role": "source",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "persistent-teacher-v1",
      "relationship": "extends",
      "contribution": "Measures incremental collection persistence and bounded snapshot reads separately from teacher startup."
    }
  ],
  "novelty": "Bounded collection write/read evidence under the new storage path; not teacher throughput."
}
```

### 2026-09-10 — verification: infrastructure delivery

- Implemented five-table SQLite/JSONB storage, capability/version checks, writer
  ownership, per-unit transactions, immutable occurrence identities, recovery,
  stable source resume, retained failures, typed candidate evidence and reanalysis.
- Added versioned recipe-to-SQL selection, first-success/override resolution,
  source-family/trajectory/input isolation, deterministic bucket ownership and
  quota failures. Export freezes typed Parquet and a compact evidence SQLite
  subset, verifies replay/labels and hashes before publication, and retains
  incomplete export evidence. Readers prepare bounded batches.
- Explicit v1/library imports retain parent/source/history/target evidence;
  small expressible v1 exports carry a snapshot provenance sidecar. Unsupported
  conversions fail explicitly. Existing JSON loading/training remain compatible.
- Verification: full `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check`
  passed 490 Python tests with one opt-in MPS skip, five browser lifecycle tests,
  production builds, lint, docs and catalog. Subsequent focused verification
  passed 12 store/compatibility tests plus one tensor-parity test, including the
  added curated-phase import and failed-actor accounting assertions.
- Corrected a duplicate Position glossary entry from the architecture capture
  after it caused 13 report/glossary failures; existing definition now includes
  the canonical board/history distinction. No unrelated changes were reverted.
- Follow-up: [AB-LEARN-010](AB-LEARN-010-snapshot-training-protocol.md) owns
  production optimizer integration; AB-DATA-008 owns larger generation policies
  and pilot execution. Current generation adapter retains existing per-run limits.
- Review: not-required; accepted infrastructure scope complete. No commit or
  overnight run performed.

### 2026-09-10 — finding: bounded synthetic collection I/O

The serial verified series completed all fixed quotas and standalone snapshot
checks. [Compact evidence](../../../data/experiments/learning/history/collection-io-v1.json)
links configs, source copies and raw runs. Values below are measured on this host.

| Games | Occurrences | Analyses | Write seconds | Logical SQL bytes | Export seconds | Snapshot rows | Writer peak MB | Reader peak MB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16 | 256 | 64 | 0.238 | 809583 | 0.048 | 16 | 78.5 | 71.0 |
| 64 | 1024 | 256 | 0.839 | 3197834 | 0.057 | 64 | 84.6 | 71.2 |
| 256 | 4096 | 1024 | 3.213 | 12760193 | 0.093 | 256 | 105.2 | 72.1 |

- Finding: 16x occurrences produced about 15.8x logical write traffic and 13.5x
  generation time. Writer RSS rose with bounded caches; fresh-reader RSS stayed
  around 71–72 MB. Batch reads were 444/1761/7059 rows/s, dominated by startup
  at these small sizes; they are not sustained large-dataset throughput estimates.
- Limits: one synthetic execution per size, no teacher or optimizer work, and
  logical SQL traffic rather than physical disk write amplification. A first
  benchmark attempt failed because its exclusion corpus duplicated the initial
  snapshot; its evidence and intermediate successful series remain retained.
- Decision: the measured series supports the incremental access pattern within
  this bounded workload. It does not establish million-position or overnight
  readiness. Revisit under AB-DATA-008 with representative games, budgets and
  larger exports before choosing scale or concurrency settings.
- Review: not-required; bounded implementation evidence, not a learning result.


```experiment
{
  "schema_version": 1,
  "id": "collection-io-v1",
  "title": "Collection persistence and bounded reads",
  "question": "Does collection persistence avoid full-library work as source count grows?",
  "kind": "performance",
  "topics": [
    "sqlite",
    "parquet",
    "persistence",
    "bounded reads",
    "training data"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "At 256/1024/4096 occurrences, generation took 0.238/0.839/3.213 seconds and logical SQL writes were 0.810/3.198/12.760 MB. Fresh-reader peak RSS was 71.0/71.2/72.1 MB; all fixed quotas and replay checks passed.",
  "conditions": "Fresh processes at 16/64/256 random games, 16 plies, four synthetic legal labels/game, seed 7. Fixed split quotas; explicit shared-input exclusions. Shards 256 and batches 128; one execution/size, 600s cap.",
  "limitations": "Small synthetic storage workload, no teacher/optimizer/overnight inference. SQL bytes are logical traffic, not physical disk writes. PyArrow optional CPU-cache sysctls were restricted by the sandbox; reads succeeded. Source copies preserve executed code; later failed-actor telemetry correction does not affect this random-only workload.",
  "decision": "Accept incremental collection access for the measured bounded workload; keep million-position/overnight readiness open.",
  "revisit": "Representative larger distinct-position workloads and real-teacher preparation.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/collection-io-v1.json",
      "role": "results",
      "sha256": "af7bc47f92655d2292e0eb85955c225e81ce9a2d00249089a9aae74bca6beda4"
    },
    {
      "path": "artifacts/learning/collection-io-v1-verified/results.json",
      "role": "results",
      "sha256": "b6b188a6ad798e6cd83757975a39254db1a9cedddb4d1a321b0292dba4029ac5"
    },
    {
      "path": "artifacts/learning/collection-io-v1/failure.json",
      "role": "results",
      "sha256": null
    },
    {
      "path": "scripts/benchmark_collection.py",
      "role": "source",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "persistent-teacher-v1",
      "relationship": "extends",
      "contribution": "Measures incremental collection persistence and bounded snapshot reads separately from teacher startup."
    }
  ],
  "novelty": "Bounded collection write/read evidence under the new storage path; not teacher throughput."
}
```

### 2026-09-10 — verification: independent review and cleanup

- Independent review reproduced a writer-lock bypass through symlink aliases and
  incomplete recipe enforcement in standalone verification. Canonical writer
  paths and bounded reselection over frozen evidence fix both; the reviewer
  reran reproductions and a valid omitted-override case successfully.
- Legacy export now requires representable imported v1 source provenance,
  preserves the generation seed independently of selection seed, and records
  parent hashes. Import indexes lineage once and records failed attempts.
- Shared source identity construction replaces duplicate generator logic;
  selection no longer copies unused analysis payloads into its temporary table.
  The optional `selected_only` recipe filter distinguishes retained actor audit
  analyses from explicitly selected occurrences and records its SQL binding.
- Retired the landed forward specification in favor of current module authorities.
  Existing supported JSON readers and converters remain available.
- Focused verification: 15 store tests and one bounded tensor integration test
  passed. The compact snapshot verifies retained eligibility and order; it does
  not prove ranking against observations omitted from the original collection.
- Final repository gate: `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check`
  passed lint, docs, catalog, production builds, 544 Python tests (one opt-in MPS
  skip) and five browser tests. Counts include concurrent generation-policy tests;
  those separately owned files are excluded from the infrastructure commit.
