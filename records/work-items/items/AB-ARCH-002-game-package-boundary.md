---
description: Establish the first uv package and replaceable referee boundary without changing game semantics.
scope: backlog item
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-002
work_status: wip
work_kind: build
added: 2026-09-21
tags: domain, architecture, packaging
depends_on: AB-ARCH-001
residual_of: none
residual_items: none
---

# AB-ARCH-002 — Establish the game package boundary

## Intent

Deliver the first useful slice of the accepted
[modular redesign](AB-ARCH-001-modular-runtime.md): a uv-managed game package with
independent dependency ownership and a replaceable referee seam backed by the
current Python implementation. Native execution and other package boundaries
remain subsequent slices.

## Acceptance Criteria

- Establish a uv workspace/shared lock for supported code and a game package
  with its own project/dependency declaration. Keep package creation scoped to
  this slice; do not scaffold the complete destination tree.
- Separate game snapshot/replay interchange from application/player session
  records. Game contracts and reference behavior must import no players, Torch,
  API/frontend, training or evaluation implementations.
- Introduce the smallest referee substitution boundary used by an existing
  gameplay or replay operation. Demonstrate explicit backend injection with the
  current reference implementation; do not add unused generic game abstractions.
- Migrate affected internal imports/consumers directly, including CLI/HTTP and
  tests as needed. Add no default old-path reexports or compatibility shims.
- Preserve existing snapshot interpretation, ordered legal actions, state hashes,
  invalid-action atomicity and outcomes. Retain pre-change fixtures and compare
  existing replay/terminal cases across the extracted boundary. Original evidence
  remains unchanged; explicit artifact migration is separate work if needed.
- Verify the game package in an isolated environment with only its declared
  runtime/test dependencies, and test the forbidden import boundaries. Run
  affected consumer checks and the cross-cutting `make check` gate. Document
  any unrelated baseline failures separately.
- Update current implementation paths and commands in the owning guides/bindings;
  keep accepted future directions clearly distinguished from implemented behavior.

## Context and Trade-offs

[ADR-0012](../../../docs/adr/0012-replaceable-game-execution.md) accepts replaceable
execution; [ADR-0013](../../../docs/adr/0013-modular-packages-and-direct-migration.md)
accepts package-owned dependencies and direct migration. The core currently has
no qi imports, while Snapshot shares a module with player/application records.
This slice tests an actual dependency boundary before selecting a native backend.

Native-library/language selection, performance claims, model/data package moves,
the general experiment runner, API/FE redesign and server implementation are
outside this slice. Possible serving remains a low-fidelity direction; it must
not introduce speculative queues, RPC interfaces or deployment machinery here.
Exact package names and local interface signatures are implementation choices
within the accepted ownership constraints.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | ready | Architecture interview settled the governing boundaries; first build slice prepared without starting runtime changes. |
| 2026-09-21 | GPT-6 | ready | wip | User authorized implementation, milestone commits and a final independent review; baseline make check passed. |

## Implementation Ledger

- **2026-09-21 — decision:** Extract `qi-game` with pure game DTOs, shared identity
  types, a two-operation structural referee protocol and the explicit Python
  reference. CLI/HTTP game operations use the seam; Python search/data consumers
  reconstruct reference state explicitly. No legacy paths or Snapshot method
  remain. Detailed serving/native design stays deferred. **Review:** pending.
- **2026-09-21 — verification:** Before runtime changes, `make check` passed
  752 Python tests (one optional skip), five browser unit tests and lint/type/build
  checks. Commit `58e6143` captures approved architecture and scope. Frozen referee
  fixtures record that commit and source hashes; follow-up verification compares
  against those values without regenerating expectations. **Review:** not-required.
- **2026-09-21 — verification:** Extracted-package milestone: `make check` passed
  779 Python tests (one optional MPS skip), five browser tests, Ruff, 134-document
  hygiene, experiment catalog, OpenAPI/TypeScript agreement and production builds.
  `scripts/check_game_package.py` built an sdist then wheel, installed only the
  game package's declared dependencies outside the checkout, verified application
  and ML dependencies absent, and passed 67 package tests. A structural comparison
  to `58e6143` found all 16 original game function/class ASTs unchanged. Independent
  review and the installed learning-package integration remain next. **Review:** pending.
