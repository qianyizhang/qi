---
description: Track bounded search comparisons and explain their evidence through local reports and optional traces.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-EVAL-002
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-ENGINE-004, AB-EVAL-001
residual_of: none
residual_items: none
---

# AB-EVAL-002 — Search experiments and inspection

## Intent

Compare existing search recipes using durable local evidence, bounded sequential
execution, and regeneratable interactive HTML reports. Inspect selected decisions
with complete explored-work traces, separately from untraced timing measurements.

## Acceptance Criteria

- Preview a versioned plan covering fixed-position probes and paired-color games;
  retain exact configurations, corpus identities, code provenance, and results.
- Persist completed units and partial games; stop between decisions at a run
  deadline, with explicit incomplete/failed status and no invented draws.
- Validate replay, identity, accounting, and derived results before reporting.
- A local HTML report compares recipes/budgets and provides board/move inspection.
  Scores retain their scale and perspective; overlapping counters are not stacked.
- Optional traces cover alpha-beta iterations, cutoffs, cache use, extensions,
  quiescence, exchange analysis, MCTS selection/expansion, rollouts, and backup.
  Unsearched branches and exhausted recording limits are explicit.
- Traced reruns require matching code/configuration and reproduce the saved move
  and deterministic diagnostics. Their timings never enter benchmark summaries.
- Tests cover bounded execution, tampering, incomplete work, trace parity and
  accounting; repository checks and real browser inspection pass.
- Run the first local comparison with a 600-second allowance checked between
  decisions, and record actual evidence and limitations.

## Context and Trade-offs

User locked search-only scope, a local sequential runner, standalone interactive
HTML, and a 10-minute initial allowance. Full explored-tree inspection is opt-in
for selected decisions. Referee/player ownership stays unchanged; the experiment
module owns orchestration and evidence, and the report is a projection.
No database, background service, training changes, or full-tree batch capture.
Run artifacts remain ignored; tracked plans and module contracts are durable.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User ended the decision interview and authorized implementation |
| 2026-09-08 | Codex | wip | done | Module, reports, traces, checks, and the explicitly bounded first experiment verified |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: existing arena records and search diagnostics already own result
  semantics; ignored comparison scripts show the missing orchestration boundary.
- Consequence: reuse those contracts with explicit saved plans, validation, and
  an optional observational recorder in the search modules.
- Follow-up: complete implementation, checks, and the bounded initial run.
- Review: not-required.

### 2026-09-08 — implementation and verification

- Evidence: the [experiment guide](../../../src/qi/experiments/README.md) owns
  plan, persistence, verification, report, and trace semantics. The first plan
  freezes a 12-position corpus (four openings, six local midgame prefixes, two
  referee-proven immediate-win positions), 10 recipes, and three visit budgets.
- Consequence: local experiments now retain partial work and produce offline
  comparison, board replay, move diagnostics, and optional explored-tree views.
  The existing search loops remain authoritative; tracing is an optional observer.
- Verification: `UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed with 265 Python
  tests, three web lifecycle tests, Ruff, 58 governed Markdown files, report
  JavaScript syntax/format checks, TypeScript, and the production build.
  Existing FastAPI/Starlette deprecation warnings remain.
- Browser verification: all 42 desktop/mobile cases passed with the existing
  explicit local policy checkpoint. After the final report presentation changes,
  both report cases passed again. Report tests use temporary hermetic artifacts,
  check offline loading, inert untrusted text, filtering, replay, lazy tree
  expansion, complete/incomplete traces, and no document overflow. Desktop and
  mobile screenshots were inspected; final desktop presentation was rechecked.
- Environment: refreshing the editable package after documentation-binding
  changes required network access to the configured package mirror; the existing
  locked environment was refreshed without changing dependency versions. Browser
  tests required permission to bind their local test server on port 18765.
- Follow-up: finish the bounded real run, verify its evidence, and generate
  selected-decision traces and the user-facing report.
- Review: local live-diff/contract review and deterministic verification;
  no separate reviewer agent.


### 2026-09-08 — bounded experiment and interpretation

- Evidence: `qi experiment run --plan data/experiments/search-components-v1.json`
  with a 600-second allowance saved 360/360 probes, 20/24 complete games, and a
  53-ply partial game. Three games never started. It stopped with `deadline`
  status after 601.309 seconds; the last in-flight decision accounts for the
  allowed overshoot. The experiment matrix is explicitly incomplete; this
  implementation work item is complete under its bounded-run acceptance criteria.
- Verification: `qi experiment verify` replayed all 2856 recorded decisions,
  checked state/seed/version/budget accounting, and verified outcomes. All ten
  completed color pairs enter results; the partial game enters none. No illegal
  choices, retries, or player failures occurred.
- Results: combined alpha-beta versus quiescence recorded W/D/L 1/3/0 at 128
  visits and 4/0/0 at 512 (two opening/color pairs per budget), then 1/1/0 at
  2048 (one pair). Tactical MCTS versus plain MCTS recorded 1/2/1, 1/1/2, and
  1/0/1 at the same budgets and respective pair counts. These are small selected
  samples, not strength estimates.
- Results: all eight alpha-beta recipes solved both immediate-win targets at
  each budget. Both MCTS recipes missed both targets at 128 visits and solved
  both at 512 and 2048. Only those two targets have referee-proven winning moves;
  the other positions have no best-move ground truth.
- Traces: five selected decisions record 5039 total events, with no truncation
  and exact move/diagnostic parity. They show combined alpha-beta from the initial
  and winning positions, plain MCTS missing/finding an immediate win at 128/512
  visits, and a discarded tactical MCTS leaf. Every charged visit is accounted
  for. Trace timings are excluded from benchmark summaries.
- Limits: recipes run in a fixed order and share referee caches. Latencies are
  observations under that execution order, not isolated algorithmic speedups.
  Node counts and deterministic decisions remain reproducible. The single seed,
  selected corpus, and incomplete highest-budget games limit generalization.
- Artifacts: local ignored `artifacts/experiments/search-v1/` contains the
  manifest, per-unit records, status, five traces, `report-summary.json`, and
  the standalone `report.html` (4889153 bytes). The report was queued in Codex;
  its file URL is unsupported by browser-control inspection. Offline report
  behavior and layouts were verified through the hermetic desktop/mobile tests.
- Identity: source SHA-256
  `a145037e47f8163064a677951e342ac5326613123e91d21eeca23df9b068a849`;
  corpus SHA-256
  `81f5c6bb7988abf9eec84222adc6e511457b3967484e5e32e29558b15298eab5`;
  plan SHA-256
  `660f39400d1a65f4ef1a28bf9e28ef20d28cc4a65a23ec7488c542f686214c7c`.
- Consequence: the user can reproduce the plan, retain partial evidence, compare
  matched positions/budgets, and inspect full explored work for selected moves.
- Follow-up: none required for this bounded implementation. Further experiments
  should choose their own budget and control cache/order effects before making
  performance claims.
- Review: local review and replay/accounting verification; no separate agent.

## Beginner-help follow-up — 2026-09-08

- User requested domain/technical glossary coverage and beginner tooltips in the
  existing HTML report. Expanded the vocabulary authority to 193 English/Chinese
  entries covering rules, pieces, search, counters, experiments, traces, software,
  and learning. Aliases map report labels and saved field names to those entries.
- Added a reading guide, searchable embedded reference, and hover/focus/tap help.
  MCTS node visits and charged-work visits have distinct explanations. Annotated
  JSON remains valid when copied; dynamic filters and trace views retain help.
- Definitions are loaded from `docs/glossary/ddd.md` during report generation,
  with a separate glossary digest. Saved experiment identities remain unchanged.
- Validation: `make check` passed (269 Python and 3 web unit tests, formatting,
  documentation checks, and browser build). After final help refinements,
  `make lint`, 17 experiment/glossary tests, and four desktop/mobile browser cases
  passed, including actual touch input, keyboard dismissal, glossary search, and
  unchanged copied JSON. Tooltip screenshots were visually inspected.
- Regenerated the existing local report. Replay/accounting validation still shows
  380 of 384 planned units complete; no search experiment was rerun.
