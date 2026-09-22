---
description: Optimize legal move generation with exact behavioral controls and a bounded playing-strength follow-up.
scope: backlog item
status: stable
last_update: 2026-09-22
document_class: work_record
work_id: AB-EVAL-007
work_status: done
work_kind: research
added: 2026-09-15
tags: referee, performance, experiments
depends_on: AB-EVAL-006
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15"
---

# AB-EVAL-007 — Faster legal move generation

## Intent

Replace exhaustive destination/attacker scans with piece-specific candidates and
king-centered attack queries while preserving rules, ordered legal moves,
referee outcomes and fixed-budget player decisions. Measure whether saved CPU
time funds stronger search under an approximately matched latency envelope.

## Acceptance Criteria

- Keep a frozen before source and independent exhaustive geometry oracle.
- Match ordered legal moves and checks on arbitrary and replayable positions;
  retain fixed-budget decision and full recorded-game replay controls.
- Measure old/new cold legal generation and end-to-end PVS latency separately,
  with repeated, alternating isolated processes.
- Select a larger node cap using timing alone, then execute fixed paired games.
- Preserve measurements, failures, limits and source lineage; pass `make check`
  and register findings in the experiment catalog.

## Context and Trade-offs

`enhanced-potential-20260915` completed 84 probes and 72 games: PVS at 1024 visits
beat original enhanced at 128 visits 8–0, but lost 0/0/16 against both capped
Pikafish profiles. A single instrumented decision put 89.3% of cumulative time
in legal generation. That profile is a diagnostic, not general speed evidence.
This study changes execution cost, not the rules or search recipe.

### Protocol fixed before implementation/measurement

- Preserve the current runtime source under the local run's `before/` directory.
- Correctness: independent full-board oracle using unchanged `reaches`; all
  unique board/turn positions from the prior 72 games (both sides), 1000 seeded
  arbitrary boards (both sides), deterministic reachable trajectories and
  initial-position depth-three perft. Compare ordered tuples, checks, outcomes,
  and 24 fixed-budget PVS decisions (12 prior starts at 128/1024 visits, depth 4).
  Any mismatch blocks performance interpretation and game execution until fixed.
- Timing: 256 evenly spaced unique prior-game boards, both sides, cold legal
  generation; 12 prior starts with PVS 1024/depth 4, cold caches per decision.
  Three old/new rounds in isolated processes, alternating process order. Do not
  run other local tests during timing. Keep raw per-position times and choices.
- Node calibration uses the same 12 development starts, without game outcomes:
  new PVS at 2048/4096/8192 visits, depth 4, three repeats. Choose the largest
  cap whose mean decision latency is no greater than old PVS 1024. If none
  qualifies, use 1024. This is timing-calibrated fixed-node play, **not a clock
  limit or a claim of equal elapsed time on every game position**.
- Games: next eight distinct development opening families after the 12 used by
  AB-EVAL-006. Both colors against small and large Pikafish, plus first four
  families against PVS 1024/depth 4. 16 + 16 + 8 = **40 planned games**.
  Use the same January 2, 2026 binary/network, one thread, Hash 16 MiB;
  small 1000 native nodes/depth 3, large 100000/depth 8; seed 7.
- Thirty minutes of game execution, checked before every game; finish a started
  game under node and referee limits. Only complete pairs score; retain failures
  and pending games. No custom early adjudication, locked-pool use or training.
- Adoption: require exact controls and lower old/new median end-to-end latency
  in all three rounds. Playing-strength signal: at least 25% score versus small
  and over 50% versus PVS 1024. Close-to-profile criterion remains 40% against
  each Pikafish profile. Zero gains remain a useful negative result; no Elo.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-15 | GPT-6 | — | wip | User accepted legal move-generation optimization and measured follow-up. |
| 2026-09-15 | GPT-6 | wip | done | Exact controls and repeated speed criterion passed; 40/40 games complete; adoption and limits documented. |

## Implementation Ledger

- **2026-09-15 — decision:** Freeze correctness, timing, calibration and game
  protocol before implementation. Preserve previous results and unrelated work.
  Evidence: this owner and local before-source hashes. Review: not-required.


```experiment
{
  "schema_version": 1,
  "id": "movegen-20260915",
  "title": "Legal move generation optimization",
  "question": "Can equivalent faster legal move generation fund stronger alpha-beta at approximately the old latency?",
  "kind": "performance",
  "topics": [
    "alpha-beta",
    "PVS",
    "Pikafish",
    "legal moves",
    "referee",
    "speed",
    "optimization"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Frozen before source; exhaustive ordered-move controls; three isolated old/new timing rounds; timing-only node calibration; 40 paired game slots on eight new-to-selection development families.",
  "limitations": "Timing-calibrated node cap is not a per-move clock; small development sample and bounded Pikafish.",
  "decision": "Require exact behavioral controls before measuring/adopting the optimization.",
  "revisit": "Assess the fixed timing and playing-strength criteria.",
  "evidence": [
    {
      "path": "artifacts/experiments/movegen-20260915/before-hashes.json",
      "role": "source",
      "sha256": "7b875f965f09166a9974d5e586d76358674901098a3df52e39c6ac7f5769746b"
    }
  ],
  "prior_work": [
    {
      "id": "enhanced-potential-20260915",
      "relationship": "extends",
      "contribution": "Optimize its observed move-generation bottleneck and test a timing-calibrated larger search budget."
    }
  ],
  "novelty": "Output-preserving execution optimization, separated from search-budget playing-strength effects."
}
```

## Outcome

- **2026-09-15 — finding:** All 7292 board/side queries, 72 prior-game outcomes,
  depth-three perft (79666) and 24 fixed-budget start/budget cases matched.
  Across three isolated rounds, total legal-generation work sped up 10.23–10.49×
  and PVS 1024 decisions 5.53–5.61×; every median-speed criterion passed.
  Timing-only calibration selected 4096 visits at 573.7 ms versus old 1024 at
  782.9 ms. Evidence: [report](../../reports/2026-09-15-move-generation.md),
  [compact results](../../../data/evaluation/movegen-20260915.json).
  Consequence: adopt the equivalent referee optimization. Review: not-required.
- **2026-09-15 — finding:** All 40 game slots completed in 11.6 minutes without
  failures or interruptions. PVS 4096 scored 8/0/0 versus PVS 1024, 0/3/13 versus
  small Pikafish and 0/0/16 versus large. The small-profile practical threshold
  and both closeness thresholds failed. More search helped the direct local
  control; it did not establish competitiveness with Pikafish. Review: not-required.
- **2026-09-15 — decision:** Keep default budgets and player/ruleset versions;
  expose 4096-node PVS as an explicitly measured option. No evaluator/search
  change or broad strength promotion. Revisit after a new strength mechanism,
  frozen before a fresh family comparison. Review: not-required.
- **2026-09-15 — verification:** `make check` passed (745 Python tests, one
  skipped; five browser tests, lint/docs/catalog, contracts/types and build).
  Both study scripts passed Ruff checks. All 40 generated games also replayed
  under the frozen old referee. Raw timings reproduce every reported aggregate
  and the selected cap; source/dependency hashes match the measured snapshot.
  The local-only receipt is
  `artifacts/experiments/movegen-20260915/verification.json`.
  Follow-up: none required for this bounded study. Review: not-required.


```experiment
{
  "schema_version": 1,
  "id": "movegen-20260915",
  "title": "Legal move generation optimization",
  "question": "Can equivalent faster legal move generation fund stronger alpha-beta at approximately the old latency?",
  "kind": "performance",
  "topics": [
    "alpha-beta",
    "PVS",
    "Pikafish",
    "legal moves",
    "referee",
    "speed",
    "optimization"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "7292 ordered-move/check queries, 72 prior-game outcomes, depth-three perft 79666 and 24 fixed-budget start/budget cases matched. Three timing rounds: 10.23-10.49x faster legal generation; 5.53-5.61x faster PVS decisions. Timing-selected 4096 visits uses 573.7 ms versus old 1024 at 782.9 ms. All 40 games verified: 8/0/0 versus PVS 1024, 0/3/13 versus small Pikafish, 0/0/16 versus large.",
  "conditions": "Three alternating isolated-process rounds: 256 boards both sides and 12 PVS starts. 2048/4096/8192 calibration, 36 decisions each, depth 4. Eight new-to-selection development families for each Pikafish profile and four for direct control, paired colors, seed 7. 11.6 minutes within 30-minute game bound.",
  "limitations": "Finite equivalence controls and fixed local timing workloads. Coarse timing-calibrated cap is not a game clock. Different families prevent attributing the previous-to-current Pikafish score change solely to the budget. Small unequal-resource development sample; capped engines; no held-out, external Elo or parity claim.",
  "decision": "Adopt the equivalent faster referee; preserve default budgets. 4096-node PVS is a measured option, not a Pikafish strength promotion.",
  "revisit": "A stronger evaluator or search recipe frozen before a fresh development-family comparison with the same Pikafish profiles.",
  "evidence": [
    {
      "path": "records/reports/2026-09-15-move-generation.md",
      "role": "report",
      "sha256": "0f9e84f129d537a4f5c5b8f73f04dc4fbe6fe1013029340db0d056cabf33d714"
    },
    {
      "path": "data/evaluation/movegen-20260915.json",
      "role": "results",
      "sha256": "70adf1b5ae8ac3c614f23c3abc64a8ec8297521f118c2044fd0c6c6a9397948b"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/movegen_optimization.py",
      "role": "source",
      "sha256": "0ed7b29cee6fe04dd5a99f94ffe20a9705139c6fd8111a6ba3f9aac9c5312106"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/movegen_games.py",
      "role": "source",
      "sha256": "4a33432d459a5021d6564b43a0fb71d9da28fac0e30b199df4930edc38921a63"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/after/src/qi/game.py",
      "role": "source",
      "sha256": "aa8d179b16f1746b7a090a2a52008d53a54266169d29ce85a52d7ac24582bd61"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/after/src/qi/test_move_generation.py",
      "role": "source",
      "sha256": "bdd511b9660a4be53bb7438e5e0691bc4bf4dfce8780c7dbded876401cc7bccc"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/equivalence.json",
      "role": "results",
      "sha256": "2a1d4a856f2ebf2d0d460e4d19124db703f66b6a2844eebd102d7c601125568b"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/performance.json",
      "role": "results",
      "sha256": "fc960ccbe2266ae6a94f22922ead29abc2fc62c99779850cb4fa0b264b30e4d2"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/games-manifest.json",
      "role": "run",
      "sha256": "fa277841626794bf9aeb7bc72d5b5db31e4ef28016184ff86d096b93491d314a"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/games-summary.json",
      "role": "results",
      "sha256": "977dcbe19c66b7921d1d608295c97f71931148278d1e5ad4068ee1f6bda5cf4f"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/verification.json",
      "role": "results",
      "sha256": "c9288d64ae44cbe0451f3bb318add45a0cbf0a48bb412881c19c6296da21ed39"
    }
  ],
  "prior_work": [
    {
      "id": "enhanced-potential-20260915",
      "relationship": "extends",
      "contribution": "Optimize its observed move-generation bottleneck and test a timing-calibrated larger search budget."
    }
  ],
  "novelty": "Output-preserving execution optimization, separated from search-budget playing-strength effects."
}
```

### 2026-09-22 — portable report locator

This final revision records the report after ignored artifact links were
made explicit local-only paths. The scientific result and old digest remain
historical evidence.

```experiment
{
  "schema_version": 1,
  "id": "movegen-20260915",
  "title": "Legal move generation optimization",
  "question": "Can equivalent faster legal move generation fund stronger alpha-beta at approximately the old latency?",
  "kind": "performance",
  "topics": [
    "alpha-beta",
    "PVS",
    "Pikafish",
    "legal moves",
    "referee",
    "speed",
    "optimization"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "7292 ordered-move/check queries, 72 prior-game outcomes, depth-three perft 79666 and 24 fixed-budget start/budget cases matched. Three timing rounds: 10.23-10.49x faster legal generation; 5.53-5.61x faster PVS decisions. Timing-selected 4096 visits uses 573.7 ms versus old 1024 at 782.9 ms. All 40 games verified: 8/0/0 versus PVS 1024, 0/3/13 versus small Pikafish, 0/0/16 versus large.",
  "conditions": "Three alternating isolated-process rounds: 256 boards both sides and 12 PVS starts. 2048/4096/8192 calibration, 36 decisions each, depth 4. Eight new-to-selection development families for each Pikafish profile and four for direct control, paired colors, seed 7. 11.6 minutes within 30-minute game bound.",
  "limitations": "Finite equivalence controls and fixed local timing workloads. Coarse timing-calibrated cap is not a game clock. Different families prevent attributing the previous-to-current Pikafish score change solely to the budget. Small unequal-resource development sample; capped engines; no held-out, external Elo or parity claim.",
  "decision": "Adopt the equivalent faster referee; preserve default budgets. 4096-node PVS is a measured option, not a Pikafish strength promotion.",
  "revisit": "A stronger evaluator or search recipe frozen before a fresh development-family comparison with the same Pikafish profiles.",
  "evidence": [
    {
      "path": "records/reports/2026-09-15-move-generation.md",
      "role": "report",
      "sha256": "788710ebf9eadfceec7bb5af6d4746269f0769d987246e424ab75eb0a7c1fed1"
    },
    {
      "path": "data/evaluation/movegen-20260915.json",
      "role": "results",
      "sha256": "70adf1b5ae8ac3c614f23c3abc64a8ec8297521f118c2044fd0c6c6a9397948b"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/movegen_optimization.py",
      "role": "source",
      "sha256": "0ed7b29cee6fe04dd5a99f94ffe20a9705139c6fd8111a6ba3f9aac9c5312106"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/movegen_games.py",
      "role": "source",
      "sha256": "4a33432d459a5021d6564b43a0fb71d9da28fac0e30b199df4930edc38921a63"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/after/src/qi/game.py",
      "role": "source",
      "sha256": "aa8d179b16f1746b7a090a2a52008d53a54266169d29ce85a52d7ac24582bd61"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/after/src/qi/test_move_generation.py",
      "role": "source",
      "sha256": "bdd511b9660a4be53bb7438e5e0691bc4bf4dfce8780c7dbded876401cc7bccc"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/equivalence.json",
      "role": "results",
      "sha256": "2a1d4a856f2ebf2d0d460e4d19124db703f66b6a2844eebd102d7c601125568b"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/performance.json",
      "role": "results",
      "sha256": "fc960ccbe2266ae6a94f22922ead29abc2fc62c99779850cb4fa0b264b30e4d2"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/games-manifest.json",
      "role": "run",
      "sha256": "fa277841626794bf9aeb7bc72d5b5db31e4ef28016184ff86d096b93491d314a"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/games-summary.json",
      "role": "results",
      "sha256": "977dcbe19c66b7921d1d608295c97f71931148278d1e5ad4068ee1f6bda5cf4f"
    },
    {
      "path": "artifacts/experiments/movegen-20260915/verification.json",
      "role": "results",
      "sha256": "c9288d64ae44cbe0451f3bb318add45a0cbf0a48bb412881c19c6296da21ed39"
    }
  ],
  "prior_work": [
    {
      "id": "enhanced-potential-20260915",
      "relationship": "extends",
      "contribution": "Optimize its observed move-generation bottleneck and test a timing-calibrated larger search budget."
    }
  ],
  "novelty": "Output-preserving execution optimization, separated from search-budget playing-strength effects."
}
```
