---
description: Establish the first uv package and replaceable referee boundary without changing game semantics.
scope: backlog item
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-002
work_status: done
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
accepts package-owned dependencies and direct migration. Before extraction, the
core had no qi imports, while Snapshot shared a module with player/application
records. This slice establishes a tested dependency boundary before selecting
a native backend.

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
| 2026-09-21 | GPT-6 | wip | done | Game package and direct migration verified; independent review finding fixed; isolated distributions, full application checks and 90 browser E2E cases passed. |

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
- **2026-09-21 — verification:** Commit `99fa578` records the runtime milestone.
  Independent read-only review found one functional miss: browser E2E setup still
  imported Snapshot from the removed owner. The direct import fix passed all 90
  desktop/mobile Playwright cases. Review found no other blocking issues in the
  referee seam, ordering/history/hash preservation, atomicity, dependency isolation
  or artifact identity. Review also probed fresh-result isolation and invalid
  full-history rejection. Earlier pending implementation reviews are resolved.
  **Review:** ratified.
- **2026-09-21 — verification:** Installed both `qi` and `qi-game` wheels built
  from sdists into a fresh environment outside the checkout, then ran the existing
  CPU learning reference workflow. All 26 verification checks passed, including
  checkpoint reload and legal predictions; installed runtime correctly reports
  unknown checkout identity. Local evidence:
  `artifacts/reference-package-arch-20260921-verified/run/verification.json`.
  The isolated game distribution also passed all 67 tests with network disabled
  after dependency installation. These are macOS ARM CPU checks; Linux is wired
  into CI but was not run locally, and the optional MPS lane was not run.
  **Review:** ratified.
- **2026-09-21 — decision:** Preserve retained experiment scripts with recorded
  source hashes or frozen-layout assumptions. The experiment method now routes
  reproduction through each run's recorded source/lock and distinguishes these
  from migrated supported tooling. No evidence bytes or original results were
  rewritten. Corrected the optional independent-reference setup to install
  `qi-game` in its own environment. ADR-0013 retains decision-time context per the
  immutable-ADR rule; current workspace/lock and implementation status are owned
  by project direction and the package guide. Native execution, player sessions,
  other package splits and the generic experiment task remain explicitly outside
  this completed slice. **Review:** ratified.
