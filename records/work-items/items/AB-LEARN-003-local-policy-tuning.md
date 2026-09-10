---
description: Test bounded local policy improvements and verify selected changes on fresh held-out games.
scope: backlog item
status: stable
last_update: 2026-09-10
document_class: work_record
work_id: AB-LEARN-003
work_status: done
work_kind: research
added: 2026-09-08
tags: domain
depends_on: AB-LEARN-002
residual_of: none
residual_items: none
---

# AB-LEARN-003 — Local policy tuning

## Intent

Improve the small local policy with controlled, affordable experiments. The user
allows training time, strategy and modest model-size changes, with sensible
commits and a soft stop at 25% weekly Codex usage or diminishing returns.

## Acceptance Criteria

- Preserve the completed pipeline and its baseline evidence in a commit.
- Record configurations, fixed data/splits, seeds, real work, and both successful
  and unsuccessful results. Existing validation becomes tuning data once used
  for configuration selection; final claims use fresh source games.
- Keep teacher/referee/player boundaries and local CPU/MPS scale. Promote only
  verified useful changes; preserve compatibility or explicitly version new models.
- Check weekly usage between substantial stages; stop by the requested threshold
  or when further experiments have no meaningful supported gain.

## Context and Trade-offs

Initial 768-example policy: 20.19% mean validation agreement, 100% training
agreement, cross-entropy 10.987 versus uniform-legal 3.664. This suggests testing
confidence control and learning dynamics before adding more infrastructure.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized autonomous bounded optimization and progress commits |
| 2026-09-09 | Codex | wip | done | Locked candidates failed to improve fresh-test move agreement; stopped at diminishing returns |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: pipeline commit `2506bf3`; weekly Codex usage checked at 6%.
- Consequence: compare learning rate, duration, regularization and hidden widths
  under fixed data and seeds; reserve fresh held-out games for the selected recipe.
- Follow-up: record results and promote only a useful verified slice.
- Review: not-required.

### 2026-09-08 — exploratory findings and final-test lock

- Evidence: 12 configurations across three initialization seeds, with checkpoints
  at 50/200/800 updates, produced 108 tuning observations. The original 768-example
  training set and 251-example tuning set stayed fixed. Data-size claims from
  AB-LEARN-002 remain historical; this split now serves configuration selection.
- Findings: lowering learning rate from 0.01 to 0.003 gave 21.25% tuning agreement
  at 200 updates versus 20.19% baseline. Extending to 800 updates gave no further
  top-1 gain and worsened cross-entropy. Adam weight decay 0.01 and legal-only
  label smoothing 0.1 reduced overconfidence but did not improve top-1 agreement.
  Increasing hidden width to 128 or 256, both with and without regularization,
  did not produce a useful gain. A mover-relative rotation/color encoding also
  underperformed (best tested mean 18.19%). A legal-masked action-frequency
  baseline learned from training labels achieved 9.96% tuning agreement.
- Consequence: no framework, representation or model-size change is justified
  by this tuning sweep. Label smoothing was distributed only over legal actions;
  direct PyTorch smoothing over all 8100 outputs would conflict with the mask.
- Final-test lock: before generating new labels, saved `selection.json` chooses
  baseline (64 units, LR .01, 200 updates), slower (64 units, LR .003, 200), and
  regularized (64 units, LR .003, decay .01, smoothing .1, 50). All use seeds
  7/17/27. New source-game seed 101, 16 games, up to 32 plies and 16 labels/game;
  teacher remains 1000 nodes/depth 3. Exclude every old training/tuning input.
  Do not retune against the fresh test or select a lucky initialization seed.
- Artifacts: ignored `artifacts/learning/tuning-v1/` and
  `artifacts/learning/tuning-perspective-v1/` retain scripts, configurations,
  losses, timing, model checkpoints, and source/data hashes.
- Follow-up: evaluate the locked candidates once, then stop if gains do not
  justify adoption. Weekly usage remained 6% at the stage boundary.
- Review: not-required.

### 2026-09-09 — final held-out result and stop

- Evidence: generated 256 labels from 16 new source games at seed 101, with the
  same teacher and reserved corpus. Removed two inputs overlapping any old train
  or tuning input, leaving 254 final-test positions. Source trajectories were
  distinct, and no final-test labels influenced training or recipe selection.
  Dataset digest: `7d4ba9dc6649c883926003b0343b81cf310f144e25447840c6037fa005634ab4`.
- Fresh-test results, averaged over the three preselected initialization seeds:

  | Recipe | Correct counts / 254 | Mean agreement | Cross-entropy |
  | --- | --- | ---: | ---: |
  | Original baseline | 37, 38, 39 | 14.96% | 14.178 |
  | Lower learning rate | 39, 37, 34 | 14.44% | 8.929 |
  | Regularized, 50 updates | 27, 29, 27 | 10.89% | 3.783 |

- Interpretation: the small learning-rate tuning gain did not reproduce on new
  games. Regularization improved confidence calibration but reduced greedy
  teacher agreement. Larger models, longer fits and mover-relative encoding did
  not justify promotion. This single small held-out sample is not a strength
  benchmark; the meaningful conclusion is absence of evidence to replace the
  current recipe. A legal action-frequency baseline also remained weak.
- Verification: the final evaluator checked locked configurations, seeds,
  checkpoint/data hashes, identical teacher query settings, source-game identity,
  input disjointness, finite losses and per-source outcomes. Research checkpoints
  are marked by their prototype payloads and were never used as production player
  checkpoints. Complete scripts and all 108 tuning checkpoints remain local in
  the two ignored tuning directories; `final-test-report.json` records the fresh
  test and the exact retained input identities. The final test has now been
  inspected; future tuning needs a new untouched test or a prespecified protocol.
- Consequence: keep the current PyTorch/MPS trainer and defaults. No wider model,
  alternate encoding, smoothing or weight-decay option was added to the production
  surface based on unsuccessful experiments. The earlier controlled data-size
  improvement remains the useful finding from this session.
- Stop: use the user's diminishing-returns condition rather than consume the
  remaining quota on a broader search. Weekly usage was 6% at the final check,
  below the 25% soft stop. No usage-reset credit or remote training was used.
- Follow-up: if work resumes, investigate a better teaching curriculum or more
  independent data before another width/step sweep. No further run is scheduled.
- Review: local evidence/contract review; no separate reviewer agent.


```experiment
{
  "schema_version": 1,
  "id": "policy-tuning-v1",
  "title": "Local policy tuning and fresh-test check",
  "question": "Do tuning-selected recipes improve fresh held-out teacher agreement?",
  "kind": "learning",
  "topics": [
    "tuning",
    "negative result",
    "learning rate",
    "regularization",
    "width",
    "orientation"
  ],
  "execution": "complete",
  "conclusion": "not-supported",
  "finding": "On 254 fresh-test positions, mean agreement was 14.96% baseline, 14.44% lower learning rate, and 10.89% regularized. The small tuning gain did not reproduce; regularization lowered cross-entropy but reduced top-1 agreement.",
  "conditions": "Fixed 768 training labels; 12 configurations with three seeds and checkpoints at 50/200/800 updates (108 correlated observations), plus width/orientation sweep and locked fresh test.",
  "limitations": "Exploratory selection, one small fresh test and shallow teacher; unsuccessful tested options are not universal rejections.",
  "decision": "Keep current recipe; prioritize independent data or teaching curriculum over another width/step sweep.",
  "revisit": "Changed data, teacher or representation with an untouched test.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/tuning-v1.json",
      "role": "results",
      "sha256": "f4c35ffb8eb7af2afc6e022cedb51a3353fc849f8e0511f36dcda7e60a1c8f97"
    },
    {
      "path": "data/experiments/learning/history/tuning-perspective-v1.json",
      "role": "results",
      "sha256": "4f94858320497aaa4463c50a09dc07ca81da3c4cbe3c5bb6b01d2e17125df193"
    },
    {
      "path": "data/experiments/learning/history/tuning-final-test.json",
      "role": "results",
      "sha256": "3e18896cd43706f1ecb41702a899eb6d6d9de461b0d2464b1a770c9e42efb49d"
    }
  ],
  "prior_work": [
    {
      "id": "policy-generalization-v1",
      "relationship": "extends",
      "contribution": "Tests optimizer/model variants and checks selected recipes once on fresh games."
    }
  ],
  "novelty": "Tests optimizer/model variants and checks selected recipes once on fresh games."
}
```
