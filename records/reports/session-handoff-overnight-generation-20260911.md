---
description: Operate sequential hour-sized generation batches with cumulative resource accounting and bounded recovery.
scope: session handoff report
status: experimental
last_update: 2026-09-11
document_class: coordination
produced_by: "handoff@0.8.0 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# Session handoff — overnight generation

**Mode:** session · OPERATE
**Authorized transitions:** OPERATE → bounded operational FIX → VERIFY → OPERATE;
material scientific, storage-integrity or resource decisions → PAUSE for the user.
**Stop condition:** User asks to stop, a safety boundary is reached, or a material
fault needs a decision. Stop dispatching, preserve partial evidence, and report
completed work plus the exact next action. Do not treat finishing one batch as
finishing the session.

## Pickup instruction

The user authorized the **next session** to repeatedly launch roughly one-hour
batches and babysit them until they wake and ask it to stop. Start operating after
preflight; do not re-ask permission for each batch. This packet was prepared without
launching overnight work. “Spawn” here means sequential generation processes;
there is one collection writer, not parallel engine workers or new Codex tasks.

## Authorities

- [CLAUDE.md](../../CLAUDE.md): repository rules and required checks.
- [AB-DATA-008](../work-items/items/AB-DATA-008-generation-scaling-pilot.md):
  generation decisions, pilot evidence and remaining scientific work.
- [Generation guide](../../docs/data-generation.md): executable policy/resume contracts.
- [ADR-0008](../../docs/adr/0008-sqlite-collection-parquet-snapshots.md) and
  [collection guide](../../src/qi/training_data/README.md): SQLite/JSONB and frozen snapshots.
- [Measured resource results](../../data/experiments/learning/history/generation-resource-v1.json)
  and [original overnight plan](../../data/experiments/learning/generation-resource-v1/overnight-plan-v1.json).
  The original 9,000-game/10-hour file is a frozen calibration proposal. The newer
  authorization changes dispatch cadence and continuation, not teacher/sampling settings.
- [AB-EVAL-004](../work-items/items/AB-EVAL-004-heldout-methodology.md): later full-game
  Elo protocol. [AB-LEARN-010](../work-items/items/AB-LEARN-010-snapshot-training-protocol.md):
  later snapshot optimizer integration. Neither is part of this overnight operation.

## State

- Infrastructure is committed as `9ab7e1a`; generation, tests, recipes and measured
  evidence as `4ea57b1`. No outstanding parallel claims or requested merge remain.
- Seven real-engine cells completed: 512 games and 14,798 retained successful
  analyses; replay, SQL integrity, checkpoint/reopen and selected-only export were
  exercised. Long plausible games produced 21/32 checkmate or stalemate outcomes;
  the other 11 reached the referee's 300-ply cap. These are not Elo results.
- Fixed-horizon writes/game grew 10–12% from 32 to 128 games; WAL peaked near
  4.3MB and sampled runner plus teacher RSS stayed below 604MB. OS writes were
  17–27 times closed database size. Larger-pool behavior remains unverified.
- Verification at closeout: `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check`
  passed 552 Python tests, one opt-in MPS skip, five browser tests, Ruff, docs,
  catalog and both browser builds. The batch-construction snippet below was checked
  for disjoint source IDs and passed pinned-asset CLI preview without generation.
- Left: actually run/monitor batches, accumulate verified evidence, assess saturation
  and I/O, then freeze split exclusions and export before training. The paired 1M-node
  quality-reference study and playing-strength claims remain outside this operation.
- Open decisions do not block generation: final training size, model scaling and
  full-game rating protocol. Neither 1M samples nor 9,000 games is an overnight quota.

## Preflight and batch construction

1. Work in `/Users/zhangqy/pkgs/qi`. Inspect HEAD/status and any existing overnight
   ledger/process before dispatch. Never start a second writer or reuse an output
   directory speculatively. Teacher assets are already local; preview verifies hashes.
2. Keep a durable `artifacts/learning/overnight-batches-20260911/ledger.json` and
   append-only operator journal. Record authorization, running/paused/stopped state,
   batch/config hash, source-block interval, implementation hash, output/execution
   paths, owned PID/tool session, times, exit reason, validation cursors and cumulative
   resource totals. Reconcile existing executions before resuming after a context cut.
3. Register the larger operational study in AB-DATA-008/catalog before its first
   generation. Preserve the completed pilot entries and hashes. Derived batch recipes
   and raw results live under ignored artifacts; retain compact assessed results in
   the tracked experiment history at closeout.
4. Use the snippet below once for each **new** batch. Batch 0 covers blocks 0–9,
   batch 1 covers 10–19, etc. It keeps 800 plausible / 100 intervention / 100 random
   games and 900 train / 100 validation games per batch. Blocks beyond 89 are permitted
   by the repeated-batch authorization, subject to the same cumulative safety envelope.
   Do not reuse earlier source IDs to manufacture apparently new data.

```python
# Run with .venv/bin/python from the repository root. Set from the reconciled ledger.
import copy
import json
from pathlib import Path

from qi.training_data.generation_runner import PolicyGenerationConfig

batch_index = 0
assert isinstance(batch_index, int) and batch_index >= 0
root = Path("artifacts/learning/overnight-batches-20260911").resolve()
path = Path("data/experiments/learning/generation-resource-v1/overnight-long-play-v1.json").resolve()
base = PolicyGenerationConfig.model_validate_json(path.read_text()).resolve(path.parent).model_dump()
prototypes = copy.deepcopy(base["sources"][:3])
assert [s["actor"]["mode"] for s in prototypes] == ["plausible", "intervention", "random"]
base["name"] = f"overnight-batch-{batch_index:04d}"
base["seconds"] = 3600.0
base["sources"] = []
for block in range(batch_index * 10, (batch_index + 1) * 10):
    for prototype in prototypes:
        source = copy.deepcopy(prototype)
        source["id"] = f'{source["actor"]["mode"]}-block-{block:03d}'
        source["split"] = "validation" if block % 10 == 0 else "train"
        base["sources"].append(source)
config = PolicyGenerationConfig.model_validate(base)
assert sum(s.games for s in config.sources) == 1000
assert sum(s.games for s in config.sources if s.split == "validation") == 100
root.mkdir(parents=True, exist_ok=True)
recipe = root / f"batch-{batch_index:04d}.json"
with recipe.open("x") as stream:
    stream.write(json.dumps(config.model_dump(), indent=2) + "\n")
print(recipe)
```

The source IDs preserve the template's actor/sampler seeds. Paths are resolved
before relocating the recipe. Actor nodes remain 10k; selected states receive
10k and 100k labels. Keep the 300-ply ceiling, candidate policy, intervention
window, audit stride, phase caps 1/8/8 and spacing four unchanged.

For batch 0, preview this command, then run it without `--preview` after the
cumulative-budget check below. Use the corresponding number for later batches:

```bash
.venv/bin/python scripts/run_generation_pilot.py \
  --config artifacts/learning/overnight-batches-20260911/batch-0000.json \
  --output artifacts/learning/overnight-batches-20260911/batch-0000 \
  --collection artifacts/learning/overnight-batches-20260911/collection.sqlite \
  --max-write-gb 20 --max-rss-mb 1500 --min-free-gb 30 \
  --preview
```

The common collection's parent must exist before launching; the snippet creates
it. Capture the owned process/session when launching, and preserve stdout/stderr
in that batch's journal. Do not wrap this in a blind infinite shell loop. The
operator must review each outcome before dispatching the next invocation.

## Budget and monitoring loop

- Plan around 40–60 minutes per 1,000-game batch from the small-pool rates, with
  a 3,600-second generation limit. Actual time and sample yield can differ. A
  completed smaller-duration batch can be followed immediately by the next;
  do not pad the hour with unnecessary searches or enlarge its frozen recipe.
- **Session-wide allowance: 150 decimal GB of runner OS-attributed writes.**
  Each invocation, including a resume, has a 20GB runner guard. Require at least
  **21GB remaining** before dispatch, reserving 1GB for archive/closeout and
  sampled-guard overshoot. Otherwise pause; do not reset the cumulative total or
  raise a guard to spend the remaining allowance. RSS cap is 1,500MB; keep 30GB
  free disk space throughout. These are sampled limits, not kernel hard caps.
- Bill each distinct execution once using the larger of final
  `resources.disk_write_bytes` and `resources.process.disk_write_bytes` from its
  summary. The latter is the fresh process's lifetime counter and includes work
  before probe initialization. On abnormal exit preserve the latest observed
  counter; missing final accounting is an uncertainty to resolve or conservatively
  charge the invocation's full 21GB before continuing. Never count only the latest
  execution of a resumed batch. Account validation/operator process writes too;
  these counters are not whole-machine or physical SSD wear measurements.
- Inspect the first 32 completed games, then approximately every five minutes:
  execution `progress.json`, journal advancement, owned process liveness, disk
  headroom, RSS and DB/WAL sizes. Between inspections use interruptible waits of
  at most 60 seconds so user stop requests remain responsive. Report meaningful
  progress/faults; do not dump per-game logs into chat.
- Watch interval writes per **new completed game** and throughput by policy, not
  just cumulative averages or reused-game events. Investigate sustained >2x
  writes/game growth at a matched policy/horizon, >100x write/DB amplification,
  or WAL exceeding 64MB and still growing across two observations. WAL 64MB is
  a conservative operational investigation threshold, not a measured failure point.
  Stop the writer before expensive diagnosis if growth is rapid. Do not weaken
  `synchronous=FULL`, checkpoint continuously, or scan the full DB every poll.
- If progress stalls for two minutes, inspect the current process and last event
  before retrying: progress is written per game, so a slow game is not itself a
  deadlock. Establish whether searches/CPU or validation are advancing. Unexplained
  hangs, repeated engine failures or unavailable guard counters pause dispatch.

## Batch boundary, resume and validation

1. Wait for the owned process to exit; read `latest.json`, its execution summary,
   events and relevant SQL run/game statuses. A `shortfall` summary with
   `generation_status: complete` means all requested games finished with sampling
   shortfalls. Never reinterpret it as missing game work or refill phase quotas.
2. On the ordinary time limit, verify the recorded deadline stop and unchanged
   source/recipe, then repeat the **identical command with `--resume`**, subject
   to the same 21GB remaining-budget check. Completed games are reused; an
   unfinished game is a separate retained attempt and regenerates from its start.
   Each resume has its own hour and resource charge. One boundary retry is routine;
   if it adds no completed game, stop for diagnosis instead of repeatedly retrying.
3. Validate newly completed trajectories and new successful analyses once, in
   bounded reads, borrowing invariants from `scripts/benchmark_generation.py:verify`.
   Use primary-key ranges and persisted cursors; include previously running rows
   in the next pass. Check legal replay, played decisions, state/spec identity,
   requested = selected + shortfall and complete-game selected counts. Report
   failed/incomplete-game retained rows separately. Do not call that pilot verifier
   unchanged on the shared collection: it assumes one fresh cell and scans all rows.
4. Close readers after each bounded check. At the first completed batch and final
   stop run SQLite integrity/foreign-key checks with no writer active, then reopen
   read-only. Avoid a full verification/export of all earlier batches every hour.
   At other boundaries verify new rows and record elapsed/read/write costs. Full
   cross-split overlap/dedup queries belong at the final selection audit, not every poll.
5. Record outcomes (including referee cap draws), policies, splits, phases,
   selected occurrences, query counts/budgets and failure/shortfall counts. Count
   global unique board-and-turn inputs separately at bounded checkpoints; summing
   per-batch uniques overcounts. Persist validation results before advancing.
6. Continue to the next unused batch only after accounting and checks pass. Stay
   active and supervise; if monitoring must survive a turn boundary, use the app's
   supported thread heartbeat, inspect/update any existing matching automation,
   and make it honor ledger paused/stopped state and the single-writer rule.
   Do not claim supervision continues after ending a turn without a wakeup mechanism.

## Quick fix versus pause

**Routine actions already authorized:** exact-config deadline resume, the runner's
one fresh-session retry for transient teacher timeout/exit, correcting a launcher
path, and a small independently testable logging/accounting defect. Preserve the
failed execution, stop its writer, reproduce the defect, apply the narrow fix,
run focused tests plus required repo checks, commit it, and record the new version
before dispatch. Budget time spent diagnosing and validating in the journal.

**Pause and wait for the user:** illegal moves or replay/spec/hash mismatches,
corruption or unclear data validity, repeated failures after the built-in retry,
rapid unexplained I/O/memory growth, exhausted/uncertain resource allowance,
source-family/split conflicts, or any fix requiring changed generation settings,
engine budgets, schema/durability, exclusions or broader refactoring. A resource
stop is not permission to relax the resource guard. Never delete offending records
or label them successful to resume. Leave a concise incident with identifiers,
evidence, impact, candidate actions and the decision needed.

Changing `src/qi` changes the implementation hash and creates a different logical
run. Do not blindly resume a partly completed batch after such a fix: that could
regenerate all completed trajectories in a new run. Prefer a fix that preserves
the tested implementation; otherwise pause to reconcile retained source identities
and the remaining work before restarting. A changed hash is not an empty collection.

## User stop and final handoff

On “stop,” mark the ledger stopped first and prevent future dispatch. Interrupt
only the known owned runner with SIGINT (the runner records the interrupted attempt
and closes its engine); inspect its actual exit and preserve any abnormal shutdown
state. Do not signal unrelated processes. Pause/remove only a monitor created for
this operation. If no writer is active, do not start another batch to finish a quota.

Summarize elapsed time, completed/partial batches and games, selected/unique inputs,
phase/outcome mix, resource totals, failures and SQL verification, with exact local
paths. Save compact evidence and update AB-DATA-008/catalog. Before any subsequent
training, freeze data-only shared-input exclusions and ambiguity decisions, verify
quota feasibility, then export a selected-only immutable snapshot. Training and
full-game Elo evaluation await their separate protocol/work items.

## Suggested skills and forbidden actions

Use `experiment` for predeclared operation and assessed evidence; `handoff` for
context cuts or incidents. Use `grilling` only for a material unresolved decision.
Do not introduce parallel writers, replay-backed child policies, new teacher
budgets, model fitting, Elo runs, destructive cleanup, automatic artifact deletion,
or a different sampling mixture during this operation. Keep all failed evidence.
