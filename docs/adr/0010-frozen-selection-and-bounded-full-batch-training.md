---
description: Preserve full-batch optimization while selecting and training bounded immutable snapshots.
scope: architecture decision
status: stable
last_update: 2026-09-11
document_class: coordination
produced_by: "domain-modeling@1.4.1 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# ADR-0010: Frozen selection and bounded full-batch training

- **Status**: accepted
- **Last Update**: 2026-09-11
- **Serves**: Training Data owns selection; trainers own weight optimization.

The user accepted the generated-data audit recommendations and authorized the
first mixture study. Preserve full-batch Adam while consuming immutable snapshots
in bounded chunks. Training Data explicitly records excluded model inputs and
position/label semantic predicates in the selection recipe.

## Context

The new collection has shared split observations, same-specification target
conflicts and multiple teacher regimes. Exclusions are decisions, not new
evaluation openings. Per-position tactical features are not inherited source
themes. Historical v1 recipes must retain their original interpretation.

## Considered Options

- Adopt minibatch Adam now: useful later, but changes continuity with previous
  learning experiments. The user chose full-batch updates for this comparison.
- Materialize the full dataset or export it through legacy JSON: defeats bounded
  memory or misrepresents generated-source provenance.
- Hide exclusions in the reserved opening corpus or modify collection facts:
  obscures the distinction between retained evidence and selection policy.

## Consequences

Version 2 selection recipes add reasoned input exclusions, explicit input lists
per bucket and versioned immediate tactical predicates. The compiler still
validates lineage, labels, eligibility, priority and deterministic order. Original
v1 recipes remain valid with the new fields absent. Frozen evidence retains all
contributing source histories; exclusion is symmetric across experimental splits.

Verified snapshot rows prepare a disk-backed tensor cache in bounded batches.
Cache identity pins the snapshot and prepared files. Each complete pass sums
chunk losses divided by the total training count, then performs exactly one Adam
update. Chunking bounds memory; it is not minibatch optimization. Floating-point
accumulation order can differ, so parity uses explicit numeric tolerances.

Use fixed snapshot order, float32, explicit CPU/MPS device and chunk size. Check
deadlines between chunks, discard an unfinished pass's gradients, and retain
only fully completed updates in a terminal checkpoint. No optimizer-state resume
or automatic fit continuation is claimed. Reports and predictions distinguish
complete, deadline and failed work and retain dataset/specification provenance.
