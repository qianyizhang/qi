---
description: Prove the accepted Training Data boundary with random and teacher-guided sources and frozen composition.
scope: backlog item
status: stable
last_update: 2026-09-09
document_class: work_record
work_id: AB-DATA-002
work_status: done
work_kind: build
added: 2026-09-09
tags: domain
depends_on: AB-DATA-001
residual_of: none
residual_items: none
---

# AB-DATA-002 — First Training Data slice

## Intent

Prove [ADR-0004](../../../docs/adr/0004-training-data-bounded-context.md) and the
[core model](../../../docs/models.md) with executable composition rather than
empty interfaces. Implemented in `src/qi/training_data/`; the module guide owns executable contracts.

## Acceptance Criteria

- Extract existing random generation without changing its seeded selection,
  teacher labels, split/exclusion behavior or existing artifact interpretation.
- Add teacher-guided continuations from named replay-backed starting positions;
  keep actor choice independent of supervision and validate any analysis reuse.
- Make phase, theme, optional objective and sampling window addressable under
  versioned policies. Document the initial phase classifier and example fixtures;
  do not treat ply ranges as semantic phases or claim general forced-win proofs.
- Retain reusable examples and materialize a reproducible two-mode mixture with
  state/observation/example/manifest fingerprints, exact quota accounting,
  source-family isolation and explicit incomplete status.
- Preserve one target contract and teacher recipe per dataset. Reject ambiguous
  supervision and source/observation leakage; retain contributing provenance.
- Demonstrate trainer consumption and required slice coverage/results using
  a fixed held-out recipe, with core contract tests and a bounded local pilot.

## Context and Trade-offs

Package layout, canonical serialization details, concrete classifier thresholds
and pilot mixture counts must be documented during implementation. Existing
fields and dataset artifacts need an explicit compatibility/migration path.
Learner-driven generation, recorded-game ingestion, diagram-only states,
heterogeneous supervision, dynamic epoch mixtures and persistent teacher sessions
are later extensions, not required to prove this slice.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | ready | First implementation slice identified at design closeout; no execution started. |
| 2026-09-09 | Codex | ready | wip | User authorized implementation; extracting compatibility API and building executable composition. |
| 2026-09-09 | Codex | wip | done | Contract/integration checks and real CPU/MPS phase-filtered pilot passed; all quotas and checkpoint reload verified. |

## Implementation Ledger

- Extracted `legacy.py` byte-for-byte from the prior generator; `qi.learning.data`
  re-exports its API. Existing seeded selection, teacher labels, splits, exclusions
  and v1 digests retain their interpretation.
- Added replay-backed starts, independent actors/supervisors, bounded shared
  continuations, validated teacher-analysis reuse, phase/window/theme/objective
  selection, reusable examples and deterministic frozen composition.
- Library and manifest validation enforce exact quotas, contributing lineage,
  family/observation isolation, reserved history exclusions and target consistency.
  Partial work is saved explicitly; incomplete requested mixtures cannot train.
- `qi data generate`, `assemble` and `train` expose the new format. The shared
  trainer accepts it and reports quota and diagnostic slices. Checkpoints carry
  a separate manifest fingerprint and retain CPU inference/reload compatibility.
- [Module guide](../../../src/qi/training_data/README.md) documents serialization,
  phase thresholds, overlap policy, budgets, failure behavior and compatibility.
  [Pilot script](../../../scripts/training_data_pilot.py) is the reproducible local
  recipe example. No external services or persistent teacher sessions were added.

### Pilot evidence and what changed

Local evidence is in `artifacts/learning/training-data-pilot-v1/` and
`artifacts/learning/training-data-pilot-v2/`. These generated libraries, JSON
recipes, manifests, identity indexes, coverage, weights and reports are ignored
artifacts; this record retains the findings and script needed to reproduce them.

The first pilot generated 95 examples in 23.57 seconds and selected 36 examples
under origin-theme quotas. All quotas passed, but the actual training slice had
**zero opening positions**: continuations from opening starts had moved into the
middlegame. This demonstrated why origin themes and semantic phases are separate.

The second pilot filters the sampler and buckets by semantic phase. It generated
69 reusable examples in 20.73 seconds and retained 28, filling all 12 mode/phase/
split buckets. Each split contains 2 opening, 6 middlegame and 6 endgame examples,
with both random and teacher-guided sources represented. Validation families and
mixture are frozen. Manifest fingerprint:
`91c16401c83bff4fd9ea323fc23f91a8ee55e700fb5f377da33268f1ab43ab31`.

Both CPU and MPS completed 30 updates on that same manifest, produced legal moves
on all 28 selected positions, and reproduced their predictions after CPU reload.
Training agreement was 14/14; held-out agreement was 1/14 for both devices. This
is a functioning-data-path check, not evidence of improved generalization or game
strength. One tiny run took 0.038 seconds of CPU optimization and 0.146 seconds
on MPS; those smoke timings do not replace the earlier device benchmark.

### Validation

- `make check` passed on the shared checkout: 345 Python tests, one opt-in GPU
  test skipped, three web tests, lint/docs/type checks and production browser build.
  Two existing FastAPI/Starlette deprecation warnings remain.
- Used `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache` and the existing virtualenv on
  PATH after a dependency resync attempted a sandbox-blocked package-index fetch.
  Actual CPU and MPS training were checked separately using the frozen pilot.
- Seventeen new data-contract tests and two integration tests cover identities,
  quota/manifest tampering, source families, observation/target conflicts, reserved
  prefixes, actor reuse, deadlines, partial failures, phase policies and objectives.
- The legacy implementation was compared byte-for-byte with its pre-extraction
  version. Concurrent learning-configuration work was preserved and kept outside
  this change's commit scope.
- Exported HEAD plus only the staged Training Data patch into an isolated temporary
  checkout: all 68 Markdown files passed governance checks; 327 Python tests passed
  with one opt-in GPU test skipped. This verifies the commit without depending on
  the concurrent configuration changes.
- Weekly account usage remained at 9%, below the requested 25% soft stop.
