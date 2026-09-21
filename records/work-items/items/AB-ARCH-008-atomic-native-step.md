---
description: Atomic native scalar stepping with matched evidence and existing correctness guarantees.
scope: bounded performance implementation and experiment
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-008
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, performance
depends_on: AB-LEARN-008
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-008 — Atomic native scalar stepping

## Intent

Implement scalar stepping without copying the entire history/repetition map.
The user selected option 1: native optimization plus a bounded two-worker study.
[AB-LEARN-008](AB-LEARN-008-experiment-performance.md) measured 56.1% of native-core
profile time in state copying/release, while full teacher generation gained only
1.039x from native execution. This tests the identified native implementation cost;
it does not promise that component savings dominate total generation time.

## Acceptance Criteria

- Prepare next board/key, history capacity and one repetition entry before a
  nonthrowing semantic commit. Allocation failure preserves logical game state.
- Inject failures at every allocation point on fresh, growing and repeated-state
  paths; compare state and successful retries. Preserve all-or-nothing native
  batch staging; no batch optimization or GIL change is planned.
- Differential conformance, installed native wheel checks, ASan/UBSan and the
  application gate pass before adopting the candidate.
- Preserve Python as default, all semantic identities, guard/error precedence,
  exact actions/labels, per-move SQLite WAL/FULL and existing recovery guarantees.
- Fresh workers and collections; no builds/tests during confirmation timing.
  Freeze both implementation trees, native binaries, configs and study source.
- Retain incomplete/failed attempts, independent replay/label/SQLite checks and
  normalized equality. Stop on mismatch; at most 180 seconds per worker and
  20 minutes per comparison. No strength or broad-population performance claim.

## Context and Trade-offs

Three alternating fresh-process rounds compare archived b1eff30 native, candidate
native and candidate Python on the 64-game/17169-ply controlled workload, and the
16-game/four-family teacher workload from the profiling study. Exact-action
comparisons replay the same controlled games with full observations, three
repetitions per cell. Candidate action throughput must improve at least 20% over
baseline native; flag a median pipeline regression above 5% for investigation.
Adoption requires correctness and repeatable component improvement; teacher noise
is reported separately. Backend-default promotion is outside scope.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User accepted option 1 and authorized implementation and bounded comparison. |
| 2026-09-21 | GPT-6 | wip | done | Atomic scalar stepping passes conformance, fault injection, sanitizer and package/application gates with a measured gain. |

## Implementation Ledger

- **2026-09-21 — decision:** Option 1 locked. Preserve settled contracts; native
  scalar optimization and isolated two-worker measurement have separate adoption
  decisions. Baseline b1eff30 source and native binary archived before editing.
  **Review:** not-required.


- **2026-09-21 — finding:** Matched action throughput improves 1.882x over old native and 2.757x over Python. Controlled pipeline throughput improves 1.086x; teacher throughput is 0.986x old native with variable child search costs. Every normalized result matches.
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
- **2026-09-21 — decision:** Adopt scalar preparation. Keep batch staging, Python default and per-move WAL/FULL. The measured full pipelines do not satisfy native default promotion. **Review:** not-required.
- **2026-09-21 — deviation:** Final review hardened a coordinator timeout-cleanup
  race when a worker exits before SIGKILL. Focused coverage passes; original timed
  controllers remain frozen and successful-path measurements are unchanged.
  **Review:** not-required.

```experiment
{
  "schema_version": 1,
  "id": "native-atomic-step-20260921",
  "title": "Atomic native scalar stepping",
  "question": "Implement scalar stepping without copying the entire history/repetition map.",
  "kind": "performance",
  "topics": [
    "native",
    "atomicity",
    "generation",
    "throughput"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Three alternating fresh-process rounds compare archived b1eff30 native, candidate\nnative and candidate Python on the 64-game/17169-ply controlled workload, and the\n16-game/four-family teacher workload from the profiling study. Exact-action\ncomparisons replay the same controlled games with full observations, three\nrepetitions per cell. Candidate action throughput must improve at least 20% over\nbaseline native; flag a median pipeline regression above 5% for investigation.\nAdoption requires correctness and repeatable component improvement; teacher noise\nis reported separately. Backend-default promotion is outside scope.",
  "limitations": "One machine and a bounded fixed workload. Timing repeats are not independent datasets.",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "generation-profile-20260921",
      "relationship": "extends",
      "contribution": "Implement scalar stepping without copying the entire history/repetition map."
    }
  ],
  "novelty": "Implement scalar stepping without copying the entire history/repetition map."
}
```


```experiment
{
  "schema_version": 1,
  "id": "native-atomic-step-20260921",
  "title": "Atomic native scalar stepping",
  "question": "Implement scalar stepping without copying the entire history/repetition map.",
  "kind": "performance",
  "topics": [
    "native",
    "atomicity",
    "generation",
    "throughput"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Safe scalar preparation improves matched-action throughput 1.882x over old native and 2.757x over Python, with exact states/history. Controlled generation improves 1.086x over old native. Teacher throughput is 0.986x with one slower child-search round retained. All conformance, allocation-failure, sanitizer and package/application checks pass.",
  "conditions": "Three alternating fresh-process rounds compare archived b1eff30 native, candidate\nnative and candidate Python on the 64-game/17169-ply controlled workload, and the\n16-game/four-family teacher workload from the profiling study. Exact-action\ncomparisons replay the same controlled games with full observations, three\nrepetitions per cell. Candidate action throughput must improve at least 20% over\nbaseline native; flag a median pipeline regression above 5% for investigation.\nAdoption requires correctness and repeatable component improvement; teacher noise\nis reported separately. Backend-default promotion is outside scope.",
  "limitations": "One local macOS machine, fixed source families and three timing replications, not population or strength evidence. No CPU affinity/clock control or local Linux run. Teacher child CPU varies. RSS sampling can double-count shared pages and miss short peaks; timing includes worker verification but combined audit is separate. Production multiworker merge/recovery remains unimplemented.",
  "decision": "Adopt the scalar optimization with existing logical-state atomicity. Keep native batch staging, Python default and WAL/FULL. No teacher speedup or backend-default promotion.",
  "revisit": "Reprofile a changed workload before further core work; do not infer teacher throughput from the component gain.",
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
      "path": "artifacts/generation-optimization-20260921/native-01/summary.json",
      "role": "results",
      "sha256": "7249e9d4b6ca2cb16a413fc8993d2d9d2f7985cc20906bd979571b54dfd626b6"
    },
    {
      "path": "artifacts/generation-optimization-20260921/native-01/runtime-manifests.json",
      "role": "source",
      "sha256": "00382927cc20136f6f9e5d4de2e6dc2d30e5555505ca85f2179a75d1eea6eca8"
    },
    {
      "path": "artifacts/generation-optimization-20260921/native-01/controller.py",
      "role": "source",
      "sha256": "506fea737f0a92e43847b638c1cad8bbbb49fc002f8d6b10cf55487f604577f5"
    }
  ],
  "prior_work": [
    {
      "id": "generation-profile-20260921",
      "relationship": "extends",
      "contribution": "Implement scalar stepping without copying the entire history/repetition map."
    },
    {
      "id": "native-generation-20260921",
      "relationship": "extends",
      "contribution": "Preserves native scalar and batch contracts while removing scalar full-state copying."
    }
  ],
  "novelty": "Implement scalar stepping without copying the entire history/repetition map."
}
```
