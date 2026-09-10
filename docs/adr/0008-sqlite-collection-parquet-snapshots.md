---
description: Use an incremental SQLite collection and SQL-selected Parquet snapshots for training data.
scope: architecture decision
status: stable
last_update: 2026-09-10
document_class: coordination
produced_by: "domain-modeling@1.4.1 · agent=GPT-6 · effort=unspecified · 2026-09-10"
---

# ADR-0008: SQLite collection and frozen Parquet snapshots

- **Status**: accepted
- **Last Update**: 2026-09-10
- **Serves**: [Training Data ownership, composition and identity](../models.md).

Use SQLite as the growing Training Data collection, with typed columns and
validated JSONB for extensible payloads. Backend operations query the collection;
training consumes immutable Parquet snapshots selected through SQL and validated
under explicit composition policies. JSON remains supported for existing artifacts
and small configurations, rather than the primary bulk-data representation.

## Context

The proposed one-million-position generation study needs incremental persistence,
recovery, metadata queries and reanalysis under multiple teacher configurations.
Current preparation reconstructs and writes the growing library after each game;
current training loads and copies whole JSON datasets. Changing the file format
without replacing those access patterns would preserve the scaling bottlenecks.

Board-and-turn equality, an occurrence in a trajectory, and a teacher analysis
have different identities. A played move is a trajectory fact; a recommended
move is evidence under a particular supervision specification. These distinctions
must survive storage changes without requiring a table for every concept.

## Considered Options

- **Continue whole-collection JSON**: retains compatibility but does not address
  incremental queries, writes, recovery or bounded training reads.
- **SQLite collection and frozen Parquet exports**: selected. SQLite serves local
  transactional generation and reanalysis; Parquet supplies portable, typed batch
  data. Export costs time and extra storage, but fixes training input independently
  of subsequent collection changes.
- **Train repeatedly from a live SQL view**: rejected as the default. A view saves
  a query, not its results; later analyses and annotations can change the dataset.
  A separately frozen SQLite snapshot is viable but a second training backend is
  not part of the first implementation.
- **Parquet as the generation store**: useful for immutable bulk data, but would
  need additional machinery for per-attempt state, incremental deduplication and
  recovery. It is the export format rather than the operational store.
- **Eight normalized tables immediately**: defer separate positions, annotation
  histories and candidate-move tables until measured queries or storage justify
  them. Board hashes and typed payloads preserve their meaning in five tables.

## Consequences

- Collection records facts; selection expresses policy; snapshots freeze decisions.
  A small versioned selection recipe is the export interface and compiles to SQL;
  record both recipe and SQL/parameters. Arbitrary export SQL and a general query
  DSL are outside the first implementation. Isolation and label-conflict checks
  remain mandatory. Default selection excludes incomplete game attempts while
  retaining their evidence for inspection and reanalysis.
- The first committed success per occurrence/specification is the default analysis.
  Reanalysis appends evidence; a different specification has its own default.
  Explicit export overrides pin another successful attempt without rewriting history.
- The first collection has `generation_runs`, `games`, `position_occurrences`,
  `analysis_specs` and `analyses`. Board identity is required and indexed even
  though board values are stored on occurrences. Exact-state identity governs
  history-sensitive analysis; board equality alone never authorizes reuse.
- JSONB is an internal SQLite representation. Versioned application validation
  remains required; identity hashes use canonical logical content, not JSONB
  bytes. Backend filters and relationships use explicit columns where useful.
- Persist trajectories once, preserve referenced prefixes and keep analysis
  attempts separately. Use short transactions and one application-side writer;
  teacher execution occurs outside write transactions. Resume from committed
  games; exact mid-game continuation is outside the initial contract.
- Freeze SQL results from a consistent source state with exact analysis/content
  identities, splits, order, annotation and target policies, counts and shard
  hashes. SQL text or local row IDs alone are insufficient. Final snapshots are
  self-contained for training and retain replay/source evidence for verification.
- Parquet rows expose typed fields and nested structures. Training reads bounded
  batches without materializing all examples, legal masks or logits. Hugging Face
  compatibility does not require that library, remote hosting or publication.
  AB-DATA-007 delivers the reader and tensor-preparation integration verification;
  production optimizer integration follows under a separately locked protocol.
- Preserve old files and fingerprint meanings. Explicit import/export adapters
  support the existing formats where semantics are representable; unsupported
  conversions fail rather than dropping provenance or mixing target contracts.
- [AB-DATA-007](../../records/work-items/items/AB-DATA-007-sqlite-training-data-store.md)
  owns the build specification. [AB-DATA-008](../../records/work-items/items/AB-DATA-008-generation-scaling-pilot.md)
  owns the pilot and overnight protocol. The Training Data guide now owns the
  implemented collection/export/reader contracts; AB-DATA-007 records verification
  and bounded persistence/read evidence. This does not establish overnight readiness.

SQLite's [JSONB documentation](https://sqlite.org/json1.html#jsonb),
[view semantics](https://sqlite.org/lang_createview.html) and Hugging Face's
[Parquet loading guide](https://huggingface.co/docs/datasets/loading#parquet)
support the format and interface distinctions above.
