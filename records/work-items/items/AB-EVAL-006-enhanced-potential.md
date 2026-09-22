---
description: Bounded alpha-beta budget and search-efficiency experiments against pinned Pikafish profiles.
scope: backlog item
status: stable
last_update: 2026-09-22
document_class: work_record
work_id: AB-EVAL-006
work_status: done
work_kind: research
added: 2026-09-15
tags: search, experiments
depends_on: AB-EVAL-005
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-15"
---

# AB-EVAL-006 — Enhanced alpha-beta potential

## Intent

Test whether a modest budget increase and reduced search overhead can make
handcrafted alpha-beta competitive with the pinned local Pikafish profiles.

## Acceptance Criteria

- Predeclare bounded comparisons, selection rule and limitations.
- Preserve baseline identity; verify search correctness and hard budgets.
- Execute complete paired games, replay evidence, record failures and costs.
- Publish findings and searchable catalog evidence, including negative results.

## Context and Trade-offs

Prior `saved-checkpoint-elo-20260914`: enhanced at 128 visits/depth 2 scored
26/6/0 against basic alpha-beta but 0/0/32 against each Pikafish profile.
`search-components-v1` found small-budget recipe interactions but its game
matrix was incomplete. This extends those findings with budget scaling,
component subtraction and principal variation search (PVS): later moves first
receive a narrow score window, then a full re-search if they can improve the best.
No training, referee changes or external-strength claims are involved.

### Protocol fixed before execution

- Use only the existing CCPD **development** book, in stored order, one start
  per family. First four families are exploratory screening; next eight families
  are follow-up. These are new-to-this-selection families, not certified held-out
  data or the repository's reserved test pool.
- Probes: first 12 distinct-family starts, enhanced at 128/512/2048 visits,
  lean and PVS at 512/2048; depth cap 4. Record completed depth, fallback,
  quiescence/SEE work and latency. Probes do not select the game winner.
- Screen: four paired starts per profile versus Pikafish-small; four profiles:
  original enhanced 128/depth 2, scaled enhanced 1024/depth 4,
  lean 1024/depth 4 (remove SEE and check extensions), PVS lean 1024/depth 4.
  All retain positional evaluation, legal quiescence, ordering and history-aware TT.
- Select among the three 1024-visit profiles by paired score versus small;
  tie-break lower measured mean move latency, then profile ID. Do not pick by
  longer survival, teacher agreement or completed search depth.
- Follow-up: selected profile versus small and large on next eight paired starts;
  selected profile versus original enhanced 128 on first four follow-up starts.
  32 screening + 40 follow-up games = **72 planned games**.
- Pikafish pinned January 2, 2026 binary/network, one thread, Hash 16 MiB;
  small 1000 native nodes/depth 3, large 100000 native nodes/depth 8.
  Both native limits apply; actual reported work and fresh-process overhead matter.
- Seed 7, both colors, unchanged xiangqi-training-v1 terminal rules. No artificial
  early draw or loss adjudication. Only complete color pairs score.
- Execution bound: 30 minutes of game execution, checked before each game;
  current game finishes (hard player node caps and referee ply cap). Interrupted,
  failed or unstarted slots remain explicit; no selective extension after results.
- Practical next-step signal: selected profile scores at least 25% versus small
  in follow-up and beats original enhanced. 'Close' requires at least 40% against
  each tested profile; this small exploratory sample cannot establish parity with
  unrestricted Pikafish. No Elo from this selected, small matrix.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-15 | GPT-6 | — | wip | User authorized bounded optimization and experiment documentation. |
| 2026-09-15 | GPT-6 | wip | done | 84 probes and 72/72 games complete; replay, baseline parity and make check passed. |

## Implementation Ledger

- **2026-09-15 — decision:** Protocol above fixed before probes/games. Preserve
  original enhanced recipe and baseline versions. Evidence: this record and the
  resolved experiment config. Review: not-required.


```experiment
{
  "schema_version": 1,
  "id": "enhanced-potential-20260915",
  "title": "Enhanced alpha-beta potential",
  "question": "Can bounded search optimization approach the local Pikafish profiles?",
  "kind": "performance",
  "topics": [
    "alpha-beta",
    "enhanced",
    "Pikafish",
    "PVS",
    "search efficiency",
    "budget"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Predeclared 84 probes and 72 paired game slots, 30-minute game-execution bound; development family screen/follow-up split; explicit node/depth caps.",
  "limitations": "Exploratory selection, small sample, unequal resources, bounded Pikafish; no unrestricted-engine parity or external Elo claim.",
  "decision": "Run fixed budget/ablation/PVS comparisons and preserve all attempts.",
  "revisit": "Assess complete follow-up pairs under predeclared score thresholds.",
  "evidence": [],
  "prior_work": [
    {
      "id": "saved-checkpoint-elo-20260914",
      "relationship": "extends",
      "contribution": "Direct alpha-beta optimization and bounded-engine comparison after the 128-visit reference panel."
    },
    {
      "id": "search-components-v1",
      "relationship": "extends",
      "contribution": "Isolate budget scaling, component subtraction and PVS with completed paired-game evidence."
    }
  ],
  "novelty": "A bounded search-efficiency follow-up, not a new reference-strength scale."
}
```

### Supplemental diagnostic fixed during game execution

After all game attempts, profile one PVS decision at 1024 visits/depth 4 on the
first frozen opening, with cold referee caches. This only locates CPU cost;
profiling timings cannot enter screening selection or strength comparisons.
Retain profiler output and check the original enhanced decisions against the
pre-change search implementation on the 12 frozen probe starts.


## Outcome

- **2026-09-15 — finding:** 84 position probes and 72/72 paired-game slots
  completed in 18.1 game-execution minutes, with no failures or interruptions.
  All four screen profiles lost 0/0/8 against small Pikafish. PVS advanced by
  the declared latency tie-break; on fixed follow-up families it scored 8/0/0
  against original enhanced, 0/0/16 against small and 0/0/16 against large.
  This does not support the predeclared practical/close-to-Pikafish criteria.
  The 8–0 control changes both budget and recipe; no isolated PVS gain is shown.
  Evidence: [report](../../reports/2026-09-15-enhanced-alpha-beta.md),
  [compact results](../../../data/evaluation/enhanced-potential-20260915.json).
  Consequence: retain explicit experimental variants, with no strength promotion.
  Revisit after a materially faster search or stronger evaluator, under a new
  frozen paired-game comparison. Review: not-required.
- **2026-09-15 — verification:** Shared replay/scoring verified every completed
  game; source/config/game hashes checked. Original enhanced matched its pre-change
  search on all 12 probe starts. All 94 runtime Python files match the execution
  source archive. `make check`: 731 passed, one skipped; five browser unit tests,
  lint/docs/catalog, OpenAPI/type checks and production build passed. Both study
  scripts also passed Ruff checks. The local-only receipt is
  `artifacts/experiments/enhanced-potential-20260915/verification.json`.
  Follow-up: none required for this bounded study. Review: not-required.


```experiment
{
  "schema_version": 1,
  "id": "enhanced-potential-20260915",
  "title": "Enhanced alpha-beta potential",
  "question": "Can bounded search optimization approach the local Pikafish profiles?",
  "kind": "performance",
  "topics": [
    "alpha-beta",
    "enhanced",
    "Pikafish",
    "PVS",
    "search efficiency",
    "budget"
  ],
  "execution": "complete",
  "conclusion": "not-supported",
  "finding": "84 probes and 72/72 games completed, all replay-validated, no failures. At 128 visits enhanced fell back on 5/12 probe starts. All four screen profiles scored 0/8 against small Pikafish. PVS selected by latency tie-break; follow-up 8/0/0 versus original enhanced, 0/0/16 versus small and 0/0/16 versus large. Original enhanced unchanged on 12/12 probes.",
  "conditions": "Four development families for screening, next eight for follow-up; both colors, seed 7. Original 128 visits/depth 2; scaled/lean/PVS 1024/depth 4. Pikafish 1k/depth 3 and 100k/depth 8, one thread, Hash 16 MiB. 18.1-minute game execution within 30-minute bound.",
  "limitations": "The 8-0 control combines eightfold visit budget with recipe changes. Equal-budget screen shows no PVS strength gain. Small selected development study, unequal resources, bounded Pikafish. One CPU profile is not general speed evidence. No held-out, unrestricted-engine parity or Elo claim.",
  "decision": "No evidence of approaching either capped Pikafish profile through these small changes. Retain explicit experimental variants; next investigate faster legal move generation with equivalence checks and a new matched-time game study.",
  "revisit": "A materially faster search or stronger evaluator, frozen before a fresh development-family paired-game study.",
  "evidence": [
    {
      "path": "records/reports/2026-09-15-enhanced-alpha-beta.md",
      "role": "report",
      "sha256": "251457eef49a5e45224a3563c4b7c6e47d5067a42ec9c795f5e4d5a84f6e94f0"
    },
    {
      "path": "data/evaluation/enhanced-potential-20260915.json",
      "role": "results",
      "sha256": "149d553c15a0cc67fd656e4294d7992bce070a4951484c3a23b63148f8c78ddd"
    },
    {
      "path": "data/experiments/enhanced-potential-20260915.json",
      "role": "config",
      "sha256": "29c580d16f736f2a42caf9413607a641472ea6f819dc4770faef558d6b182c83"
    },
    {
      "path": "data/experiments/enhanced_potential.py",
      "role": "source",
      "sha256": "72cc4435912512414fa6e5263b56abba1f9dfea6cb756ada2ed6f654b92b96f6"
    },
    {
      "path": "data/experiments/enhanced_diagnostics.py",
      "role": "source",
      "sha256": "705aadb47d9138cac978569ac08840d540f6ebc9e5f056d1b415aa9b2fcd3410"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/manifest.json",
      "role": "run",
      "sha256": "72be21833a4151d5a68975df129cc017e574c8e59658949b920f88f6bdf84cdd"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/summary.json",
      "role": "results",
      "sha256": "7d05c5310d23eecf7482af9120d41fa1bcc6e994b0a8a6c71f8983fe34536684"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/diagnostics.json",
      "role": "results",
      "sha256": "399b569a7c00f077d445ac170574182dbd03fbef7d568397987298e271c22bc8"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/verification.json",
      "role": "results",
      "sha256": "b0eb06cee400262ac8fee68305a9c7848b9326a49c213ca11833596ea79b3d8e"
    }
  ],
  "prior_work": [
    {
      "id": "saved-checkpoint-elo-20260914",
      "relationship": "extends",
      "contribution": "Direct alpha-beta optimization and bounded-engine comparison after the 128-visit reference panel."
    },
    {
      "id": "search-components-v1",
      "relationship": "extends",
      "contribution": "Isolate budget scaling, component subtraction and PVS with completed paired-game evidence."
    }
  ],
  "novelty": "A bounded search-efficiency follow-up, not a new reference-strength scale."
}
```

### 2026-09-22 — portable report locator

This final catalog revision records the report after ignored artifact links were
made explicit local-only paths. The scientific result and old digest are retained.

```experiment
{
  "schema_version": 1,
  "id": "enhanced-potential-20260915",
  "title": "Enhanced alpha-beta potential",
  "question": "Can bounded search optimization approach the local Pikafish profiles?",
  "kind": "performance",
  "topics": [
    "alpha-beta",
    "enhanced",
    "Pikafish",
    "PVS",
    "search efficiency",
    "budget"
  ],
  "execution": "complete",
  "conclusion": "not-supported",
  "finding": "84 probes and 72/72 games completed, all replay-validated, no failures. At 128 visits enhanced fell back on 5/12 probe starts. All four screen profiles scored 0/8 against small Pikafish. PVS selected by latency tie-break; follow-up 8/0/0 versus original enhanced, 0/0/16 versus small and 0/0/16 versus large. Original enhanced unchanged on 12/12 probes.",
  "conditions": "Four development families for screening, next eight for follow-up; both colors, seed 7. Original 128 visits/depth 2; scaled/lean/PVS 1024/depth 4. Pikafish 1k/depth 3 and 100k/depth 8, one thread, Hash 16 MiB. 18.1-minute game execution within 30-minute bound.",
  "limitations": "The 8-0 control combines eightfold visit budget with recipe changes. Equal-budget screen shows no PVS strength gain. Small selected development study, unequal resources, bounded Pikafish. One CPU profile is not general speed evidence. No held-out, unrestricted-engine parity or Elo claim.",
  "decision": "No evidence of approaching either capped Pikafish profile through these small changes. Retain explicit experimental variants; next investigate faster legal move generation with equivalence checks and a new matched-time game study.",
  "revisit": "A materially faster search or stronger evaluator, frozen before a fresh development-family paired-game study.",
  "evidence": [
    {
      "path": "records/reports/2026-09-15-enhanced-alpha-beta.md",
      "role": "report",
      "sha256": "2790e97b05231c4c0e2ecbd7f0087bc100aa9c748c39ae4b1a6cb1758739d4bf"
    },
    {
      "path": "data/evaluation/enhanced-potential-20260915.json",
      "role": "results",
      "sha256": "149d553c15a0cc67fd656e4294d7992bce070a4951484c3a23b63148f8c78ddd"
    },
    {
      "path": "data/experiments/enhanced-potential-20260915.json",
      "role": "config",
      "sha256": "29c580d16f736f2a42caf9413607a641472ea6f819dc4770faef558d6b182c83"
    },
    {
      "path": "data/experiments/enhanced_potential.py",
      "role": "source",
      "sha256": "72cc4435912512414fa6e5263b56abba1f9dfea6cb756ada2ed6f654b92b96f6"
    },
    {
      "path": "data/experiments/enhanced_diagnostics.py",
      "role": "source",
      "sha256": "705aadb47d9138cac978569ac08840d540f6ebc9e5f056d1b415aa9b2fcd3410"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/manifest.json",
      "role": "run",
      "sha256": "72be21833a4151d5a68975df129cc017e574c8e59658949b920f88f6bdf84cdd"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/summary.json",
      "role": "results",
      "sha256": "7d05c5310d23eecf7482af9120d41fa1bcc6e994b0a8a6c71f8983fe34536684"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/diagnostics.json",
      "role": "results",
      "sha256": "399b569a7c00f077d445ac170574182dbd03fbef7d568397987298e271c22bc8"
    },
    {
      "path": "artifacts/experiments/enhanced-potential-20260915/verification.json",
      "role": "results",
      "sha256": "b0eb06cee400262ac8fee68305a9c7848b9326a49c213ca11833596ea79b3d8e"
    }
  ],
  "prior_work": [
    {
      "id": "saved-checkpoint-elo-20260914",
      "relationship": "extends",
      "contribution": "Direct alpha-beta optimization and bounded-engine comparison after the 128-visit reference panel."
    },
    {
      "id": "search-components-v1",
      "relationship": "extends",
      "contribution": "Isolate budget scaling, component subtraction and PVS with completed paired-game evidence."
    }
  ],
  "novelty": "A bounded search-efficiency follow-up, not a new reference-strength scale."
}
```
