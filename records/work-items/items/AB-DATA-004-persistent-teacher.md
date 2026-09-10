---
description: Integrate opt-in persistent teacher execution and measure full preparation equivalence and throughput.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-DATA-004
work_status: done
work_kind: build
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-007
residual_of: none
residual_items: none
---

# AB-DATA-004 — Persistent teacher preparation

## Intent

Reuse one pinned teacher process during configured preparation to amortize startup
and file hashing while preserving the existing supervision and referee boundaries.

## Acceptance Criteria

- Opt-in persistent execution; omitted configuration retains fresh-process behavior.
- One sequential process, same engine/network for actor and supervisor, independent
  query budgets, full history, fresh search state per query, bounded deadlines/output.
- Pin engine/network once per persistent preparation. Failures close/reap the
  process, do not retry, and retain the existing partial-generation evidence.
- Hermetic tests cover repeated queries, changed budgets/history, lifecycle,
  late-query failure, identity and preparation integration.
- Compare both execution modes through complete preparation with pinned local
  Pikafish. Preserve raw runs and compact results, separating timing from content.
- Run targeted checks and `make check`; update the owning guides.

## Context and Trade-offs

The [pilot advisory](../../reports/2026-09-09-teacher-generation-advisory.md)
measured prototype query throughput, not retained examples per preparation second.
This is a performance experiment, not a teacher-quality or training experiment.
No pool, new supervision target, trainer integration or default change is included.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | wip | User accepted the bounded persistent-session recommendation. |
| 2026-09-09 | Codex | wip | done | Session/config integration, failure tests, six real preparations and full checks passed; results below. |

## Implementation Ledger

### 2026-09-09 — decision: comparison protocol before execution

- Question: does process reuse reduce complete preparation cost without changing
  supervision, sources or frozen selection? Expect a speedup from amortized engine
  startup/network hashing; assembly may limit end-to-end benefit.
- Comparison: tracked two-mode preparation recipe, pinned engine/network and
  unchanged budgets, seeds, exclusions and quotas. Run three paired repetitions,
  alternating fresh/persistent order; each run gets a fresh output directory.
- Budget: existing 120-second generation allowance per run; six preparations,
  stop on failure or content mismatch. No training or parameter tuning.
- Proof: exact source/selection/analysis agreement excluding elapsed time and UCI time/nps values; report every mismatch. Compare completed
  retained examples divided by full preparation wall time, including startup,
  validation, checkpointing, assembly and process cleanup. Save all durations,
  output hashes and resolved configs. Timing is descriptive on this machine.
- Decision rule: retain the opt-in implementation only if equivalence passes;
  recommend its use on comparable workloads if all three paired wall times improve.
  Defaults stay fresh regardless of the pilot outcome.
- Follow-up: execute after lifecycle tests pass and record results and limitations.
- Review: not-required; user authorized this bounded implementation and comparison.


### 2026-09-09 — verification: session and preparation integration

- Added a shared lazy `TeacherSession` analysis path; existing `analyze` opens and
  closes it per call. Configured preparation opts in with
  `teacher_process: "persistent"`; old recipes remain fresh.
- A file-bound identity is verified once and reused for generation specifications
  and analysis. Actor/supervisor budgets remain independent; distinct files or
  conflicting pins are rejected before preparation output creation.
- Tests exercise same-PID reuse, full-history and budget changes, identity hashing
  once, per-query output/deadline renewal, timeout/crash/flood/illegal-move cleanup,
  cancellation, no retries, exact prepared-content equality and retained partial
  evidence after a later query fails. No worker pool or trainer change.
- Full `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed 382 Python
  tests with one opt-in MPS skip, three browser lifecycle tests, production build,
  lint and docs. The subsequently added cancellation test is verified separately.
- Follow-up: apply the opt-in setting to comparable preparations; keep defaults
  fresh and reassess before adding concurrency or changing search semantics.
- Review: not-required; bounded implementation and verification.

### 2026-09-09 — finding: full preparation equivalence and speedup

All six preparations completed: four source trajectories, sixteen library examples
and eight retained examples per run, including random and teacher-guided modes.
[Saved results](../../../data/experiments/learning/history/persistent-teacher-v1.json)
include all times, resolved recipe, output hashes and executed-source hashes.
Raw configs, libraries, datasets and source copies remain local under
`artifacts/learning/persistent-teacher-v1/`; Git does not contain those raw artifacts.
The run truthfully records an uncommitted checkout and retains its executed sources.

| Pair | Fresh seconds | Persistent seconds | Speedup | Content equal |
| --- | --- | --- | --- | --- |
| 0 | 4.997 | 0.227 | 22.04× | yes |
| 1 | 4.809 | 0.227 | 21.21× | yes |
| 2 | 4.829 | 0.227 | 21.25× | yes |

- Median full preparation time: **4.829 → 0.227 seconds**. Median retained
  examples/s: **1.66 → 35.28**. Includes identity checks, engine execution,
  checkpointing, validation, assembly, persistence and cleanup.
- All six normalized datasets match exactly, including manifests, source histories,
  moves, scores/bounds, nodes, depths and non-timing UCI diagnostics. Only
  `analysis.elapsed_ms` and UCI `time`/`nps` values are excluded. No fingerprint
  exclusion was needed: semantic manifests match; raw dataset byte hashes differ.
  A separate raw-JSON comparison reproduced this result and the timing arithmetic.
- Decision: all pairs passed equivalence and improved time; retain and recommend
  opt-in reuse for this comparable shallow local workload. Defaults remain fresh.
- Limits: a small repeated recipe, shallow 1000-node/depth-3 teacher, warm Python
  caches and uncontrolled machine load. This does not establish general speedup,
  deeper-search equivalence, optimal workers, teacher quality or student strength.
- Follow-up: measure representative larger preparation workloads before generalizing
  or changing defaults; revisit parity when engine/settings change.
- Review: not-required; predeclared comparison completed without a failed attempt.


```experiment
{
  "schema_version": 1,
  "id": "persistent-teacher-v1",
  "title": "Persistent teacher full-preparation pilot",
  "question": "Does integrated persistent execution speed preparation while preserving normalized datasets?",
  "kind": "performance",
  "topics": [
    "teacher",
    "persistent process",
    "preparation throughput",
    "dataset equivalence"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "All three paired normalized datasets matched. Median preparation time fell from 4.829 to 0.227 seconds in the small pilot.",
  "conditions": "Three paired full preparations of the two-mode recipe at 1000 nodes/depth 3, fresh versus persistent teacher process.",
  "limitations": "Small shallow startup-sensitive workload; no teacher-quality or training gain; does not validate representative stronger-budget throughput.",
  "decision": "Keep persistent execution opt-in and fresh as default.",
  "revisit": "Representative distinct-position batches and stronger teacher budgets.",
  "evidence": [
    {
      "path": "data/experiments/learning/history/persistent-teacher-v1.json",
      "role": "results",
      "sha256": "9e6629bec56341b06d53ae9a447a9e8e7c76dc24763d31b1ae4b153ce6a6f989"
    }
  ],
  "prior_work": [
    {
      "id": "teacher-throughput-20260909",
      "relationship": "extends",
      "contribution": "Measures complete production preparation and normalized output equivalence, including work omitted by the query prototype."
    }
  ],
  "novelty": "Measures complete production preparation and normalized output equivalence, including work omitted by the query prototype."
}
```
