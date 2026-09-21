---
description: Two-worker generation experiment with matched evidence and existing correctness guarantees.
scope: bounded performance implementation and experiment
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-DATA-009
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, performance
depends_on: AB-LEARN-008
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-DATA-009 — Two-worker generation experiment

## Intent

Test whether two independent single-thread teacher/game workers improve verified
retained generation throughput over identical serial work. The user selected a
bounded experiment, not a production scheduler. The prior profile attributes
about 90% of teacher-workload wall time to external response waits. Earlier teacher
query prototypes omitted current generation/persistence and do not settle this.

## Acceptance Criteria

- Use production Python-reference generation and two fixed, independent source
  partitions with separate collections. Preserve source IDs and per-source game
  indices; never share a writable SQLite collection.
- Compare every shard's normalized trajectories, decisions, selections and labels
  between schedules. Check combined identities and exact counts; validate one
  interrupted/reopened worker and completed-run no-op reuse separately.
- Measure complete verified job wall time, retained positions/s, total worker and
  teacher CPU, and sampled sum of process-tree RSS with explicit accounting limits.
- Preserve Python as default, all semantic identities, guard/error precedence,
  exact actions/labels, per-move SQLite WAL/FULL and existing recovery guarantees.
- Fresh workers and collections; no builds/tests during confirmation timing.
  Freeze both implementation trees, native binaries, configs and study source.
- Retain incomplete/failed attempts, independent replay/label/SQLite checks and
  normalized equality. Stop on mismatch; at most 180 seconds per worker and
  20 minutes per comparison. No strength or broad-population performance claim.

## Context and Trade-offs

Freeze the existing 16-game, four-development-family, 96-additional-ply, seed-17,
10k-node plausible actor and 10k/100k supervision workload. Split whole sources
alternately into two eight-game shards with one-thread teachers. Three alternating
serial/two-worker pairs use the same two shard configs. Primary wall time includes
worker startup, generation and independent verification; storage remains WAL/FULL.
A median throughput gain of at least 1.3x, a win in every pair, exact equality and
recovery checks justify proposing supported parallel generation next. This study
does not merge collections, export training data or establish optimal worker count.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User accepted option 1 and authorized implementation and bounded comparison. |
| 2026-09-21 | GPT-6 | wip | done | Three matched serial/two-worker pairs and separate interrupted-worker recovery checks pass. |

## Implementation Ledger

- **2026-09-21 — decision:** Option 1 locked. Preserve settled contracts; native
  scalar optimization and isolated two-worker measurement have separate adoption
  decisions. Baseline b1eff30 source and native binary archived before editing.
  **Review:** not-required.


- **2026-09-21 — finding:** Two workers achieve 1.770x median paired throughput, winning every pair with identical 16 games/1402 plies/169 selections and 545 retained analysis records. Sampled summed RSS rises from 650.9 to 1210.1 MiB; generation worker/child CPU rises about 7%.
  [Report](../../reports/2026-09-21-generation-optimization.md) and
  [compact results](../../../data/evaluation/generation-optimization-20260921.json)
  retain cell values, limits and raw evidence hashes. **Review:** not-required.
- **2026-09-21 — verification:** ASan/UBSan and all real-allocation failure probes
  pass; `make test-native` passes isolated source/wheel and generation/HTTP checks.
  `make check` passes 824 Python tests (one MPS skip), five frontend tests and all
  lint/docs/API/type/build gates. Seven focused study tests pass after final cleanup.
  One real-teacher shard resumes after an interruption, matches clean completed
  outputs, retains the interrupted attempt and reuses all eight games on rerun.
  Frozen sources/binaries and all normalized comparisons verify.
  **Review:** not-required.
- **2026-09-21 — decision:** The 1.3x advancement gate passes. Propose opt-in production parallel generation next after deciding combined-output and recovery ownership. This study creates no production scheduler. **Review:** not-required.
- **2026-09-21 — deviation:** Final review hardened a coordinator timeout-cleanup
  race when a worker exits before SIGKILL. Focused coverage passes; original timed
  controllers remain frozen and successful-path measurements are unchanged.
  **Review:** not-required.

```experiment
{
  "schema_version": 1,
  "id": "generation-workers-20260921",
  "title": "Two-worker generation experiment",
  "question": "Test whether two independent single-thread teacher/game workers improve verified",
  "kind": "performance",
  "topics": [
    "teacher",
    "workers",
    "generation",
    "throughput"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Freeze the existing 16-game, four-development-family, 96-additional-ply, seed-17,\n10k-node plausible actor and 10k/100k supervision workload. Split whole sources\nalternately into two eight-game shards with one-thread teachers. Three alternating\nserial/two-worker pairs use the same two shard configs. Primary wall time includes\nworker startup, generation and independent verification; storage remains WAL/FULL.\nA median throughput gain of at least 1.3x, a win in every pair, exact equality and\nrecovery checks justify proposing supported parallel generation next. This study\ndoes not merge collections, export training data or establish optimal worker count.",
  "limitations": "One machine and a bounded fixed workload. Timing repeats are not independent datasets.",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "generation-profile-20260921",
      "relationship": "extends",
      "contribution": "Test whether two independent single-thread teacher/game workers improve verified"
    }
  ],
  "novelty": "Test whether two independent single-thread teacher/game workers improve verified"
}
```


```experiment
{
  "schema_version": 1,
  "id": "generation-workers-20260921",
  "title": "Two-worker generation experiment",
  "question": "Test whether two independent single-thread teacher/game workers improve verified",
  "kind": "performance",
  "topics": [
    "teacher",
    "workers",
    "generation",
    "throughput"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Three paired serial/two-worker rounds give 1.815x, 1.765x and 1.770x throughput, median 1.770x, with identical 16 games/1402 plies/169 selections/545 retained analyses and clean interrupted-worker recovery. Median summed sampled RSS grows 650.9 to 1210.1 MiB; generation CPU rises about 7%.",
  "conditions": "Freeze the existing 16-game, four-development-family, 96-additional-ply, seed-17,\n10k-node plausible actor and 10k/100k supervision workload. Split whole sources\nalternately into two eight-game shards with one-thread teachers. Three alternating\nserial/two-worker pairs use the same two shard configs. Primary wall time includes\nworker startup, generation and independent verification; storage remains WAL/FULL.\nA median throughput gain of at least 1.3x, a win in every pair, exact equality and\nrecovery checks justify proposing supported parallel generation next. This study\ndoes not merge collections, export training data or establish optimal worker count.",
  "limitations": "One local macOS machine, fixed source families and three timing replications, not population or strength evidence. No CPU affinity/clock control or local Linux run. Teacher child CPU varies. RSS sampling can double-count shared pages and miss short peaks; timing includes worker verification but combined audit is separate. Production multiworker merge/recovery remains unimplemented.",
  "decision": "The predeclared 1.3x advancement gate passes. Propose opt-in production parallel generation after choosing combined-output and recovery ownership. Keep this as an isolated-collection experiment, with no production scheduler or weakened durability.",
  "revisit": "Decide production collection combination and recovery semantics, then implement opt-in parallel generation with equivalent outputs and failure tests; test larger worker counts separately.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-generation-optimization.md",
      "role": "report",
      "sha256": "dfc92aa5c12de48f5d30417957d97e1af79576fc686a82c3099772f9f03e9811"
    },
    {
      "path": "data/evaluation/generation-optimization-20260921.json",
      "role": "results",
      "sha256": "736b28a0e933bd59319c66b3e524c3875cab6bd95b77395149a92938f4b0b827"
    },
    {
      "path": "artifacts/generation-optimization-20260921/checks/verification.json",
      "role": "run",
      "sha256": "c67bede7e9725edb690cb94b5b78270ef524b27ce0d4ddf5191f4d1dbba8fb33"
    },
    {
      "path": "artifacts/generation-optimization-20260921/baseline.json",
      "role": "source",
      "sha256": "01de6cca4cf61f5cf88318564a74bf919efbf2f23d2a64b6de209aecb09d9ce2"
    },
    {
      "path": "artifacts/generation-optimization-20260921/candidate/manifest.json",
      "role": "source",
      "sha256": "4f249b84bc391879c54bbd8b7a1c6547ea0a603463baad3303b81b990fcb7d0e"
    },
    {
      "path": "artifacts/generation-optimization-20260921/workers-01/summary.json",
      "role": "results",
      "sha256": "3e1b9982677848c76e4f91fba8704f23ce5e50a50ee712cec2afbffb2a4f1b1d"
    },
    {
      "path": "artifacts/generation-optimization-20260921/workers-01/runtime-manifests.json",
      "role": "source",
      "sha256": "f0993744cf73708b084bd773269ed18ba0555adcc8db694b16d21f9a76892f2c"
    },
    {
      "path": "artifacts/generation-optimization-20260921/workers-01/controller.py",
      "role": "source",
      "sha256": "506fea737f0a92e43847b638c1cad8bbbb49fc002f8d6b10cf55487f604577f5"
    },
    {
      "path": "artifacts/generation-optimization-20260921/workers-01/checks.py",
      "role": "source",
      "sha256": "12a6a1679386b47c68ee847973be26579e147db7c5abfcd125640a6fa0149b68"
    },
    {
      "path": "artifacts/generation-optimization-20260921/workers-01/shard-0.json",
      "role": "config",
      "sha256": "75bfddc660f9c153db0fd75c1805f7d262250be68f1f1620c1d4c4193779382d"
    },
    {
      "path": "artifacts/generation-optimization-20260921/workers-01/shard-1.json",
      "role": "config",
      "sha256": "33cd79d0c6e158e02731f5458215f9c6e7036086b6386abd364473116da83d81"
    },
    {
      "path": "artifacts/generation-optimization-20260921/recovery-01/summary.json",
      "role": "results",
      "sha256": "8ecc5bf2e98f473f793a66da172f99da9d84bb1343d037d9a707217ffa5350fb"
    },
    {
      "path": "artifacts/generation-optimization-20260921/recovery-01/recovery.py",
      "role": "source",
      "sha256": "88a16c226e7db9c32b418f894637216ab4600f777d58ec0ffc0c6990d423b42d"
    }
  ],
  "prior_work": [
    {
      "id": "generation-profile-20260921",
      "relationship": "extends",
      "contribution": "Test whether two independent single-thread teacher/game workers improve verified"
    },
    {
      "id": "teacher-throughput-20260909",
      "relationship": "extends",
      "contribution": "Measures full policy generation, persistence and independent output verification instead of only teacher queries."
    }
  ],
  "novelty": "Test whether two independent single-thread teacher/game workers improve verified"
}
```
