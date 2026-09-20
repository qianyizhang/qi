---
description: Establish the first uv package and replaceable referee boundary without changing game semantics.
scope: backlog item
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-002
work_status: ready
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
current Python implementation. This is prepared implementation scope; no runtime
work has started.

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

## Implementation Ledger

No implementation events yet.
