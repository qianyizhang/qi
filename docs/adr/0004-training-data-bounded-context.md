---
description: Separate training-data composition and supervision provenance from weight optimization.
scope: architecture decision
status: stable
last_update: 2026-09-09
document_class: coordination
---

# ADR-0004: Training Data as a bounded context

- **Status**: accepted
- **Last Update**: 2026-09-09
- **Serves**: [Core model: ownership, composition and identity](../models.md).

Give Training Data ownership of trajectory sources, position sampling,
supervision provenance and frozen dataset assembly. Trainers consume the selected
examples to prepare model inputs and update weights. Keep generation mode,
addressable situation and supervision specification independently configurable.

## Context

The first trainer embeds one random trajectory generator, one teacher recipe and
one observation encoding in its dataset model. Data scaling improved imitation,
but opening-biased examples do not cover the desired middlegame, endgame and
classical scenarios. Additional generation modes and mixtures need independent
rules for selection, target identity, source lineage and evaluation isolation.
The user accepted these boundaries in the recorded decision interview.

## Considered Options

- **Extend the trainer's generator-mode switch**: small initial change, but ties
  sampling, supervision and composition changes to the optimization pipeline.
- **A separate pipeline for each mode**: duplicates split, identity and coverage
  rules and makes mixtures harder to interpret.
- **One Training Data context with composable responsibilities**: selected to
  centralize data invariants and make datasets reusable across training recipes.

## Consequences

Dataset manifests reference canonical content fingerprints; game-state identity,
model-visible observation identity and labeled-example identity stay distinct.
The first mixed datasets keep one supervision contract and teacher recipe.
Migration must preserve existing artifacts and their recorded digest meanings.
The referee remains outcome authority, and teacher access remains explicit.

This accepts an architectural boundary, not an implemented package or service.
The owning [core model](../models.md) records the accepted behavior; the
[decision record](../../records/work-items/items/AB-DATA-001-training-data-boundary.md)
retains interview evidence. Persistent teacher sessions are an adapter execution
choice to benchmark separately, not a prerequisite for this boundary.
