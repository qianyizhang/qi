---
description: Use uv-managed package boundaries and direct migration without default compatibility shims.
scope: architecture decision
status: stable
last_update: 2026-09-21
document_class: coordination
---

# ADR-0013: Separate package dependencies; migrate consumers directly

- **Status**: accepted
- **Last Update**: 2026-09-21

Qi remains one repository with separately declared Python packages managed by uv.
Packages own dependency declarations in their own `pyproject.toml`; optional
implementations and heavy resources load on demand. Refactoring may break internal
APIs and commands: migrate the repo's consumers directly, without default shims.

## Context

Independent experiments need bounded dependencies and test surfaces. The current
single distribution includes application dependencies and optional learning/data
extras. The user explicitly chose package-owned TOML declarations and lazy loading,
and confirmed there are no external downstream consumers to preserve. See
[AB-ARCH-001](../../records/work-items/items/AB-ARCH-001-modular-runtime.md).

## Considered Options

- **One distribution with only import conventions/extras** — insufficient for
  the requested package-owned dependency boundaries.
- **Separate repositories, releases and services** — adds coordination beyond
  the current need for local development independence.
- **One repository with uv-managed packages and direct consumer migration** —
  selected; provides explicit dependency ownership without promising independent
  release schedules or maintaining obsolete interfaces.

## Consequences

Create packages around useful ownership/dependency boundaries; avoid speculative
packages for individual helpers. Do not load every implementation through package
initializers or capability discovery. Lazy loading must not disguise undeclared
dependencies or silently substitute a different implementation.

Historical evidence, format interpretation and replay identities remain preserved.
Where a format change requires migration/backfill, make that a separate explicit
operation with source lineage; do not rewrite original evidence or fabricate
unknown metadata. Runtime compatibility wrappers are not the default migration
strategy. Exact package layout and shared-versus-separate uv lockfiles remain
open in the decision interview; they are not implied by per-package declarations.

This is an accepted destination. The current single-package layout remains the
implemented state until bounded migration work is authorized and completed.
