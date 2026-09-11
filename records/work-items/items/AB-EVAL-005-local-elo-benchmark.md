---
description: Build local ratings, resumable paired benchmarks and a Qi Lab results view for player iteration.
scope: backlog item
status: stable
last_update: 2026-09-11
document_class: work_record
work_id: AB-EVAL-005
work_status: done
work_kind: build
added: 2026-09-11
tags: domain, frontend
depends_on: AB-EVAL-004
residual_of: none
residual_items: none
---

# AB-EVAL-005 — Local Elo benchmark

## Intent

Guide checkpoint iteration using local ratings against a frozen, diverse panel,
with replayable games and explicit costs and uncertainty.

## Acceptance Criteria

- Frozen series/spec/entrant identity; six-reference round robin and extensible
  candidate gauntlet; alpha-beta anchored to 1000 local Elo.
- Sourced, replay-validated human-game opening book with family-separated
  development/locked-test partitions, and separate standard-start diagnostics.
- Atomic per-game evidence, writer exclusion, preserved attempts, explicit
  resume and compatible evidence reuse; paired scoring and offline validation.
- Draw-aware regularized batch ratings, family-level uncertainty, disconnected
  and sparse-result handling, immutable reports and locked-pool reveal/retirement.
- Typed CLI and read-only Qi Lab progress/results with ratings, matchups, costs,
  provenance and partial/failed states.
- Focused integrity/statistics/recovery tests, API and browser coverage, full
  repository checks, and a retained real-Pikafish throughput pilot.

## Context and Trade-offs

All thirteen interview recommendations were accepted, then implementation was
authorized with “go build”. [Contract](../../../docs/benchmark.md) and
[ADR-0009](../../../docs/adr/0009-local-benchmark-ratings.md) retain the decisions.
Prior teacher-quality evidence remains inconclusive for imitation and says
nothing about playing strength. Existing paired evaluation supplies outcome
validation; this work adds multi-player scheduling, persistence and ratings.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | wip | User accepted the decision interview and authorized build. |
| 2026-09-11 | Codex | wip | done | CLI, ratings, source books, resumable evidence and Lab results delivered; repository/browser checks and real-Pikafish pilot passed. |

## Implementation Ledger

### 2026-09-11 — decision

- Evidence: accepted interview, repository evaluation/referee/player contracts,
  and the linked statistical primary sources.
- Consequence: implement the explicit Davidson MAP and family-bootstrap method
  described in the contract; retain unavailable uncertainty for sparse evidence.
- Follow-up: source the book, implement and validate the complete delivery;
  calibrate provisional presets using a bounded throughput pilot.
- Review: ratified for product decisions; statistical implementation recorded
  for reproducibility, with approximation limits explicit.

### 2026-09-11 — delivery and verification

- Delivered the Python benchmark authority, CLI, immutable report snapshots and
  read-only Lab results page. Candidates can reuse compatible development
  reference games; fresh locked-test pools execute the full comparison matrix.
  Replay validation, writer exclusion and a durable pool registry protect
  recovery, test reservation and reveal/retirement boundaries.
- Retained [CCPD source attribution and selection](../../../data/evaluation/human-openings-v1/README.md):
  170 development starts in 93 opening families and 30 locked-test starts in 17
  families. This is a bounded, audited subset, not a representative dataset claim.
- `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed: 591 Python tests,
  one optional MPS skip, five JavaScript lifecycle tests, lint, docs, catalog,
  generated API/type checks and production build. All 70 desktop/mobile browser
  tests passed. Integrity cases cover interrupted/failed games, evidence reuse,
  locked-pool lifecycle, replay corruption, snapshot integrity and path boundaries;
  statistical cases check derivatives, known odds and family resampling.
- [Retained pilot result](../../../data/evaluation/benchmark-pilot-v1.json): all
  60 predeclared games completed in 229.902 seconds, with zero failed attempts;
  30 varied-opening games and 30 standard-start diagnostics. Offline replay and
  no-op resume preserved the evidence digest. The archived executed source was
  independently hashed against attempt provenance. Raw evidence remains in
  `artifacts/benchmarks/reference-pilot-v1`; protocol, bindings and executed source
  remain in `artifacts/benchmark-pilot-v1`.
- The one-family pilot verifies engineering behavior and records throughput; it
  does not establish representative playing strength or useful uncertainty.
  Concurrent local checks and heterogeneous per-move resources limit timing
  interpretation. The editable 16-start default is an initial working size.
- Future candidate checkpoints use the delivered gauntlet interface; no new
  trained model or automatic promotion policy is part of this delivery.


```experiment
{
  "schema_version": 1,
  "id": "benchmark-throughput-v1",
  "title": "Local Elo benchmark engineering and throughput pilot",
  "question": "Can the six-reference benchmark complete replayable paired games and record useful cost observations?",
  "kind": "performance",
  "topics": [
    "Elo",
    "full-game",
    "paired games",
    "Pikafish",
    "benchmark",
    "throughput"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Six frozen entrants; one development-book start plus one standard-start diagnostic, both colors, 15 matchups and 60 games. One thread and 16 MiB hash for Pikafish. Fixed native node/depth and qi-visit profiles; 900-second wall allowance.",
  "limitations": "One varied starting family is an engineering pilot; ratings and intervals cannot establish representative strength. Heterogeneous resources and per-move fresh Pikafish processes are intentional.",
  "decision": "",
  "revisit": "",
  "evidence": [
    {
      "path": "artifacts/benchmark-pilot-v1/protocol.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "artifacts/benchmark-pilot-v1/frozen.json",
      "role": "config",
      "sha256": null
    }
  ],
  "prior_work": [],
  "novelty": "Adds multi-player rating, restart/reuse and UI evidence over the existing paired-game and named-player boundaries."
}
```


```experiment
{
  "schema_version": 1,
  "id": "benchmark-throughput-v1",
  "title": "Local Elo benchmark engineering and throughput pilot",
  "question": "Can the six-reference benchmark complete replayable paired games and record useful cost observations?",
  "kind": "performance",
  "topics": [
    "Elo",
    "full-game",
    "paired games",
    "Pikafish",
    "benchmark",
    "throughput"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "All 60 planned games (30 rated, 30 standard-start diagnostics) completed in 229.902 seconds with zero failed attempts. Every completed game replayed; a no-op resume preserved all evidence. The retained executed-source archive matched its recorded hash. The human book has 170 development starts in 93 families and 30 locked starts in 17 families.",
  "conditions": "Six frozen entrants; one development-book start plus one standard-start diagnostic, both colors, 15 matchups and 60 games. One thread and 16 MiB hash for Pikafish. Fixed native node/depth and qi-visit profiles; 900-second wall allowance. Shared Mac workload included concurrent repository/browser checks. Executed source is retained independently of subsequent scheduling and snapshot-persistence hardening.",
  "limitations": "One varied starting family; no representative playing-strength conclusion or usable family-bootstrap interval. Heterogeneous settings, fresh Pikafish processes and concurrent local work affect timing. Source archive and raw games are local, ignored artifacts.",
  "decision": "Accept benchmark execution, replay, recovery and result presentation. Keep configurable 16-start development batches as an initial working size; the pilot does not establish an optimal sample count or reference resource profile.",
  "revisit": "Run the full varied-opening development batch with candidate checkpoints; inspect family-level intervals, matchup discrepancies, failures and actual runtime before changing sample counts or reference profiles.",
  "evidence": [
    {
      "path": "artifacts/benchmark-pilot-v1/protocol.json",
      "role": "config",
      "sha256": "0d27206112cccac486b94eca405560b526cf7325ee14ec968fc2f6c4b74c33a4"
    },
    {
      "path": "artifacts/benchmark-pilot-v1/frozen.json",
      "role": "config",
      "sha256": "d69963a2c35c1d93e5ac34120b8105987739a1750314b5ccde77410d6bbae73c"
    },
    {
      "path": "data/evaluation/benchmark-pilot-v1.json",
      "role": "results",
      "sha256": "fba2560a4a901f368e72f8f66f811aafc7b8aa707a747bf4d4dbb18c999b2c71"
    },
    {
      "path": "artifacts/benchmarks/reference-pilot-v1/manifest.json",
      "role": "run",
      "sha256": "580abb1d781bab13eb4213f6c40b373ca04dc606d632512643219ab46deafcf8"
    },
    {
      "path": "scripts/import_benchmark_book.py",
      "role": "source",
      "sha256": "aa9641f97b2b757a570f8ed712bd8e52542983d80b0def1a092df1590b7b0440"
    }
  ],
  "prior_work": [],
  "novelty": "Adds multi-player rating, restart/reuse and UI evidence over the existing paired-game and named-player boundaries."
}
```
