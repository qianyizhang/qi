---
description: Preserve historical rating inputs so saved projections can be verified after a run resumes.
scope: architecture decision
status: stable
last_update: 2026-09-12
document_class: coordination
---

# ADR-0011: Verify rating snapshots against their original evidence

- **Status**: accepted
- **Last Update**: 2026-09-12

Each newly saved benchmark rating snapshot retains the exact evidence inventory
and attempt contents needed to reconstruct its original scoring inputs. The reader
validates that evidence and recomputes the projection before serving verified ratings.
This extends [ADR-0009](0009-local-benchmark-ratings.md)'s immutable historical
projections across resumed execution.

## Context

The former snapshot endpoint checked only identity fields: changing a saved Elo
from 1000 to 1500 retained a successful response even though the ordinary verifier
rejected it. Recomputing an old snapshot from current attempts is insufficient:
resumes add attempts and can finalize a formerly running attempt in place.

## Considered Options

- **Trust identity fields in saved JSON** — cannot detect changed derived values.
- **Serve only current verified results** — loses the accepted historical browsing flow.
- **Retain and replay original inputs** — selected; keeps historical claims verifiable
  without changing them when later evidence arrives.

## Consequences

The frozen inventory includes mutable attempt observations, not just paths to them.
Snapshots continue to enforce the current locked-test reveal boundary. Old artifacts
remain unchanged: when their original inputs cannot be reconstructed, the browser
labels their projections unverified rather than claiming evidence validation.
Snapshot verification never launches players or rewrites scientific results.
