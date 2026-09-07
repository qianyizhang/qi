---
description: Version simplified repetition and length adjudication for the first training environment.
scope: architecture decision
status: stable
last_update: 2026-09-07
document_class: coordination
---

# ADR-0002: Version simplified training adjudication

- **Status**: accepted
- **Last Update**: 2026-09-07

Use an explicitly versioned training ruleset with threefold repetition draws and
a 300-ply ceiling. Ordinary terminal outcomes take precedence. The current
contract is [xiangqi-training-v1](../xiangqi-training-v1.md).

## Context

The first playable environment must support deterministic replay and bounded
games. The user accepted simplified adjudication as sufficient for now and
explicitly expects that it may change later. Saved games and training data must
retain their original ruleset meaning when that happens.

## Considered Options

- **Full competitive repetition/chasing adjudication initially** — deferred
  because its correctness work would delay the playable learning environment.
- **Versioned simplified adjudication** — selected for bounded implementation
  and reproducible results, accepting strategically exploitable drawing loops.
- **Unbounded games or silently changing cutoffs** — rejected because results
  would be harder to reproduce and compare across experiments.

## Consequences

Repeated checking and chasing receive no special penalty in this version.
Players may exploit those cycles to draw. Length-limited draws may also distort
playing incentives; neither kind of draw establishes competitive adjudication.

Any semantic change receives a new ruleset identity. Preserve history and the
ruleset identity in replay data. Do not mix results from different rulesets
without identifying them. The 300-ply ceiling is a project choice, not an
assertion about official Xiangqi rules.
