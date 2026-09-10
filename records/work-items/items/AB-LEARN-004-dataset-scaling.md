---
description: Measure the effect of substantially more teacher labels with the policy and optimization recipe fixed.
scope: backlog item
status: stable
last_update: 2026-09-10
document_class: work_record
work_id: AB-LEARN-004
work_status: done
work_kind: research
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-003
residual_of: none
residual_items: none
---

# AB-LEARN-004 — Scale policy training data

## Intent

Test the user's hypothesis that 768 training positions is too small to assess
policy generalization. Increase data before changing the model or curriculum.

## Acceptance Criteria

- Compare nested 768, 3072 and 12288 position subsets from one fresh dataset,
  with the same held-out source games and initialization seeds 7/17/27.
- Keep the existing 1261-64-8100 float32 MLP, full-batch Adam at LR .01,
  200 updates, 1000-node/depth-3 teacher, and random 32-ply source games fixed.
- Retain replayable datasets, manifests, checkpoint identities, complete-seed
  results and verification; distinguish imitation from playing strength.
- Make bounded larger generation/experiment runs usable through the CLI, test
  parallel selection stability and existing leakage guards, and document results.

## Context and Trade-offs

The earlier width, duration and regularization sweeps only assessed a tiny-data
regime. Their negative findings do not establish that the current model cannot
benefit from substantially more examples. Hold optimization passes constant;
compute grows with data size. No learning-rate or checkpoint selection on the new
holdout. Full-batch training fits this host's scale without changing optimizer
semantics. No architecture, curriculum, value target or search change in this study.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User requested a substantial data-size experiment first. |

| 2026-09-09 | Codex | wip | done | Nine locked fits and independent verification complete; data scaling improves imitation. |

## Implementation Ledger

### 2026-09-09 — decision: lock the comparison before generation

- Evidence: `artifacts/learning/data-scaling-v1/selection.json` fixes sizes,
  seeds and recipe before labels are generated. Seed 211, 1056 source games,
  up to 16 sampled positions per game, one-quarter of games held out.
- Consequence: raise bounded dataset capacity to 2048 games/32768 labels and
  generation deadline to 7200 seconds. Add 1-4 workers with fresh single-threaded
  engines and seeded result ordering. Raise explicit fit/matrix deadline maxima
  to 600/7200 seconds; keep all defaults and training semantics unchanged.
- Follow-up: filter previously inspected dataset inputs before fitting; record
  retained input identities and counts. Evaluate all nine locked fits once.
- Review: not-required. Weekly quota at start: 7% used, below the user's 25% stop.

### 2026-09-09 — finding: data scaling improves the fixed policy

- Evidence: generated 16896 labels from 1056 source games in 890.5 seconds.
  Removed 32 inputs overlapping any earlier smoke, tuning or final-test dataset;
  retained 12645 training positions and 4219 validation positions from 264 games.
  Dataset SHA-256:
  `dd458c3547c0915737d7621c372968dc987b71d76606afc58c0caaeae2f3da3b`.
- Results, mean over initialization seeds 7/17/27:

  | Training positions | Train agreement | Held-out agreement ± seed SD | Held-out cross-entropy |
  | ---: | ---: | ---: | ---: |
  | 768 | 100.00% | 16.74% ± 0.15 pp | 10.873 |
  | 3072 | 99.98% | 21.27% ± 0.51 pp | 9.413 |
  | 12288 | 96.47% | 25.70% ± 0.42 pp | 7.981 |

- Interpretation: 16× more training data adds 8.96 percentage points, a 53.5%
  relative increase in exact teacher agreement. Each 4× data increase adds about
  4.5 points; no flattening is evident over these three sizes. A paired bootstrap
  over the 264 validation games (5000 draws, seed 211, averaging the three model
  seeds) gives an approximate 95% interval of 7.53–10.42 points for the largest
  gain. It does not cover training-data or teacher uncertainty. Random-legal
  expected agreement is 2.85%. These new results cannot be directly compared with
  the earlier 14.96% score on a different 254-position test.
- Consequence: prioritize further data scaling over another architecture sweep.
  Substantial overfitting remains, and this unchanged random early-game curriculum
  with shallow labels does not establish playing strength. The inspected holdout
  can support only a prespecified continuation; adaptive tuning needs a fresh test.
- Follow-up: a larger fixed-recipe study remains a candidate, not a scheduled run.
  Check preprocessing/reporting costs before expanding the next data budget.
- Review: local evidence/contract review; no separate reviewer agent.

### 2026-09-09 — deviation and verification: remove repeated replay work

- Evidence: the first matrix exposed repeated reconstruction of interleaved game
  histories in tensors, scoring and reload checks. It was deliberately interrupted
  after five completed fits; its partial manifest/checkpoints remain under
  `artifacts/learning/data-scaling-v1/curve/` with status `interrupted`.
- Change: each fit still validates its dataset, then replays selected positions in
  source order and reuses immutable game objects through training and reporting.
  The final nine-fit matrix ran from scratch under `curve-cached/`; all five
  comparable checkpoints have equal metadata and bit-identical weights.
- Timing: final matrix 712.8 seconds, including per-fit preparation/reporting/save;
  summed MPS optimization 34.28 seconds. Observed 768-position trials fell from
  about 87 to 58 seconds, and 3072-position trials from 164 to 66 seconds. These
  timings are run observations, not an isolated performance benchmark. Dataset
  preparation and independent result verification are separate from matrix time.
- Verification: all nine CPU checkpoints reproduced single-position legal actions,
  losses and curve aggregates. Input exclusions, teacher identity, source splits,
  exact nested subsets and fixed recipes passed. Real serial/parallel teacher
  checks returned identical selections and moves. `make check`: 308 Python tests
  passed, one opt-in GPU skip, three browser tests, lint/docs/build passed; the
  opt-in Metal test also passed before the replay change, and the full final MPS
  matrix verifies the changed path. Two pre-existing framework deprecation warnings.
- Evidence locations: `artifacts/learning/data-scaling-v1/` retains generation and
  selection records, raw/filtered datasets, both matrices, scripts, independent
  `verification.json`, summary and PNG/SVG learning curves. Artifacts stay local;
  no model was selected using validation or activated for play.
- Stop: the requested 16× comparison is complete. Weekly quota at closeout: 8%
  used, below the user's 25% soft stop. No reset credit or remote training used.
- Review: verified locally against replay contracts and saved checkpoint bytes.


```experiment
{
  "schema_version": 1,
  "id": "policy-data-scaling-v1",
  "title": "Larger fixed-recipe data scaling",
  "question": "Does scaling labels from 768 to 12288 improve the fixed policy?",
  "kind": "learning",
  "topics": [
    "data scaling",
    "generalization",
    "interrupted run",
    "replay performance"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Mean held-out agreement rose from 16.74% to 21.27% to 25.70% at 768/3072/12288 labels. The first attempt stopped after five of nine fits; a new cached-replay execution completed all nine, with five comparable checkpoints bit-identical.",
  "conditions": "Seeds 7/17/27, 200 updates, fixed 4219-position holdout from 264 games, random early-game data and 1000-node/depth-3 teacher.",
  "limitations": "Nested sizes from one generated dataset; inspected holdout; no playing strength. Initial and completed attempts remain separate evidence.",
  "decision": "Prioritize controlled data work; retain both interrupted and completed runs.",
  "revisit": "Changed teacher/curriculum, larger independent scale or profiling that changes total cost.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/data-scaling-interrupted.json",
      "role": "results",
      "sha256": "8aa885d35728a5b9471cad6abcaefed2f84e1a759bb4cf6f3f102190d479b38e"
    },
    {
      "path": "data/experiments/learning/history/data-scaling-v1.json",
      "role": "results",
      "sha256": "57cf0321392b6c89b321f2b7b172f6c6dd0a194e44df1eda53b558cae3684908"
    }
  ],
  "prior_work": [
    {
      "id": "policy-tuning-v1",
      "relationship": "extends",
      "contribution": "Scales independent source data while retaining the fixed policy after unsuccessful tuning."
    }
  ],
  "novelty": "Scales independent source data while retaining the fixed policy after unsuccessful tuning."
}
```
