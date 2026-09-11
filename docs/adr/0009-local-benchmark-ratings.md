---
description: Keep local playing-strength ratings conditional on frozen benchmark conditions and replayed matches.
scope: architecture decision
status: stable
last_update: 2026-09-11
document_class: coordination
---

# ADR-0009: Local benchmark ratings over retained matches

- **Status**: accepted
- **Last Update**: 2026-09-11

Use versioned benchmark series to guide player iteration. Freeze the reference
panel, opening book, adjudication and scoring method. Player configuration and
resource identity define a rated entrant; the referee owns every result, and
ratings are recomputable projections of complete color pairs.

## Context

The user accepted local Elo for iteration, heterogeneous resources with measured
costs, a six-player reference panel, paired human-game openings, development and
single-use confirmation pools, resumable execution, and CLI plus Qi Lab results.
Existing evaluation retains replayable two-player results but has no league,
resume or uncertainty layer. Search visits, native engine nodes and inference
calls do not represent equal compute.

## Considered Options

- **Game-by-game Elo updates** — rejected because update order and learning-rate
  choices would affect a benchmark intended to be recomputed from fixed evidence.
- **One external engine's published Elo as truth** — rejected because this
  ruleset, opening distribution and resource settings define a different scale.
- **Batch ratings under frozen conditions** — selected. A frozen alpha-beta
  entrant defines 1000 local Elo; a draw-aware fit and family-level uncertainty
  describe the evidence without converting a prior into observed wins.

## Consequences

Bootstrap the reference panel with a round robin; new candidates face the panel
and their predecessor. Compatible completed games can be reused exactly once.
Changed benchmark conditions create a different series identity. Saved rating
snapshots never rewrite past conclusions when new evidence changes a fit.

Human-game prefixes provide variety but bypass the entrant's opening choices;
standard-start games are a separately reported diagnostic. Confirmatory pools
are committed to frozen candidates before play, revealed after completion, and
retired on reveal. Local files are an operational guard, not a secrecy boundary
against their owner. Missing training provenance cannot certify held-out status.

The [benchmark contract](../benchmark.md) owns execution and statistical details;
[AB-EVAL-005](../../records/work-items/items/AB-EVAL-005-local-elo-benchmark.md)
owns delivery and verification.
