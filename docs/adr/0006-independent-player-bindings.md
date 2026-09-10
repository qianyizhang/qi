---
description: Resolve named player configurations and external-engine participation independently per participant.
scope: architecture decision
status: stable
last_update: 2026-09-10
document_class: coordination
---

# ADR-0006: Independent player bindings and explicit engine participation

- **Status**: accepted
- **Last Update**: 2026-09-10
- **Serves**: [Core model: player configuration and identity](../models.md#player-configuration-and-identity).

Resolve a named local player binding independently for each participant. A
binding selects a player implementation and any configured checkpoint or
external-engine resources; resolution pins their content identities. Pikafish
may be an explicitly selected player, while other players retain their existing
access boundaries. The user accepted independent named entries, including two
distinct learned checkpoints, during the frontend decision interview.

## Context

The player catalog currently identifies algorithms. A learned player resolves
one process-wide environment path, so two participants cannot independently
select different checkpoints. The browser also needs human/computer and
computer/computer selection without accepting executable or checkpoint paths.

The existing teacher adapter owns local UCI interaction, and qi owns legality
and outcomes. Reusing the adapter for a selected Pikafish participant does not
make that engine a helper available to every evaluated player. This extends
explicit external-engine use consistently with
[ADR-0001](0001-own-referee-and-search-use-external-teachers.md).

## Decision

- Keep implementation IDs/versions separate from named configured bindings.
  Multiple bindings may use the same implementation with different resources.
  Display labels and lookup IDs are not content identities.
- Configure resource paths on the server. Browser requests select exposed
  bindings and supported settings; each participant resolves independently to
  pinned checkpoint or engine/network content identities.
- Retain `QI_POLICY_CHECKPOINT` as a convenience default. Replacing a named
  entry or its underlying file must not silently replace a pinned participant.
  Missing or mismatched identities fail explicitly, allowing the user to choose
  a replacement through the game's recorded configuration-change flow.
- Reuse one player selection boundary for browser play, CLI, arena and
  evaluation. The referee validates every returned move and adjudicates the
  resulting state. Saved evidence can be validated without loading weights or
  launching engines.
- Declare supported controls and budget semantics with player metadata.
  qi search retains strict charged-visit accounting. External-engine requested
  limits and reported work retain their native meaning, including possible
  overshoot and unavailable counters. Do not coerce native scores or node counts
  into qi metrics or imply equal compute from equal numerical limits.

## Considered Options

- **One process-wide checkpoint**: smallest change, but prevents two learned
  checkpoints from coexisting and makes participant identity dependent on a
  shared setting.
- **One algorithm registration per checkpoint**: makes the menu possible but
  confuses algorithm behavior with model configuration and duplicates catalog
  registrations whenever weights change.
- **Browser-supplied local paths**: flexible, but gives presentation clients
  responsibility for executable/resource resolution and bypasses the existing
  server-owned configuration boundary.
- **Independent named bindings with pinned resources**: selected to reuse
  implementations while making each participant explicit and reproducible.

## Consequences

This changes participant construction and recorded identity, not referee
ownership or automatic tool access. Pure checkpoint inference remains one CPU
model pass; search settings are inapplicable to that implementation. External
engine failures are failed decisions, not inferred game outcomes or a reason to
substitute another player silently.

Shared validators need typed engine-specific evidence alongside the existing
qi invariants. Preserve existing artifact meanings; version any changed
interchange contract and identify how old valid artifacts remain readable.

[AB-ENGINE-005](../../records/work-items/items/AB-ENGINE-005-independent-checkpoints.md)
owns shared independent checkpoint binding and paired-evaluation proof.
[AB-UI-002](../../records/work-items/items/AB-UI-002-consolidated-lab.md) owns the
frontend integration and explicit Pikafish player adapter stages. These owners
coordinate through the same binding contract rather than implementing separate
checkpoint selectors. Acceptance records architecture; the linked work items
record implementation and verification.
