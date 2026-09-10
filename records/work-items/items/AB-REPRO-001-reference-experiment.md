---
description: Make a tiny reference experiment reproducible in a clean CPU environment and CI.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-REPRO-001
work_status: wip
work_kind: build
added: 2026-09-10
tags: hygiene
depends_on: none
residual_of: none
residual_items: none
---

# AB-REPRO-001 — Reference experiment and clean CI

## Intent

Provide one small, self-contained reproduction path that does not depend on local
ignored artifacts, a teacher installation or a GPU.

## Acceptance Criteria

- Check in a tiny frozen fixture dataset, resolved CPU recipe and documented
  command that creates fresh artifacts and verifies their identities and metrics.
- Declare expected outputs and numerical tolerances; avoid unsupported claims of
  identical weights or timings across platforms.
- Run repository checks on clean Linux and add a bounded CPU-learning CI lane,
  requiring no network or external service after dependency installation.
- Exercise the distributed package in a clean environment, with explicit
  unavailable checkout provenance where appropriate.

## Context and Trade-offs

[Experiment method](../../../docs/experiments.md) owns lineage and evidence rules;
the [trainer guide](../../../src/qi/learning/README.md) owns execution semantics.
Existing local checks do not substitute for a clean installation/reproduction
lane. The fixture proves workflow behavior, not playing strength.

## Accepted Scope

- Ship a tiny synthetic frozen mixture, full CPU recipe and expected metrics.
  Reuse the existing runner through `qi learn reference --output <fresh-directory>`;
  retain artifacts and `verification.json`, with nonzero exit on failure.
- Verify exact inputs/scientific settings, completed training, legal predictions,
  checkpoint consistency and approximately matching metrics. Paths, weights and
  timings need not match across machines.
- Calibrate on macOS CPU only. Allow practical platform variation; no calibration
  matrix or generalized verification framework.
- Exercise a wheel built from the sdist outside the checkout, and add
  Linux/Python 3.12 jobs for repository checks and learning/package checks.

## Calibration

Three separate macOS 26.6.2 arm64 processes, Python 3.12.13, PyTorch 2.10.0,
seed 7, CPU/one thread, 100 updates, eight training and four validation positions:

| Metric | All three runs |
| --- | --- |
| Initial loss | 3.7770369052886963 |
| Final / training cross-entropy | 0.0 |
| Training agreement | 8/8 |
| Validation cross-entropy | 1.321690559387207 |
| Validation agreement | 3/4 |

Optimization took 0.0804–0.0886 seconds (not whole-command duration or a performance
guarantee). Loss tolerances use max(0.01 absolute, 5% relative); training agreement
must remain 8/8, validation agreement permits one-position variation. Calibration
metrics and environment are retained in
[`expected.json`](../../../src/qi/learning/reference_data/expected.json).
Full local runs are under `artifacts/learning/reference-calibration-v1/mac-{1,2,3}/`.
These observations establish the Mac baseline only. Tolerances are a practical
choice, not measured cross-platform bounds or statistical confidence intervals.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture larger reproducibility work from repository reviews. |
| 2026-09-10 | User + Codex | deferred | wip | Accepted the small reference and Mac-only calibration; implementation started. |

## Implementation Ledger

Reference bundle, generator, verifier, package smoke script and CI workflow added.

- `UV_CACHE_DIR=.cache/uv make check`: passed; 439 Python tests, one optional MPS
  skip, five browser lifecycle tests, lint/docs/type checks and production builds.
  Log: `artifacts/reference-make-check.log`.
- After adding the CLI metric-failure test, `UV_CACHE_DIR=.cache/uv make test-learning`:
  all 38 tests passed. Log: `artifacts/reference-test-learning.log`.
- `scripts/check_reference_package.py --output artifacts/reference-package-mac-v3`:
  sdist -> wheel -> fresh virtual environment passed outside the checkout with
  unavailable source/Git provenance. The installed reference remeasured its
  checkpoint and passed every check. Evidence:
  `artifacts/reference-package-mac-v3/run/verification.json` and
  `artifacts/reference-package-mac-v3.log`.
- Fixture regeneration matches the frozen dataset; focused tests reject changed
  configs, metric failures, corrupt checkpoints, missing datasets and incomplete
  summaries. A failed CLI verification retains the checkpoint and diagnostics;
  rerunning into an existing directory preserves its contents.

Remaining acceptance: execute the new workflow on clean Linux. This macOS session
has not run GitHub Actions; `wip` is retained until that CI evidence exists. No
additional cross-platform calibration is required by the accepted scope.

### Independent review and cleanup

The independent review found two defects, both fixed and rechecked:

- Both CI jobs used an unpublished `setup-uv@v10` tag. They now pin the verified
  v10.0.1 commit; upstream no longer publishes major/minor tags.
- Reverification could reuse a cached policy after its checkpoint file changed.
  The verifier now hashes current file bytes before using the inference cache.
  A same-path corruption regression verifies the failed result.

Simplified the preview test, suppressed the package check's redundant requirements
dump, and corrected the learning-extra installation hint. Supported legacy training
commands remain in use; this scope contained no deprecated implementation to remove.

Final validation: `make check` passed with 441 Python tests, one optional MPS skip,
five browser tests, lint/docs/type checks and both production builds. The fresh
sdist/wheel package check also passed offline using cached dependencies, with all
26 reference checks passing and checkout provenance unavailable. Evidence:
`artifacts/reference-review-check.log`, `artifacts/reference-package-review.log`,
and `artifacts/reference-package-review/run/verification.json`.
