---
description: Supervise repaired sequential generation with retained rejection evidence and cumulative accounting.
scope: session handoff report
status: experimental
last_update: 2026-09-11
document_class: coordination
produced_by: "babysit@1.1.0 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# Handoff — supervised generation

Use `$babysit`; work in `/Users/zhangqy/pkgs/qi` and follow
[CLAUDE.md](../../CLAUDE.md). Current operator task:
`01a08dbd-a3b6-7033-b5a5-d676a3174855`. Original source task:
`01a08c1b-897f-74c1-a28c-39c4b9007146`.

## Intent and authority

Continue sequential roughly one-hour batches until user stop or a real boundary.
The user explicitly authorized bounded repair and actual continuation: a routine
trajectory duplicate must not end the operation. Retain rejected attempts, exclude
them from accepted output, and continue without quota refill. Preserve all frozen
scientific settings and split isolation; resolve genuinely new acceptance decisions.
No training, export, Elo, parallel writers, new teacher budgets or destructive cleanup.

Owner: [AB-DATA-008](../work-items/items/AB-DATA-008-generation-scaling-pilot.md).
Contracts: [generation](../../docs/data-generation.md) and
[collection](../../src/qi/training_data/README.md).

## Latest reviewed boundary

User-authorized 10000-attempt extension: **target complete; heartbeat PAUSED**.
Final replay and analysis validation through row 443832 passed, as did SQLite
integrity, foreign keys and read-only reopen of all 10000 rows. No active writer.
Accounted writes: 189749301248 bytes including the retained 21GB conservative
launcher charge, 3GB operator reserves, measured validation and pilot writes.
Completed totals: 9963 accepted / 37 rejected,
10000 planned attempts disposed. Target includes rejections; no refill.
Latest invocation 11, batch 9; consult ledger for live status.
Batches 7–9 use eight engine threads, unchanged other recipe parameters,
and unused source blocks 70–99. Prior batches and provenance are preserved.
Write-volume caps and 21GB dispatch allowance were lifted by the user;
1500MB RSS and 30GB free-space guards remain. Ten-minute heartbeat.
Source commit 9f1d57a4b408a18e6bdba1b5b57e63d4169581a4; pinned hash 28558bcbdb10000bb5c3787df70afa4f313fca696ade5faab8691279c1f865f7.
Use `extension_boundary.py` after exited-accounted batch plus `validate.py --boundary`,
then `launch.py INDEX` and `extension_checkpoint.py TOOL_SESSION`.
Do not use the superseded `prepare_next.py`, `review_boundary.py`,
`record_checkpoint.py` or `close_budget.py` for this extension.
At 10000 attempts, run final integrity validation, pause heartbeat and refresh evidence.
This section and operator extension notes supersede historical limits below.

## Live pickup — always reconcile

Operational root: `artifacts/learning/overnight-batches-20260911/`.
Read `ledger.json`, `operator-notes.md`, recent `operator.jsonl` and
`observations.jsonl`. Shared writer store: `collection.sqlite`.

- Repair committed as `5c73fa1`; generation source hash
  `7a61464cf9a742729dbe01ab0940b01be613e93c78b884ee53a492fbd689a395`.
  Full gate passed 556 Python tests, one opt-in skip, five browser tests,
  lint/docs/catalog and builds. See `recovery-check.log`.
- Original batch 0/run 1 retains **553 completed games and failed game 554**.
  Game 554 (`plausible-block-005`, index 53) exactly duplicates opposite-split
  validation game 38, all 86 plies. Original rows, output and incident remain intact.
  [Original incident](../../data/experiments/learning/history/overnight-generation-20260911.json)
  and [recovery evidence](../../data/experiments/learning/history/overnight-generation-recovery-20260911.json)
  distinguish historical failure from the authorized recovery.
- Invocation **2** launched with the unchanged `batch-0000.json`, fresh output
  `batch-0000-recovery`, and `--continue-from-run 1`. Its frozen manifest references
  the 553 accepted identities plus the verified legacy rejection; **446 unstarted
  identities** remain at dispatch. New work belongs to a new logical run. The old
  `batch-0000` output remains under batch `prior_outputs` and prior execution records.
- Process/session and monitor status are live ledger fields. Do not duplicate a
  healthy writer. Heartbeat `supervise-qi-overnight-generation` is retargeted to this
  operator task with the revised rejection policy; verify target/status before
  handing off active supervision. Five-minute scheduling is approved and approximate.

## Resume and next dispatch

`launch.py INDEX [--resume]` checks ledger readiness, the pinned source/config,
locks and remaining allowance, records owned PIDs and bills a fresh execution's
final counters. It automatically adds the batch's `continue_from_run` option.
For batch 0, ordinary deadline resume keeps output `batch-0000-recovery` and
`--continue-from-run 1`. Never blindly resume across another source change;
continuation chains are intentionally rejected and require explicit reconciliation.

The repaired runner retains new conflicts as `failed` with stop reason
`rejected-trajectory`; resume skips those identities. Legacy game 554 stays
`failed/error` unchanged and is explicitly inherited as rejected after verification.
`generation_status: complete` means all planned identities are disposed;
**games + rejected_games = planned_games**, including inherited identities.
Accepted phase counts exclude rejected games. `shortfall` does not authorize refill.

At every exit, inspect summary/events, source identity, charge, SQL statuses and
incremental validation before dispatch. For an ordinary deadline, inspect its
actual failure and exact frozen config, then resume; no-progress retries need
diagnosis. At a completed batch, create only the next unused numbered recipe:

- Deep-copy resolved `batch-0000.json`; change its name to `overnight-batch-NNNN`.
- For batch N, map source blocks to `10*N` through `10*N+9`, IDs
  `MODE-block-NNN`; every tenth block is validation. Preserve each source's mode,
  game count, settings, seed and start. Check no source ID was used before.
- Record config/hash/source interval and fresh output `batch-NNNN` in the ledger.
  New batches have **no** `continue_from_run` field. Preview, review allowance,
  set `ready`, then launch exactly one invocation.

Runner: `.venv/bin/python scripts/run_generation_pilot.py --config RECIPE
--output OUTPUT --collection artifacts/learning/overnight-batches-20260911/collection.sqlite
--max-write-gb 20 --max-rss-mb 1500 --min-free-gb 30`, with `--preview` for preflight.
Use process-inspection permissions in the actual launch environment so guards work.

## Frozen resources and validation

Recipe: 1,000 planned games, 3,600 seconds/invocation; 800 plausible / 100
intervention / 100 random; 900 train / 100 validation. Pinned assets, 10k-node
actors, paired 10k/100k labels, 300-ply cap, candidate/intervention/audit settings,
phase caps 1/8/8 and spacing four remain unchanged. The old 9,000-game profile is
neither a quota nor the command to launch.

**150 decimal GB cumulative writes**, 20GB/invocation, at least 21GB remaining
before dispatch; 1,500MB sampled RSS and 30GB free-space floor. At recovery dispatch,
charged/reserved was **31.597721088GB**, leaving **118.402278912GB** before invocation 2:
8.583770112GB original generator writes, 21GB conservative original launcher failure,
2GB total operator reserves and 0.013950976GB measured validation writes. Preserve
all entries; never reset allowance. Charge each invocation once using the larger
final resource/process write counter; no fresh final summary means conservative
21GB fallback. Add measured validator writes and review operator reserve at closeout.

Use `observe.py` for incremental events, new/reused/rejected counts, CPU, progress
and DB/WAL; `validate.py` persists PK cursors and pending IDs. Avoid concurrent ledger
updates; prefer validation after writer exit. Check early new games and about every
five minutes. Investigate sustained >2x writes/new-game growth at matched policy/
horizon, >100x write/DB amplification, WAL >64MB growing across two observations,
or progress stale for two minutes; use CPU/search evidence before declaring a hang.

At boundaries run `validate.py --boundary`, adding `--integrity` at the first
completed batch and final stop. Revisit pending rows; report rejected/failed evidence
separately. The repaired validator checks confirmed rejection evidence and computes
global selected uniques only from completed games. Never sum per-batch unique counts.
Before later training, freeze shared-input exclusions and label-ambiguity decisions
and export an eligible immutable snapshot under the separate protocol.

On user stop: persist stopped/no-further-dispatch first, stop only the verified owned
writer, await actual exit/accounting, validate, record results and pause the heartbeat.

## Rejection warnings and acceptance diagnostics

The user's relayed clarification is implemented by the read-only operator helper
`diagnose.py`, without changing running generation source. Run it after `observe.py`
and at boundaries. It writes `acceptance-latest.json`, incremental
`acceptance-diagnostics.jsonl` and `rejection-warnings.jsonl` with durable high-water
and pending-row cursors. Warnings identify reason, rejected/matching game and source
IDs, both splits, and full trajectory hash. Counts break down by reason, policy,
split and source. Interval and cumulative acceptance are
`accepted / (accepted + duplicate-rejected)`; reused identities, unfinished attempts,
interruptions, other failures and query retries stay separate. Zero retained query
failures establishes zero retries; otherwise use finalized execution counters and
retain unavailable live retry counts explicitly. Warnings have stable event IDs.
Low acceptance is diagnostic only, with no invented stop threshold or sampling
change. Intermediate-board overlap remains a separate selection audit.
