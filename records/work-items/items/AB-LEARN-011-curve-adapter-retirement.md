---
description: Consolidate single fits and learning curves on Recipe execution.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-011
work_status: done
work_kind: build
added: 2026-09-11
tags: domain, hygiene
depends_on: AB-LEARN-005
residual_of: none
residual_items: none
---

# AB-LEARN-011 — Consolidate Recipe execution

## Intent

Use `qi learn run --config` for single fits and comparisons. Retire `qi learn train`,
`qi learn experiment`, LearningPlan and the curve adapter directly. The configured
[runner](../../../src/qi/learning/runs.py) depended back on that adapter
for ordering, provenance and summaries; remove those reverse dependencies.

## Acceptance Criteria

- Only `qi learn run --config` starts a general-purpose configured fit or comparison;
  removed commands fail as unknown commands, without aliases or compatibility wrappers.
- Keep schema-v1's seven sections, RunConfig for concrete trials, and cases × seeds.
  Dataset-embedded reserved corpus remains authoritative and its digest is recorded;
  do not add an expected-corpus field or a separate corpus option.
- Keep the existing Recipe artifact layout for every new run: preserved dataset,
  resolved recipe, manifest, per-trial config/report/checkpoint, and `cases` summary.
  No legacy `plan`, `curve`, or per-trial `size` output aliases.
- Preserve exact source ordering/interleaving, seeded nested subsets, fixed validation
  membership, negative-seed behavior, complete-seed aggregation, device preflight,
  deadlines, partial/failure/interrupt evidence, no overwrite and copy/edit/rerun lineage.
- Move ordering to the config/input-selection implementation, learning source identity
  to a trainer-free provenance module, and keep summaries in the configured runner.
  Update all live Python callers, package checks, CLI tests and maintained guides.
- Verify single-fit weights against direct training under matched inputs/settings,
  curve selections against the pre-migration order, and historical projection checks.
  Run repository and learning checks; preserve original evidence and archived scripts.

## Context and Trade-offs

This supersedes [AB-LEARN-005](AB-LEARN-005-experiment-configs.md)'s temporary
flag-command compatibility decision. Single fits now use a fresh run directory
instead of a user-named checkpoint with sidecars. Migration examples explicitly use
`source-order` for old single fits and `source-interleaved` for curves; Recipe defaults
do not change. Diagnostic subsets use `data.train_size`, not a new diagnostic mode.

The internal trainer, dataset preparation, reference workflow, dedicated study scripts,
checkpoint readers, prepared-data formats and historical migration checks remain.
No snapshot optimizer integration, new training study, source-evidence rewrite,
schema version bump, command generator or new configuration system belongs here.
[AB-LEARN-010](AB-LEARN-010-snapshot-training-protocol.md) remains separate.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | deferred | Survey identified reverse adapter dependencies; migration needs a command/format decision before implementation. |
| 2026-09-11 | User/Codex | deferred | ready | User accepted both recommended boundaries: retire both flag commands and keep the embedded corpus authoritative. Converted the decision item into the bounded build slice. |
| 2026-09-11 | Codex | ready | wip | Begin the accepted direct migration after caller and evidence inventory. |
| 2026-09-11 | Codex | wip | done | Removed both flag commands and the adapter; migrated callers, tests and guides. Isolated repository/learning checks, installed-package reference and historical verification pass. |

## Implementation Ledger

- **Decision:** Both recommendations are locked by the user's “your rec”; the
  interview has no remaining product decisions. Existing Recipe formats and semantics
  govern new runs; historical evidence retains its original shapes and identities.
  **Evidence:** Live CLI/config/runner, caller inventory, and accepted interview.
  **Consequence:** One general training command and execution path, without removing
  the internal optimizer or dedicated scientific protocols.
  **Follow-up:** Implemented and verified below.
  **Review:** ratified.

- **Change:** `config.py` now owns source-interleaved selection;
  [provenance.py](../../../src/qi/learning/provenance.py) owns learning source identity;
  `run_recipe` owns execution and case summaries directly. Removed LearningPlan,
  `experiment.py`, both flag commands and their legacy artifact aliases. Migrated
  live provenance imports, command tests and single-fit/curve examples.
  **Evidence:** Config regressions freeze the pre-migration ordering for seeds 7,
  8 and -1. Integration tests compare full and diagnostic single-fit metadata and
  every checkpoint tensor against direct training, retain completed files through
  deadline/failure/interrupt, and exercise frozen datasets, retry and copied configs.
  **Consequence:** One general training entry point; schema-v1 defaults, the optimizer
  and retained scientific evidence are unchanged.
  **Follow-up:** None within this slice; snapshot training remains AB-LEARN-010.
  **Review:** verified.

## Verification

- `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed in an isolated
  copy of `af88bb6` plus this slice: Ruff, 105 Markdown documents, 19 catalog entries,
  browser type/format checks and production builds, 567 Python tests and five
  JavaScript tests. The optional MPS test was skipped. The shared checkout attempt
  stopped at lint errors in the concurrently developing benchmark module; that work
  was excluded from this slice and preserved.
- `make test-learning` in the same isolated copy: 37 passed. The focused migration
  suite in the shared checkout passed 66 tests. Existing dependency deprecation
  warnings remain; no frontend behavior changed in this slice.
- `scripts/check_reference_package.py` built an sdist and wheel, installed locked
  dependencies outside the checkout, and passed the CPU reference checks, including
  source-identity absence, saved configs, checkpoint reload and expected metrics.
  The build dependency download required network access.
- `scripts/migrate_learning_records.py --check` passed before and after migration:
  12 generalization, five interrupted scaling, nine completed scaling, 63 tuning,
  45 perspective-tuning observations, and two smoke runs; original runs unmodified.
- Read-only Recipe previews for the three historical curves matched all 30 planned
  trial selections, initialization seeds, dataset/corpus digests and validation
  identities against their original manifests. Both new guide JSON examples validate
  as Recipe. These are migration checks, not new training or strength measurements.
