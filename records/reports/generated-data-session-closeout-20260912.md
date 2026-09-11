---
description: Closeout of generated-source mixing, semantic enrichment and scaling, with verified model retention.
scope: generated data session closeout
status: stable
last_update: 2026-09-12
document_class: coordination
---

# Generated-data session closeout

The three studies are complete. Their owners retain the frozen criteria,
results, failures and limits; no further fitting or player-default change is
part of this closeout.

| Study | Comparison fits | Outcome under its original criterion |
| --- | --- | --- |
| [Source mixing](../work-items/items/AB-LEARN-012-generated-source-mixing.md) | 36 | Intervention mixtures improved balanced top-1 agreement; source-specific losses remain |
| [Semantic enrichment](../work-items/items/AB-LEARN-013-semantic-enrichment.md) | 18 | Not supported; retain natural immediate-tag frequencies |
| [Data scaling](../work-items/items/AB-LEARN-014-generated-data-scaling.md) | 30 | All four curves supported scaling; mixture and update-count tradeoffs remain |

Results were committed through `a9a92fa`. The follow-up execution repair is
`ec7613f`: an explicit dataset identity fixed trial-path resolution. Three
completed controls from the first attempt remain retained and charged; all 18
semantic comparison fits were then rerun. The owners and append-only catalog
history preserve this chronology. These results concern teacher imitation on
inspected development positions, not demonstrated playing strength.

## Saved models

The [retention inventory](../../data/experiments/learning/generated-model-retention-20260912.json)
verifies all 89 expected final checkpoints, their saved report hashes, associated
configs and predictions, and checkpoint contents:

- 84 comparison fits, two resource pilots and three retained earlier controls.
- 75 distinct comparison weight states and 75 distinct development move vectors.
  The nine natural semantic controls exactly reproduce the corresponding
  source-mixing `both` models, including weights. Keep all runs as evidence,
  but do not count these repeats as additional models in a correlation study.
- 254119573 bytes of checkpoints across the two retained roots. Each contains
  final weights and metadata; optimizer state and every intermediate update
  were not saved. The files support inference and rescoring, not exact optimizer
  continuation from an arbitrary training step.
- All 89 runs use the same 373 development inputs; none scores any of the 3900
  sealed inputs. Distinct weights are still correlated through shared datasets,
  nested selections, seeds and evaluation positions.

The local, ignored artifact roots are
`artifacts/learning/generated-source-mixing-v1-run3` and
`artifacts/learning/generated-followups-v1`. Committing the inventory does not
back up those weights. No model, failed-attempt evidence, dataset or generated
collection was deleted in this cleanup.

Reproduce the inventory into a fresh output with:

```bash
.venv/bin/python data/experiments/learning/generated-followups-v1/inventory_checkpoints.py \
  --output /tmp/qi-generated-model-retention-recheck.json
```

The [inventory helper](../../data/experiments/learning/generated-followups-v1/inventory_checkpoints.py)
loads the checkpoint containers and hashes their state tensors; it does not run
new inference or engine searches. Earlier independent reload-and-inference
verification remains in each study's verification evidence and the follow-up
`closeout-audit.json`.

## Next question and checkout boundary

The user requested a decision interview for a separate experiment comparing
Pikafish move evaluations with teacher top-1 agreement. The
[campaign](../campaigns/policy-generalization.md) routes this frontier. Preserve
all earlier primary outcomes when assessing another metric. The interview must
resolve whether effectiveness means informative move-error estimates, predictive
validity against game outcomes, or both; metric correlation alone does not settle
playing strength. No next experiment has started.

Five pre-existing generation closeout files were outside this session's edits:
`records/reports/session-handoff-overnight-generation-20260911.md`,
`records/work-items/items/AB-DATA-008-generation-scaling-pilot.md`, and the three
`overnight-generation*20260911.json` history files. They remain outside this
closeout commit. Do not discard or stage them merely to obtain a clean checkout.

## Verification

The completed implementation passed 598 Python tests, one optional MPS skip,
five browser lifecycle tests, lint, documentation/catalog checks and the
production build. All comparison checkpoints were independently reloaded in
the owning studies. This closure adds the complete 89-file retention and
duplicate-state audit; documentation-only conclusions do not rerun training.
Closeout checks passed: helper Ruff checks, `make lint` (including docs, catalog,
TypeScript and formatting), catalog evidence verification and `git diff --check`.
