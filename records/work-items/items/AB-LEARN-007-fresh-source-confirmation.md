---
description: Confirm fixed-label source coverage on fresh generation blocks and untouched holdouts.
scope: backlog item
status: experimental
last_update: 2026-09-09
document_class: work_record
work_id: AB-LEARN-007
work_status: done
work_kind: research
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-006
residual_of: none
residual_items: none
---

# AB-LEARN-007 — Fresh-source confirmation

## Intent

Test whether broader source coverage improves fixed-budget teacher imitation on
fresh data. Also expose the existing continuation modes through a complete saved
dataset preparation config, keeping generation separate from training.

## Acceptance Criteria

- Lock the comparison before measuring holdout predictions; preserve all runs.
- Three fresh generation seeds (1201/2201/3201), 512 random games each under the
  explicit pre-fit pool amendment below (original attempt: 288), 32 plies,
  up to 16 labels/game, original v1 generator, Pikafish 1000 nodes/depth 3.
  Each block has its own untouched validation split, identical within its pair.
  Exclude observations from the prior policy datasets listed in the protocol and cross-block duplicates
  before selection. Reject duplicate full trajectories across old/new sources.
- In each block select 192 full eligible training games deterministically; compare
  its first 48 × 16 labels with 192 × 4 labels under exact global ply matching.
  Preserve shortfalls as separate attempts; never silently relax quotas or eligibility.
- Run all 18 fixed fits: three blocks × two cases × seeds 7/17/27; CPU, one thread,
  64-unit policy, float32, full-batch Adam .01, 200 updates, source-order inputs.
- Primary decision rule: retain broader coverage as a confirmed working choice
  for this regime if every block's seed-mean agreement delta is positive.
  Otherwise record nonconfirmation; no tuning, retries or checkpoint selection
  based on results. Cross-entropy is secondary. Report block and seed variation
  descriptively, without calling nine fits independent datasets or claiming strength.
- Generation: at most 1800 seconds/block, four existing bounded label workers;
  log completed teacher answers even if generation fails. Profile the first fit
  once; remaining allowance is 3× its end-to-end time, bounded to 60–600 seconds.
- Save generation settings, teacher hashes, data exclusions, exact selections,
  full training configs, source snapshots and compact results. Run `make check`
  and targeted config/training integration tests for changed behavior.

## Context and Trade-offs

The earlier holdout was inspected. This replication uses independent generation
seeds and block-specific fresh holdouts; paired cases always share the same test
inputs. Holdout differences across blocks are another source of variation.
Selection still requires sixteen eligible labels and uses constrained ply
matching. This does not remove that conditioning or test every sampling strategy.

Keep the original v1 random generator for the scientific comparison to avoid
confounding source coverage with a generator migration. The new preparation
config exercises `continuations-v2` separately with a bounded real-engine pilot.
Teacher-guided play changes trajectory distribution; teacher supervision supplies
preferences, not referee-proven ground truth. Training Data owns both operations
and assembly; the trainer continues to consume a frozen dataset.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User authorized trying the fresh confirmation and folding generation modes into configuration. Protocol locked before generation or fitting. |
| 2026-09-09 | Codex | wip | done | Configured preparation verified; amended confirmation completed all eighteen fixed fits and passed its predeclared rule. Original preparation shortfall remains separate evidence. |

## Implementation Ledger

### 2026-09-09 — finding: fresh confirmation supports broader source coverage

All eighteen fits completed 200 updates. Average over initialization seeds and
then equally over the three source blocks:

| Case | Training agreement | Fresh held-out agreement | Fresh held-out cross-entropy |
| --- | --- | --- | --- |
| 48 games × 16 labels | 100% | 12.91% | 13.20 |
| 192 games × 4 labels | 100% | 14.58% | 11.58 |

| Source block | Held-out positions | Agreement delta (pp) | Initialization std of delta (pp) | Cross-entropy delta |
| --- | --- | --- | --- | --- |
| 0 | 2013 | +1.37 | 0.19 | −1.59 |
| 1 | 2011 | +0.86 | 0.55 | −1.28 |
| 2 | 2013 | +2.78 | 0.28 | −1.97 |

- Evidence: [complete results](../../../data/experiments/learning/history/source-coverage-confirmation-v2.json),
  [locked amended protocol](../../../data/experiments/learning/source-coverage-confirmation-v2/protocol.json),
  and original datasets, configs, reports and checkpoints under
  `artifacts/learning/source-coverage-confirmation-v2/`.
- Decision: the predeclared rule passes: every source block has a positive
  seed-mean agreement delta. All nine paired agreement deltas are positive;
  all nine cross-entropy deltas are negative. Average gain is **1.67 percentage
  points**, with a **0.99 pp** sample standard deviation across block means.
  Cross-entropy falls by 1.61 on average. These are descriptive variations,
  not nine independent datasets or a confidence interval.
- Consequence: retain broader source coverage as the working sampling choice
  for comparable fixed-label, early-random-play teacher-imitation experiments.
  Both cases still memorize training labels and generalize weakly. This does
  not establish playing strength, calibrated probabilities or an optimal four
  labels/game policy. Fresh absolute scores cannot be compared directly with
  the earlier inspected-holdout scores as one benchmark.
- Limits: one fixed shallow teacher and small model; exact sixteen-label source
  eligibility; constrained ply matching; three independent generation seeds
  with separate holdouts. Candidate-pool size was explicitly amended after a
  data-only shortfall and before predictions. The additional pilot-overlap audit
  below identifies one previously used training observation, no held-out overlap.
- Verification: independent raw-JSON arithmetic reproduced the block and overall
  agreement deltas. Every executed dataset and input list matches its prepared
  selection, all checkpoint hashes match saved bytes, all reload checks agree,
  and all fits record the same source identity. `verification-runs.json` retains
  the separate checker result. The final source passed `make check` (373 Python
  tests, one opt-in GPU skip, browser tests/build and lint/docs); targeted config,
  training-config and selection checks passed twenty tests.
- Follow-up: use the broader working choice in the next comparable experiment;
  revisit on changed teacher, phase distribution, label budget or representation.
  No additional training experiment is scheduled by this result.
- Review: not-required; predeclared decision rule and independent saved-artifact verification.

### 2026-09-09 — decision: confirmation protocol and configuration boundary

- Evidence: AB-LEARN-006 and the policy-generalization campaign recommend fresh
  confirmation; GenerationRecipe already separates move choice from supervision.
- Consequence: keep the scientific comparison fixed; add a file-based preparation
  entry point around existing generation and assembly, not generation in the trainer.
- Follow-up: execute the declared matrix and record all results or explicit failure.
- Review: not-required; user authorized bounded execution and routine implementation.

### 2026-09-09 — verification: configured preparation

- Added `qi data prepare --config --output` around existing continuation generation
  and frozen assembly. Resolved configs pin corpus, engine and network content;
  optional actor-teacher settings remain independent of supervision.
- The real-engine `preparation-config-pilot-v1` completed with sixteen reusable
  examples and eight retained examples: two per mode and split. Its tracked
  recipe is `data/experiments/learning/preparation-two-mode-v1.json`; detailed
  evidence stays under `artifacts/learning/preparation-config-pilot-v1/`.
  This is pipeline evidence, not a strength or imitation-improvement comparison.
- Verification: seven targeted tests cover both modes, copied configs, separate
  actor budgets, hash mismatches, partial generation, quota shortfall and CLI
  failure behavior. `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed
  373 Python tests (one opt-in GPU skip), browser lifecycle tests/build and lint/docs.
  The existing environment was used because automatic uv build dependency fetching
  was unavailable in the sandbox; no dependency or lockfile change was required.
- Consequence: generation is explicit and reproducible without becoming a trainer
  side effect. “Dataset preparation”, “generation mode” and “teacher supervision”
  are recorded in the glossary and module guide; avoid unqualified “GT generation”.
- Follow-up: complete the separately locked scientific confirmation.
- Review: not-required; hermetic tests and local pinned-teacher execution.

### 2026-09-09 — deviation: data-only shortfall and explicit pool amendment

- Original attempt retained one complete 288-game block and 2540 successful
  teacher answers from the interrupted second block. Excluding 83 prior inputs
  left only 155 full sixteen-label training sources in block 0, below 192.
  Stopped the attempt before any fit; original protocol, raw data and partial
  answers remain unchanged. Compact evidence:
  `data/experiments/learning/history/source-coverage-confirmation-shortfall.json`.
- Before commissioning new labels, ran the existing v1 generator with a
  feasibility-only placeholder provider. Placeholder targets were discarded;
  only source/input identities, counts and matched selections were retained.
  No engine query, model prediction or holdout metric entered this audit.
- A 512-game pool per seed admits 253/285/254 full eligible sources after both
  prior-input and cross-block exclusions. Exact 48 × 16 and 192 × 4 matched
  selections are feasible in all three blocks. Full evidence and original audit
  script: `artifacts/learning/source-coverage-confirmation-feasibility/`;
  reusable audit command: `scripts/audit_fresh_coverage.py`.
- Explicit protocol amendment: new attempt `source-coverage-confirmation-v2`
  increases only candidate games per block from 288 to 512. Same generation
  seeds, teacher, exclusions, exact label budgets, selection/matching seeds,
  training recipe and decision rule. The existing per-block 1800-second bound
  remains. Changing the v1 game count rerolls trajectories; no prior answer is
  silently reused. Pins require actual inputs and selected cases to match the
  prelabel audit before fitting. Both protocols are retained; this is a declared
  data-feasibility amendment, not a result-based retry or relaxed quota.
- Consequence: the original attempt is a preparation shortfall, never a completed
  scientific comparison. The amended attempt is locked before any model results.
- Follow-up: execute the amended protocol once; preserve any subsequent failure.
- Review: not-required; within the user's authorized trial, before outcome inspection.

### 2026-09-09 — finding: additional pilot-overlap audit

- The locked exclusion list covers the prior imitation/generalization/tuning/scaling
  datasets. Separately checked all fresh candidate inputs against the three small
  Training Data/configuration pilots. Two pilots have no overlap; the earlier
  `training-data-pilot-v2` shares one block-1 training input. It is not a held-out
  input. Keep the locked selection and disclose this limit rather than claiming
  every training observation is new across every repository experiment.
- Consequence: fresh source trajectories and untouched held-out measurement remain
  the confirmation boundary; the five named prior-study exclusions are exact.
- Follow-up: preserve this distinction in the final evidence.
- Review: not-required; data-only audit before fitting.

### 2026-09-09 — verification: amended data and execution lock

- All three 512-game blocks completed: 1536 source games and 24576 raw labels,
  about 1264 seconds of generation in total. Actual candidate identities and both
  case selections match the prelabel audit exactly.
- Frozen six datasets and all eighteen individual configs before fitting.
  A separate raw-JSON verifier confirmed 768 distinct training inputs per case,
  exact 48 × 16 / 192 × 4 source quotas, unchanged labels, matched ply histograms,
  192 shared inputs within each pair, and no selected-input overlap across blocks
  or with the protocol's named prior datasets. Block holdouts have 2013/2011/2013
  positions (6037 total). Detailed proof: `verification-data.json` under the
  amended artifact directory; its independent verifier is retained there too.
- First fit completed 200 updates in 26.28 seconds end to end and counts once
  in the matrix. The remaining seventeen use 78.84-second individual allowances.
  No metric was used to alter training settings or select checkpoints.
- Six full replay recipes live under
  `data/experiments/learning/source-coverage-confirmation-v2/`; original executed
  configs retain the first fit's 600-second profiling allowance. Source copies,
  dependency files and source identities are retained for generation and training;
  runs truthfully record an uncommitted source tree rather than claiming Git alone
  reconstructs the code.
- Config pilot additionally completed a thirty-update configured fit with equal
  checkpoint-reload predictions and the original dataset manifest identity.
- Follow-up: finish and independently verify all eighteen fits before synthesis.
- Review: not-required; data integrity and complete-config checks before results.
