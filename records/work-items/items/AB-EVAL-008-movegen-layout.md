---
description: Compare dense NumPy checks and compact occupancy masks for further move-generation optimization.
scope: backlog item
status: stable
last_update: 2026-09-22
document_class: work_record
work_id: AB-EVAL-008
work_status: done
work_kind: research
added: 2026-09-15
tags: referee, performance, experiments
depends_on: AB-EVAL-007
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15"
---

# AB-EVAL-008 — Move-generation data structures

## Intent

User requested further optimization and proposed NumPy/Torch for nested table
construction loops and append-based data structures.

## Context and Trade-offs

The previous
[study](../../reports/2026-09-15-move-generation.md) achieved about 10.4× faster
legal queries and 5.5× faster PVS decisions against exhaustive generation.
Those measurements exclude import-time table construction. Its 40-game follow-up
did not establish competitiveness with Pikafish. This study measures additional
execution savings at identical outputs and budgets; it makes no new strength claim.

## Protocol fixed before measurement

- Freeze the current source, dependencies and inherited inputs in a new local
  run directory. Preserve all prior study files.
- Measure one-time table construction separately (100 builds), plus a single
  1024-node PVS profile as a diagnostic. Reuse the prior 256 timing boards and
  12 development starts, explicitly as performance-development inputs.
- Prototype two bounded alternatives: NumPy batched king-safety checks across
  candidate moves, and integer occupancy masks reused for candidate king safety.
  Simplify ray construction with direct ranges. Up to one follow-up refinement
  of the better CPU representation is allowed; retain unsuccessful prototypes.
- Screen each on all 7292 prior board/side correctness queries, then three
  timing repeats on 512 cold legal queries. Include board/array conversion and
  candidate materialization in NumPy timings; measure its setup/import separately.
  No Torch/GPU implementation unless NumPy wins this per-position screen.
- Before adoption, compare the frozen baseline and selected source in three
  isolated process rounds with alternating order: 512 cold legal queries and
  12 cold PVS decisions at each of 1024 and 4096 visits, depth 4, seed 7.
  Require exact ordered legal/check results, full fixed-budget Choice equality
  except elapsed time, prior recorded-game outcomes and depth-three perft 79666.
- Adopt only if each round improves median end-to-end latency at both budgets
  and pooled mean latency improves at least 5%. Otherwise retain the baseline
  and record the negative result. No tuning based on playing outcomes, new
  matches, node-budget/default changes, training or dependency additions without
  a measured benefit. Run the cross-cutting `make check` gate.

## Acceptance Criteria

- Answer setup-loop and data-structure comments with separated measurements.
- Retain prototypes, source snapshots, exact inputs, raw timings and controls.
- Document adopted/rejected alternatives and limits in a report and catalog.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-15 | GPT-6 | — | wip | User requested additional optimization and a tensor/data-structure comparison. |
| 2026-09-15 | GPT-6 | wip | done | Equivalent mask/attack-lookup implementation passed repeated speed gates and full verification; NumPy result retained. |

## Implementation Ledger

- **2026-09-15 — delivery cleanup:** Before the user-requested commit, add
  early output guards to the maintained preparation/screen scripts and tidy
  the implementation note. All 12 existing-output cases reject without changing
  evidence. The 132 runtime/dependency hashes still match the fully tested
  snapshot (752 Python tests, one skipped; five browser tests). Original measured
  script copies and findings remain unchanged. Docs, script lint and catalog
  evidence checks pass. Review: not-required.
- **2026-09-15 — decision:** Freeze the bounded performance protocol above
  before implementation and timing. Review: not-required.
- **2026-09-15 — diagnostic and refinement:** The single profile puts 56.5%
  of cumulative decision time in positional `king_safety`, which still scans
  all pieces for every palace-zone square. The NumPy screen was slower than
  baseline; masks were faster with all 7292 queries matching. Use the one
  allowed follow-up refinement to reuse inverse attack tables for arbitrary
  target squares in that evaluator, without changing scores or weights.
  Before timing/adoption, add exhaustive attack checks on every target square
  for 1000 arbitrary boards/both sides and compare all 7292 evaluation
  breakdowns. Include a masks-only source ablation in the final three timing
  rounds so its savings remain separate. This is an adaptive performance
  refinement after the diagnostic, not a predeclared independent hypothesis.
  Evidence: local `before-profile.txt` and `screen.json`. Review: not-required.


```experiment
{
  "schema_version": 1,
  "id": "movegen-layout-20260915",
  "title": "Move-generation data structures",
  "question": "Can batched arrays or compact occupancy masks improve the already optimized referee?",
  "kind": "performance",
  "topics": [
    "referee",
    "NumPy",
    "bitmasks",
    "alpha-beta",
    "optimization"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "One-time setup measurements; bounded NumPy/bitmask prototypes; 7292 board-side controls; three isolated rounds of 512 legal queries and 12 starts at 1024/4096 visits.",
  "limitations": "Reused development workloads; no playing-strength or general tensor claim.",
  "decision": "Adopt only equivalent outputs and repeated end-to-end speed improvement.",
  "revisit": "Assess the frozen protocol.",
  "evidence": [
    {
      "path": "artifacts/experiments/movegen-layout-20260915/before-hashes.json",
      "role": "source",
      "sha256": "5c28eccca4ecdeefbf26fb28388bcd9f872788932d1a16f3c827bd6e5838ecee"
    }
  ],
  "prior_work": [
    {
      "id": "movegen-20260915",
      "relationship": "extends",
      "contribution": "Separate setup cost from per-candidate runtime and compare arrays with occupancy masks."
    }
  ],
  "novelty": "Additional execution optimization at unchanged search budgets, not independent playing-strength evidence."
}
```

## Outcome

- **2026-09-15 — finding:** Batched NumPy was 9.0% slower than the baseline
  legal generator; integer masks passed all 7292 screen queries and were faster.
  Table construction was only 0.524 ms in the initial diagnostic. Retain the
  rejected prototype and keep production dependencies unchanged. Review: not-required.
- **2026-09-15 — finding:** Three isolated rounds measured additional PVS
  speedups of 2.65× at 1024 visits and 2.47× at 4096, relative to AB-EVAL-007.
  Masks-only and full-source ablations separate the legal-generation and
  positional attack-lookup savings. All median/pooled-mean adoption gates passed.
  Final tables cost roughly 0.9 MB more and 0.6 ms additional startup.
  Evidence: [report](../../reports/2026-09-15-movegen-layout.md),
  [compact results](../../../data/evaluation/movegen-layout-20260915.json).
  Review: not-required.
- **2026-09-15 — verification:** 7292 ordered legal/check/evaluation comparisons,
  180000 exhaustive arbitrary-target checks, 112 existing-game replays and perft
  79666 matched. All 24 distinct start/budget Choice comparisons matched in
  three rounds for all sources except timing. `make check` passed: 752 Python
  tests, one skipped; five browser tests; lint/docs/catalog, types and build.
  Frozen source/input hashes and raw timing means were verified. The initial
  docs-only gate failure and corrected rerun are retained in the local-only
  receipt `artifacts/experiments/movegen-layout-20260915/verification.json`.
  Review: not-required.
- **2026-09-15 — decision:** Adopt masks and the shared attack query without
  changing rules, scores, default budgets or player versions. This study adds
  performance evidence only; previous Pikafish outcomes remain the strength
  evidence. Revisit strength with a frozen search/evaluator change or a fresh
  timing-calibrated match study. Review: not-required.


```experiment
{
  "schema_version": 1,
  "id": "movegen-layout-20260915",
  "title": "Move-generation data structures",
  "question": "Can batched arrays or compact occupancy masks improve the already optimized referee?",
  "kind": "performance",
  "topics": [
    "referee",
    "NumPy",
    "bitmasks",
    "alpha-beta",
    "optimization"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Batched NumPy was 9.0% slower on the screen; masks improved legal generation. Three isolated rounds show 2.65x faster PVS at 1024 visits and 2.47x at 4096 relative to the already optimized baseline; masks-only ablation separates evaluator savings. All 7292 legal/check/evaluation queries, 180000 target attacks, 112 replays, perft 79666 and fixed-budget Choice controls matched.",
  "conditions": "Three alternating isolated-process rounds, 512 cold legal queries and 12 development starts at 1024/4096 visits per source/round; baseline, masks-only and masks plus attack lookup. Initial NumPy/mask screen and adaptive profile-driven evaluator refinement retained.",
  "limitations": "Finite reused development controls and local timings; no new games, clock limit, Elo or Pikafish closeness evidence. NumPy result is specific to this per-position batched prototype; Torch/GPU untested. Approximately 0.9 MB extra table memory and 0.6 ms startup.",
  "decision": "Adopt occupancy masks and shared geometric attack lookup with identical evaluator scores and no new dependencies or default-budget changes.",
  "revisit": "Fresh timing-calibrated matches or a frozen strength mechanism; batch arrays only for a materially different workload.",
  "evidence": [
    {
      "path": "records/reports/2026-09-15-movegen-layout.md",
      "role": "report",
      "sha256": "89377d6f835ac69dd27ee509555d9a94001b8fe1a24972413a8ebe802f598598"
    },
    {
      "path": "data/evaluation/movegen-layout-20260915.json",
      "role": "results",
      "sha256": "f58260f887e7b2a1159cf7b04d32c3222b33bc81428180b7c81706d25a1c10c8"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/movegen_layout.py",
      "role": "source",
      "sha256": "7941230e3a8091ca0e5c69a40aab1cf436205933ffdd199342bb06267c70ed07"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/movegen_layout_validation.py",
      "role": "source",
      "sha256": "075478bc436bc692f18cd7d660b29b47450db3e14025c5507a6000e1e55acbd0"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/movegen_optimization.py",
      "role": "source",
      "sha256": "0ed7b29cee6fe04dd5a99f94ffe20a9705139c6fd8111a6ba3f9aac9c5312106"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after/src/qi/game.py",
      "role": "source",
      "sha256": "29f61c5a1e22ff58fc13107a1bbbfc6eef0e8e1ed535d196aaa15aefe2740148"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after/src/qi/players/components/positional/__init__.py",
      "role": "source",
      "sha256": "9af35d32c4ec3f3af3a656cf7a6bd8fb587e90a6f5a091de04bd2948fbe2cfa1"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after/src/qi/test_move_generation.py",
      "role": "source",
      "sha256": "e717d2fa5e10b467f236e808036d12b1ba544f6bba970847490ef62d7f16f738"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/manifest.json",
      "role": "run",
      "sha256": "06cfca74378bd56ae51144cc6a251be556a0687e94815c83cd15bcca3728b04d"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/before-hashes.json",
      "role": "source",
      "sha256": "5c28eccca4ecdeefbf26fb28388bcd9f872788932d1a16f3c827bd6e5838ecee"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/masks-only-hashes.json",
      "role": "source",
      "sha256": "71c24aa5b76699267be1e633a3ea3e898f3ef048465a4e0c5a4396a693552084"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after-hashes.json",
      "role": "source",
      "sha256": "66523f99da71b08c7496e749b5da03ae764bd413ea4e13cf7f50244bf86516c0"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/screen.json",
      "role": "results",
      "sha256": "7db46541df3bc50cda260ac3db76542171c3361309ee70dc85478cada3e1c922"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/setup-before.json",
      "role": "results",
      "sha256": "31a31267a5a85fc521d22558722fc7e9e97955298df12aa2d45daba33dc52c59"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/before-profile.txt",
      "role": "results",
      "sha256": "50cdb4234b7828642b3fbd6aff4234d948db439e3250913778fcb5b515a09236"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/equivalence.json",
      "role": "results",
      "sha256": "2f57ab1dbb4346dfd1dc2ddd83b098e643e308d8bc62cf5dc4072f5b9470ac8e"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/performance.json",
      "role": "results",
      "sha256": "f9713709c88c1b3f6bda8e773d9a43bc7062eaf802aa75f7e471f3c87ed8ad5f"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/verification.json",
      "role": "results",
      "sha256": "1cb47b2507d625b375bd01f9c4c791b196fe273a5848272cf1514c90c007e976"
    }
  ],
  "prior_work": [
    {
      "id": "movegen-20260915",
      "relationship": "extends",
      "contribution": "Separate setup cost from per-candidate runtime and compare arrays with occupancy masks."
    }
  ],
  "novelty": "Additional execution optimization at unchanged search budgets, not independent playing-strength evidence."
}
```

### 2026-09-22 — portable report locator

This final revision records the report after ignored artifact links were
made explicit local-only paths. The scientific result and old digest remain
historical evidence.

```experiment
{
  "schema_version": 1,
  "id": "movegen-layout-20260915",
  "title": "Move-generation data structures",
  "question": "Can batched arrays or compact occupancy masks improve the already optimized referee?",
  "kind": "performance",
  "topics": [
    "referee",
    "NumPy",
    "bitmasks",
    "alpha-beta",
    "optimization"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Batched NumPy was 9.0% slower on the screen; masks improved legal generation. Three isolated rounds show 2.65x faster PVS at 1024 visits and 2.47x at 4096 relative to the already optimized baseline; masks-only ablation separates evaluator savings. All 7292 legal/check/evaluation queries, 180000 target attacks, 112 replays, perft 79666 and fixed-budget Choice controls matched.",
  "conditions": "Three alternating isolated-process rounds, 512 cold legal queries and 12 development starts at 1024/4096 visits per source/round; baseline, masks-only and masks plus attack lookup. Initial NumPy/mask screen and adaptive profile-driven evaluator refinement retained.",
  "limitations": "Finite reused development controls and local timings; no new games, clock limit, Elo or Pikafish closeness evidence. NumPy result is specific to this per-position batched prototype; Torch/GPU untested. Approximately 0.9 MB extra table memory and 0.6 ms startup.",
  "decision": "Adopt occupancy masks and shared geometric attack lookup with identical evaluator scores and no new dependencies or default-budget changes.",
  "revisit": "Fresh timing-calibrated matches or a frozen strength mechanism; batch arrays only for a materially different workload.",
  "evidence": [
    {
      "path": "records/reports/2026-09-15-movegen-layout.md",
      "role": "report",
      "sha256": "e44f782a9f22d2948a42cff56070c4a67492d8d219b8e2245d3d2b0b12419d8b"
    },
    {
      "path": "data/evaluation/movegen-layout-20260915.json",
      "role": "results",
      "sha256": "f58260f887e7b2a1159cf7b04d32c3222b33bc81428180b7c81706d25a1c10c8"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/movegen_layout.py",
      "role": "source",
      "sha256": "7941230e3a8091ca0e5c69a40aab1cf436205933ffdd199342bb06267c70ed07"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/movegen_layout_validation.py",
      "role": "source",
      "sha256": "075478bc436bc692f18cd7d660b29b47450db3e14025c5507a6000e1e55acbd0"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/movegen_optimization.py",
      "role": "source",
      "sha256": "0ed7b29cee6fe04dd5a99f94ffe20a9705139c6fd8111a6ba3f9aac9c5312106"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after/src/qi/game.py",
      "role": "source",
      "sha256": "29f61c5a1e22ff58fc13107a1bbbfc6eef0e8e1ed535d196aaa15aefe2740148"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after/src/qi/players/components/positional/__init__.py",
      "role": "source",
      "sha256": "9af35d32c4ec3f3af3a656cf7a6bd8fb587e90a6f5a091de04bd2948fbe2cfa1"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after/src/qi/test_move_generation.py",
      "role": "source",
      "sha256": "e717d2fa5e10b467f236e808036d12b1ba544f6bba970847490ef62d7f16f738"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/manifest.json",
      "role": "run",
      "sha256": "06cfca74378bd56ae51144cc6a251be556a0687e94815c83cd15bcca3728b04d"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/before-hashes.json",
      "role": "source",
      "sha256": "5c28eccca4ecdeefbf26fb28388bcd9f872788932d1a16f3c827bd6e5838ecee"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/masks-only-hashes.json",
      "role": "source",
      "sha256": "71c24aa5b76699267be1e633a3ea3e898f3ef048465a4e0c5a4396a693552084"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/after-hashes.json",
      "role": "source",
      "sha256": "66523f99da71b08c7496e749b5da03ae764bd413ea4e13cf7f50244bf86516c0"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/screen.json",
      "role": "results",
      "sha256": "7db46541df3bc50cda260ac3db76542171c3361309ee70dc85478cada3e1c922"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/setup-before.json",
      "role": "results",
      "sha256": "31a31267a5a85fc521d22558722fc7e9e97955298df12aa2d45daba33dc52c59"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/before-profile.txt",
      "role": "results",
      "sha256": "50cdb4234b7828642b3fbd6aff4234d948db439e3250913778fcb5b515a09236"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/equivalence.json",
      "role": "results",
      "sha256": "2f57ab1dbb4346dfd1dc2ddd83b098e643e308d8bc62cf5dc4072f5b9470ac8e"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/performance.json",
      "role": "results",
      "sha256": "f9713709c88c1b3f6bda8e773d9a43bc7062eaf802aa75f7e471f3c87ed8ad5f"
    },
    {
      "path": "artifacts/experiments/movegen-layout-20260915/verification.json",
      "role": "results",
      "sha256": "1cb47b2507d625b375bd01f9c4c791b196fe273a5848272cf1514c90c007e976"
    }
  ],
  "prior_work": [
    {
      "id": "movegen-20260915",
      "relationship": "extends",
      "contribution": "Separate setup cost from per-candidate runtime and compare arrays with occupancy masks."
    }
  ],
  "novelty": "Additional execution optimization at unchanged search budgets, not independent playing-strength evidence."
}
```
