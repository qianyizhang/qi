---
description: Add minimal declarative training recipes, copyable run configs and retrospective learning records.
scope: backlog item
status: stable
last_update: 2026-09-09
document_class: work_record
work_id: AB-LEARN-005
work_status: done
work_kind: build
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-004
residual_of: none
residual_items: none
---

# AB-LEARN-005 — Experiment configs and learning records

## Intent

Make training settings explicit and reusable, and preserve findings across small
experiments without building a general experiment platform.

## Acceptance Criteria

- Seven validated config sections; prepared datasets only; no scientific CLI
  overrides in config mode. Preview needs no trainer and writes nothing.
- Every configured run saves its full recipe and concrete started-trial configs,
  reusable after copying and editing; existing training behavior stays shared.
- Named cases × seeds remain a provisional comparison shape. Partial/failure
  evidence, no overwrite, and completed-seed aggregation remain explicit.
- Reconstruct existing experiment settings and preserve original evidence,
  unknowns, prototype limitations, and interrupted executions honestly.
- Add a short experiment method and evidence synthesis; verify code behavior,
  migration projections, and repository checks.

## Context and Trade-offs

The user accepted prepared dataset input, authoritative config files, and a full
config artifact that can be copied and tweaked. Cases × seeds is an initial shape,
open to later refactoring. No new curriculum, optimizer, model architecture,
parameter sweep, or fingerprint registry is included. Existing artifact identity
and checkpoint contracts remain in force.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User confirmed the three boundaries and requested implementation. |
| 2026-09-09 | Codex | wip | done | Config execution, copy/edit/rerun and retrospective migration verified; shared gate caveat recorded below. |

## Implementation Ledger

### 2026-09-09 — decision

- Evidence: accepted interview answers: prepared datasets, config authority with
  full re-dumps, provisional named cases × seeds.
- Consequence: `qi learn run --config` has only output and preview options;
  existing flag-only commands remain compatible. Relative data paths resolve
  against the config; saved configured runs use their preserved dataset copy.
- Follow-up: verify copy/edit/rerun parity and additive historical projections.
- Review: user-ratified boundaries; local implementation review completed below.

### 2026-09-09 — verification and migration

- Evidence: validation rejects unsupported fields and CLI overrides; cases expand
  independently with fixed held-out membership. Tests verify bit-identical weights
  against direct training, saved-config copy/edit/CLI execution, no overwrite and
  retained failure/deadline/interrupt evidence. Complete frozen Training Data
  datasets preserve manifest identity and slice results; shortfalls are rejected.
- Migration: preserved two smoke runs, 12 generalization fits, five interrupted
  and nine completed data-scaling fits, and 108 checkpoint observations from
  continuous tuning fits. Separate records preserve the locked final test and
  device/framework benchmarks. Historical scripts are copied byte-for-byte;
  original artifacts were not changed. Migration `--check` passed. All three
  reconstructed curve previews match original dataset identities and exact
  training/held-out selections.
- Verification: 341 Python tests passed, one opt-in GPU skip; three browser tests,
  browser type/format checks and production build passed. The learning lane passed
  21 tests and the explicit Metal lane passed outside the sandbox. Config/preview
  imports do not load torch. Ruff lint/format and `git diff --check` passed.
- Gate caveat: `make check` stopped on the concurrent AB-DATA-002 record's missing
  transition to `wip`; remaining checks were run separately. This work's docs had
  no violations. Checks used the existing environment with `UV_NO_SYNC=1` after
  sandboxed package-index refresh failed; this slice adds no dependencies.
- Consequence: config artifacts and historical records are usable. No scientific
  experiment was launched. Cases × seeds remains provisional; unsupported
  prototype settings stay historical.
- Follow-up: the concurrent Training Data owner should clear its status-history
  mismatch and rerun the aggregate gate.
- Review: local implementation/contract review and artifact comparison; no separate reviewer agent.

### 2026-09-09 — final gate and automatic lineage

- Verification: the concurrent documentation mismatch was corrected; aggregate
  `make check` subsequently passed with 341 Python tests, one opt-in GPU skip,
  browser tests/build and all lint/docs checks. This supersedes the gate caveat
  and follow-up above.
- Refinement: each saved config carries its `origin_config` path. Copying it and
  changing only one scientific parameter automatically records the original
  artifact as the next run's `derived_from`; users need not edit lineage fields.
  The final CLI copy/edit test proves this path. After that metadata refinement,
  all 21 learning integration tests and 23 recipe/plan unit tests passed again,
  along with focused lint, docs and retrospective-projection checks.
- Consequence: the requested scaffold and migration are complete. No additional
  experiment settings need locking before using the interface.
- Review: verified locally.

### 2026-09-09 — independent review and cleanup

- Review: an independent read-only reviewer reproduced four issues: case-only
  names could overwrite configs on macOS; config conversion rejected previously
  valid legacy seeds; migrated ancestry paths were ambiguous; failed device
  preflight left a sidecar that blocked retry.
- Fixes: reject case-insensitive name collisions, preserve legacy seed behavior,
  resolve ancestry relative to the config, and finish device validation before
  writing single-fit artifacts. Sidecars use the entire checkpoint filename so
  `.pt` and `.pth` outputs do not collide. Equivalent PyTorch seed aliases cannot
  be counted as independent initializations.
- Cleanup: replace the duplicated legacy execution loop and aggregation with
  adapters over the configured executor and summaries. Preserve legacy curve
  fields and validated source selection. Historical projections now also retain
  recorded interruption errors, elapsed time and already-known script/data hashes.
- Verification: all 23 learning integration tests and 26 config/plan tests passed,
  including the new collision, negative-seed, ancestry and preflight-retry cases.
  Migration projections still match their original sources.
- Follow-up: final independent fix review and aggregate checks before commit.
- Review: original findings addressed; fix review pending.

### 2026-09-09 — independent fixes accepted

- Evidence: the reviewer independently confirmed collision rejection, resolved
  ancestry, and bit-identical legacy negative-subset execution versus a saved
  recipe rerun. Migration checks preserve interruptions and existing identities.
- Verification: final aggregate `make check` passed with 350 Python tests, one
  opt-in GPU skip, browser tests/build and lint/docs gates. The bounded follow-up
  review found no remaining commit blocker.
- Consequence: fixes and shared-executor cleanup are ready to commit. The
  source-coverage experiment investigation follows this commit separately.
- Review: independently reviewed; all reported issues addressed.
