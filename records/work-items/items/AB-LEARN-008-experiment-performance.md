---
description: Profile a representative experiment before selecting a parity-preserving optimization.
scope: backlog item
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-LEARN-008
work_status: done
work_kind: research
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-LEARN-008 — Profile experiment costs

## Intent

Find the next useful performance improvement using one bounded representative
workload under the [efficiency campaign](../../campaigns/experiment-efficiency.md).

## Acceptance Criteria

- Freeze workload, source/teacher/training settings, hardware and measurement
  budget before running; retain phase timings, throughput and peak memory.
- Separate generation, teacher calls, validation/persistence, input preparation,
  fitting and reporting costs where applicable.
- Rank measured bottlenecks and propose one independently testable build slice
  with output-equivalence criteria; record an inconclusive result if warranted.
- Keep raw measurements and limitations. Do not claim a speedup from fewer
  examples, weaker validation or changed training semantics.

## Context and Trade-offs

Cumulative library checkpointing and repeated report inference are review
candidates. Reuse, chunking, checkpoint cadence, sharding and concurrency need
measurement and explicit integrity boundaries before implementation. This item
does not authorize a large run or a minibatch-training experiment.

## Predeclared generation diagnosis, 2026-09-21

The authorized question is why the C++ game loop advantage shrinks in policy
generation, extending `incremental-append-20260921` and the native integration
series. This measures current execution without changing production behavior.
Expected contributors are durable SQLite writes, teacher work, Python boundary
overhead, and full native state copying for atomic steps. Existing phase counters
are not comparable engine timers: Python computes next-position legality lazily,
while native observations materialize it during the step.

- Freeze the current runtime, native binary, inputs and diagnostic harness.
  Primary timings use fresh serial workers, cold reference caches, disposable
  collections, WAL/FULL and identical actors/labels. No concurrent tests/builds.
- Three alternating Python/native pairs on the prior 64-game, 300-ply controlled
  fixture workload; three pairs on 16 plausible-actor games over four distinct
  development-book families, 96 additional plies, 10k-node/three-candidate actor,
  10k and 100k supervision, one teacher thread, seed 17. These are representative
  settings, not a representative population or strength evaluation.
- Independent post-timing Python replay, label validation, SQLite integrity and
  normalized semantic comparison. Preserve raw records, failures and partial
  attempts. Stop on mismatch; at most 180 seconds per worker and 20 minutes total
  timed execution. Never overwrite existing output directories.
- Separate Python/native profiles for both workloads, nested boundary timings,
  SQLite statement/transaction-exit timing and native step/inspect call counts.
  Record wall/worker CPU/child CPU and worker peak RSS before verification;
  child RSS is a separate maximum, not additive combined peak memory.
- Diagnostic-only matched runs may use SQLite synchronous=OFF on disposable
  collections to bound synchronization cost. This changes crash durability and
  is never an adoption candidate. Also measure Python's shared-trajectory adapter.
- Replay identical saved actions through direct Python, maintained native and
  raw native bindings; require matching states. A standalone C++ diagnostic may
  separate validation, state copy, transition and next legal generation, comparing
  production staged stepping with in-place execution solely to attribute cost.
  No weaker atomicity or recovery behavior enters the supported runtime.
- Rank observed costs and select one bounded next build slice with explicit
  correctness gates. Profile timings explain costs; unprofiled pairs establish
  throughput. Preserve the existing native advancement criterion and defaults.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture larger review work while completing bounded cleanup. |
| 2026-09-21 | GPT-6 | deferred | wip | User authorized profiling and investigation of the small integrated native speedup. |
| 2026-09-21 | GPT-6 | wip | done | Matched timing, profiles, native-core attribution and independent parity checks complete; next optimization ranked in the report. |

## Implementation Ledger

- **2026-09-21 — deviation:** The first controlled launcher completed its first
  worker, then failed while recording a relative output path. The retained
  `artifacts/generation-profile-20260921/controlled-01` is incomplete and excluded
  from paired results. The launcher now resolves the path; confirmation restarts
  in a fresh directory. Before profiling, nested timing records were also copied
  before verification so later checks cannot contaminate measured spans.
  **Review:** not-required.
- **2026-09-21 — finding:** Current native throughput is 1.097x Python on the
  controlled pipeline and 1.039x on the larger teacher workload. Identical-action
  full observations gain 1.475x; native full-state copying and old-state release
  account for 56.1% of the core diagnostic. In-place diagnostic execution gains
  2.394x but lacks allocation-failure atomicity. Controlled synchronization
  sensitivity and teacher wait/child CPU explain the remaining pipeline limits.
  The [report](../../reports/2026-09-21-generation-bottlenecks.md) owns the findings;
  [compact results](../../../data/evaluation/generation-profile-20260921.json)
  retain ratios, cells and raw evidence hashes. **Review:** not-required.
- **2026-09-21 — deviation:** The initial native-core driver discarded in-check
  results, allowing optimization to remove that work. `core-02` consumes it in
  a digest independently verified against Python; `core-01` remains superseded.
  Final harness preparation now creates its own fixture assets, removing reliance
  on a previous ignored run. Timed workers retain their frozen executed source.
  **Review:** not-required.
- **2026-09-21 — verification:** All workload semantic digests match across
  unprofiled, profiled, adapter and disposable synchronization runs. Independent
  replay/label/SQLite checks and the native-core oracle pass. Three harness tests
  plus 20 native/backend integration tests pass; `make test-native` separately
  passes isolated sdist/wheel checks and its 10 integration tests. The sandboxed
  package command could not access the uv cache; approved execution passed.
  Ruff, formatting, document checks and catalog/evidence verification are recorded
  with the final evidence receipt. **Review:** not-required.
- **2026-09-21 — handoff:** For teacher-generation throughput, compare two isolated
  independent workers against the same serial work. For native execution, target
  full-state copying while preserving allocation-failure atomicity. Keep every-move
  WAL/FULL and current defaults. Follow-up implementation is not part of this
  completed profiling task; the efficiency campaign routes the measured frontier.
  **Review:** not-required.
- **2026-09-21 — cleanup:** Reusable synchronous spans, resource accounting and
  cProfile export now live in `qi.profiling`; the
  [study directory](../../../data/experiments/generation_profile_v1/README.md)
  owns fixtures and native/SQLite diagnostics. Removed historical-script imports;
  scoped patches restore on failure, result snapshots exclude validation, failed
  sweeps retain partial evidence, arguments and deadlines are bounded, and native
  replay executes under `python -O`. Frozen measurements and sources are unchanged.
  **Review:** not-required; user authorized package integration and cleanup.
- **2026-09-21 — cleanup verification:** `make check` passes 818 Python tests
  (one optional MPS skip), five frontend tests, lint/docs/API/type checks and both
  production builds. Fifteen focused profiling tests pass, including native
  timing/profile parity and optimized-Python action replay. Rebuilt C++ diagnostics
  match the existing independent oracle in all three modes. An initial full check
  was invalidated by source edits during its continuation test; the saved configs
  differ only in implementation hash, and the fixed-source rerun passes.
  The catalog links the separate cleanup verification receipt. The only global
  evidence-hash issue remains unrelated AB-EVAL-005.
  **Review:** not-required.

```experiment
{
  "schema_version": 1,
  "id": "generation-profile-20260921",
  "title": "Generation bottleneck diagnosis",
  "question": "Why does native game execution barely accelerate full policy generation?",
  "kind": "performance",
  "topics": [
    "native",
    "throughput",
    "profile",
    "generation",
    "SQLite",
    "teacher",
    "state copy"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Three alternating fresh-process Python/native pairs on 64 controlled games and 16 teacher games from four development families; separate instrumented profiles, identical-action execution and disposable synchronization diagnostics. See owner protocol.",
  "limitations": "",
  "decision": "",
  "revisit": "",
  "evidence": [
    {
      "path": "artifacts/generation-profile-20260921/inputs/controlled.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/teacher.json",
      "role": "config",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "incremental-append-20260921",
      "relationship": "extends",
      "contribution": "Diagnoses remaining costs without changing production behavior."
    },
    {
      "id": "native-backends-20260921",
      "relationship": "challenges",
      "contribution": "Explains the difference between coarse native loop speed and maintained per-move integration."
    }
  ],
  "novelty": "Separates full pipeline costs, shared adapter overhead, native binding/core costs and teacher child resources after incremental append."
}
```


```experiment
{
  "schema_version": 1,
  "id": "generation-profile-20260921",
  "title": "Generation bottleneck diagnosis",
  "question": "Why does native game execution barely accelerate full policy generation?",
  "kind": "performance",
  "topics": [
    "native",
    "throughput",
    "profile",
    "generation",
    "SQLite",
    "teacher",
    "state copy"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Three paired rounds give 1.097x native throughput on 64 controlled games and 1.039x on 16 teacher games. Identical-action full observations give 1.475x. Copying/releasing full native state accounts for 56.1% of a core profile; in-place diagnostic execution is 2.394x faster. Controlled SQLite synchronization is costly; real-teacher response reads occupy about 90% of profiled wall time. All normalized outputs match.",
  "conditions": "macOS ARM64/Python 3.12, runtime 90a8a73 and pinned native binary. Controlled: 17169 plies/417 selections. Teacher: four development families, 1402 plies/169 selections, 1402 10k-node actor calls and 338 10k/100k supervision calls. Three alternating fresh-process pairs; separate profiles, synchronization and adapter diagnostics. Native core uses five fixed-action replays per cell and independent Python verification.",
  "limitations": "One machine, short controlled windows and a bounded teacher workload. Timing repeats are not independent workload samples. Teacher child cost varies despite identical outputs/node counts. Instrumentation changes timing. In-place native and SQLite OFF diagnostics weaken guarantees and are not adopted. Child resource accounting includes small provenance subprocesses; child maximum RSS is not combined peak memory. Initial launcher incomplete and initial core driver superseded; frozen evidence retained.",
  "decision": "Keep Python default and all production semantics. For realistic throughput, next test two independent isolated teacher-generation workers versus serial work. For native execution, target full-state copy cost with atomic preallocation/commit and conformance/failure tests. Storage changes retain per-move WAL/FULL or need a separate recovery-contract decision.",
  "revisit": "Measure the bounded two-worker comparison or a safe atomic native-step prototype under matched outputs before implementing a scheduler or promoting native. Reprofile different actor/teacher budgets; do not extrapolate core-only speedups to the pipeline.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-generation-bottlenecks.md",
      "role": "report",
      "sha256": "3ca2064fb4e0fc04850aba35de6202cdf0fef2eb0d30dd17bf1d615a32811263"
    },
    {
      "path": "data/evaluation/generation-profile-20260921.json",
      "role": "results",
      "sha256": "4cd62dc15b09230e9b2727ab53f4f12c056b46b7f61494d1aeb186e7952903b8"
    },
    {
      "path": "artifacts/generation-profile-20260921/verification.json",
      "role": "run",
      "sha256": "26c672a5845d98b70dc8632191165491d5cee6db52d1773609eebef92d80046a"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-02/summary.json",
      "role": "results",
      "sha256": "9c3232e68996ce3be5f8e7348b073ca44ce6adddf89f3a998bfa30e66f3a7fda"
    },
    {
      "path": "artifacts/generation-profile-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "33c5beeeeb34db8d57da40566410f93a279009230d2140e47c86519162f501ab"
    },
    {
      "path": "artifacts/generation-profile-20260921/profile-controlled-01/summary.json",
      "role": "results",
      "sha256": "be67023b273b4294ce9682ad962c5e949682b5c732aab2258767656893d7d1b1"
    },
    {
      "path": "artifacts/generation-profile-20260921/profile-teacher-01/summary.json",
      "role": "results",
      "sha256": "10c6d064f297971dc5c9caad8f04b8a3155c96a50219c75d824d435e5a598cb0"
    },
    {
      "path": "artifacts/generation-profile-20260921/sync-sensitivity-01/summary.json",
      "role": "results",
      "sha256": "ce3e45b265c4c38b132f7120f3e2492677f4c2d57b9dfb1cb4af5dcb30337a30"
    },
    {
      "path": "artifacts/generation-profile-20260921/adapter-01/summary.json",
      "role": "results",
      "sha256": "642f33c332bbfce5d4b4117e2f4bae2ac5e3e2393f6a94e608b51798c1c32d5a"
    },
    {
      "path": "artifacts/generation-profile-20260921/actions-01/summary.json",
      "role": "results",
      "sha256": "b75ffb1794977c5ef8606b4fc8e48c388051c132c61e721e169160d90cdb250b"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-02/summary.json",
      "role": "results",
      "sha256": "6eac80d70fe18ee62e7506ab8e6c7ee94079018a15b063351059cb45b51dadcd"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-02/frozen/scripts/profile_generation.py",
      "role": "source",
      "sha256": "1b22cd1f69721188c470fcf941782e12dcb2bf5b22c3a106371763825f738665"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-02/frozen/scripts/profile_native_core.cpp",
      "role": "source",
      "sha256": "27e3c3c41693776d433537a2614a8892b00766ccada2143f69f4c2cccd07a6ea"
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/controlled.json",
      "role": "config",
      "sha256": "fb53e4dc3242178f6cdb3bcb41e3acc5d7d3fa19b68759081b9c73f04bcd17af"
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/teacher.json",
      "role": "config",
      "sha256": "d3f0fc6394b9d1ae6237337431a93154809e6b223c214a982ab87dc04ad2d6d6"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-01/failure.json",
      "role": "run",
      "sha256": "682a89c4daa7fdfb5b98aed64f32eafd52e8e7dd4a6f2dfa5c4c1cfd00b4ae48"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-01/superseded.json",
      "role": "run",
      "sha256": "e969e6c09875c81a6b2ae59d9fe022d62ec8b4be240ef6457bcac8257bd3f4f0"
    }
  ],
  "prior_work": [
    {
      "id": "incremental-append-20260921",
      "relationship": "extends",
      "contribution": "Diagnoses remaining costs without changing production behavior."
    },
    {
      "id": "native-backends-20260921",
      "relationship": "challenges",
      "contribution": "Explains the difference between coarse native loop speed and maintained per-move integration."
    }
  ],
  "novelty": "Separates full pipeline costs, shared adapter overhead, native binding/core costs and teacher child resources after incremental append."
}
```


```experiment
{
  "schema_version": 1,
  "id": "generation-profile-20260921",
  "title": "Generation bottleneck diagnosis",
  "question": "Why does native game execution barely accelerate full policy generation?",
  "kind": "performance",
  "topics": [
    "native",
    "throughput",
    "profile",
    "generation",
    "SQLite",
    "teacher",
    "state copy"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Three paired rounds give 1.097x native throughput on 64 controlled games and 1.039x on 16 teacher games. Identical-action full observations give 1.475x. Copying/releasing full native state accounts for 56.1% of a core profile; in-place diagnostic execution is 2.394x faster. Controlled SQLite synchronization is costly; real-teacher response reads occupy about 90% of profiled wall time. All normalized outputs match.",
  "conditions": "macOS ARM64/Python 3.12, runtime 90a8a73 and pinned native binary. Controlled: 17169 plies/417 selections. Teacher: four development families, 1402 plies/169 selections, 1402 10k-node actor calls and 338 10k/100k supervision calls. Three alternating fresh-process pairs; separate profiles, synchronization and adapter diagnostics. Native core uses five fixed-action replays per cell and independent Python verification.",
  "limitations": "One machine, short controlled windows and a bounded teacher workload. Timing repeats are not independent workload samples. Teacher child cost varies despite identical outputs/node counts. Instrumentation changes timing. In-place native and SQLite OFF diagnostics weaken guarantees and are not adopted. Child resource accounting includes small provenance subprocesses; child maximum RSS is not combined peak memory. Initial launcher incomplete and initial core driver superseded; frozen evidence retained.",
  "decision": "Keep Python default and all production semantics. For realistic throughput, next test two independent isolated teacher-generation workers versus serial work. For native execution, target full-state copy cost with atomic preallocation/commit and conformance/failure tests. Storage changes retain per-move WAL/FULL or need a separate recovery-contract decision.",
  "revisit": "Measure the bounded two-worker comparison or a safe atomic native-step prototype under matched outputs before implementing a scheduler or promoting native. Reprofile different actor/teacher budgets; do not extrapolate core-only speedups to the pipeline.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-generation-bottlenecks.md",
      "role": "report",
      "sha256": "274c9023ba097c5e445846d0f22818b1d9df5bec5c2bfc07d90550ca33cb8731"
    },
    {
      "path": "data/evaluation/generation-profile-20260921.json",
      "role": "results",
      "sha256": "4cd62dc15b09230e9b2727ab53f4f12c056b46b7f61494d1aeb186e7952903b8"
    },
    {
      "path": "artifacts/generation-profile-20260921/verification.json",
      "role": "run",
      "sha256": "26c672a5845d98b70dc8632191165491d5cee6db52d1773609eebef92d80046a"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-02/summary.json",
      "role": "results",
      "sha256": "9c3232e68996ce3be5f8e7348b073ca44ce6adddf89f3a998bfa30e66f3a7fda"
    },
    {
      "path": "artifacts/generation-profile-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "33c5beeeeb34db8d57da40566410f93a279009230d2140e47c86519162f501ab"
    },
    {
      "path": "artifacts/generation-profile-20260921/profile-controlled-01/summary.json",
      "role": "results",
      "sha256": "be67023b273b4294ce9682ad962c5e949682b5c732aab2258767656893d7d1b1"
    },
    {
      "path": "artifacts/generation-profile-20260921/profile-teacher-01/summary.json",
      "role": "results",
      "sha256": "10c6d064f297971dc5c9caad8f04b8a3155c96a50219c75d824d435e5a598cb0"
    },
    {
      "path": "artifacts/generation-profile-20260921/sync-sensitivity-01/summary.json",
      "role": "results",
      "sha256": "ce3e45b265c4c38b132f7120f3e2492677f4c2d57b9dfb1cb4af5dcb30337a30"
    },
    {
      "path": "artifacts/generation-profile-20260921/adapter-01/summary.json",
      "role": "results",
      "sha256": "642f33c332bbfce5d4b4117e2f4bae2ac5e3e2393f6a94e608b51798c1c32d5a"
    },
    {
      "path": "artifacts/generation-profile-20260921/actions-01/summary.json",
      "role": "results",
      "sha256": "b75ffb1794977c5ef8606b4fc8e48c388051c132c61e721e169160d90cdb250b"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-02/summary.json",
      "role": "results",
      "sha256": "6eac80d70fe18ee62e7506ab8e6c7ee94079018a15b063351059cb45b51dadcd"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-02/frozen/scripts/profile_generation.py",
      "role": "source",
      "sha256": "1b22cd1f69721188c470fcf941782e12dcb2bf5b22c3a106371763825f738665"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-02/frozen/scripts/profile_native_core.cpp",
      "role": "source",
      "sha256": "27e3c3c41693776d433537a2614a8892b00766ccada2143f69f4c2cccd07a6ea"
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/controlled.json",
      "role": "config",
      "sha256": "fb53e4dc3242178f6cdb3bcb41e3acc5d7d3fa19b68759081b9c73f04bcd17af"
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/teacher.json",
      "role": "config",
      "sha256": "d3f0fc6394b9d1ae6237337431a93154809e6b223c214a982ab87dc04ad2d6d6"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-01/failure.json",
      "role": "run",
      "sha256": "682a89c4daa7fdfb5b98aed64f32eafd52e8e7dd4a6f2dfa5c4c1cfd00b4ae48"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-01/superseded.json",
      "role": "run",
      "sha256": "e969e6c09875c81a6b2ae59d9fe022d62ec8b4be240ef6457bcac8257bd3f4f0"
    },
    {
      "path": "artifacts/generation-profile-20260921/final-checks.json",
      "role": "run",
      "sha256": "409d138845bb706dc533bb37ae3a4f52e70883584d25e2957257eed45a4720f0"
    }
  ],
  "prior_work": [
    {
      "id": "incremental-append-20260921",
      "relationship": "extends",
      "contribution": "Diagnoses remaining costs without changing production behavior."
    },
    {
      "id": "native-backends-20260921",
      "relationship": "challenges",
      "contribution": "Explains the difference between coarse native loop speed and maintained per-move integration."
    }
  ],
  "novelty": "Separates full pipeline costs, shared adapter overhead, native binding/core costs and teacher child resources after incremental append."
}
```


```experiment
{
  "schema_version": 1,
  "id": "generation-profile-20260921",
  "title": "Generation bottleneck diagnosis",
  "question": "Why does native game execution barely accelerate full policy generation?",
  "kind": "performance",
  "topics": [
    "native",
    "throughput",
    "profile",
    "generation",
    "SQLite",
    "teacher",
    "state copy"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Three paired rounds give 1.097x native throughput on 64 controlled games and 1.039x on 16 teacher games. Identical-action full observations give 1.475x. Copying/releasing full native state accounts for 56.1% of a core profile; in-place diagnostic execution is 2.394x faster. Controlled SQLite synchronization is costly; real-teacher response reads occupy about 90% of profiled wall time. All normalized outputs match.",
  "conditions": "macOS ARM64/Python 3.12, runtime 90a8a73 and pinned native binary. Controlled: 17169 plies/417 selections. Teacher: four development families, 1402 plies/169 selections, 1402 10k-node actor calls and 338 10k/100k supervision calls. Three alternating fresh-process pairs; separate profiles, synchronization and adapter diagnostics. Native core uses five fixed-action replays per cell and independent Python verification.",
  "limitations": "One machine, short controlled windows and a bounded teacher workload. Timing repeats are not independent workload samples. Teacher child cost varies despite identical outputs/node counts. Instrumentation changes timing. In-place native and SQLite OFF diagnostics weaken guarantees and are not adopted. Child resource accounting includes small provenance subprocesses; child maximum RSS is not combined peak memory. Initial launcher incomplete and initial core driver superseded; frozen evidence retained.",
  "decision": "Keep Python default and all production semantics. For realistic throughput, next test two independent isolated teacher-generation workers versus serial work. For native execution, target full-state copy cost with atomic preallocation/commit and conformance/failure tests. Storage changes retain per-move WAL/FULL or need a separate recovery-contract decision.",
  "revisit": "Measure the bounded two-worker comparison or a safe atomic native-step prototype under matched outputs before implementing a scheduler or promoting native. Reprofile different actor/teacher budgets; do not extrapolate core-only speedups to the pipeline.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-generation-bottlenecks.md",
      "role": "report",
      "sha256": "9b24ae8c716cf53897a36f96986586a05c317a4dea6702f9d4bcadcc8b509a3d"
    },
    {
      "path": "data/evaluation/generation-profile-20260921.json",
      "role": "results",
      "sha256": "4cd62dc15b09230e9b2727ab53f4f12c056b46b7f61494d1aeb186e7952903b8"
    },
    {
      "path": "artifacts/generation-profile-20260921/verification.json",
      "role": "run",
      "sha256": "26c672a5845d98b70dc8632191165491d5cee6db52d1773609eebef92d80046a"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-02/summary.json",
      "role": "results",
      "sha256": "9c3232e68996ce3be5f8e7348b073ca44ce6adddf89f3a998bfa30e66f3a7fda"
    },
    {
      "path": "artifacts/generation-profile-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "33c5beeeeb34db8d57da40566410f93a279009230d2140e47c86519162f501ab"
    },
    {
      "path": "artifacts/generation-profile-20260921/profile-controlled-01/summary.json",
      "role": "results",
      "sha256": "be67023b273b4294ce9682ad962c5e949682b5c732aab2258767656893d7d1b1"
    },
    {
      "path": "artifacts/generation-profile-20260921/profile-teacher-01/summary.json",
      "role": "results",
      "sha256": "10c6d064f297971dc5c9caad8f04b8a3155c96a50219c75d824d435e5a598cb0"
    },
    {
      "path": "artifacts/generation-profile-20260921/sync-sensitivity-01/summary.json",
      "role": "results",
      "sha256": "ce3e45b265c4c38b132f7120f3e2492677f4c2d57b9dfb1cb4af5dcb30337a30"
    },
    {
      "path": "artifacts/generation-profile-20260921/adapter-01/summary.json",
      "role": "results",
      "sha256": "642f33c332bbfce5d4b4117e2f4bae2ac5e3e2393f6a94e608b51798c1c32d5a"
    },
    {
      "path": "artifacts/generation-profile-20260921/actions-01/summary.json",
      "role": "results",
      "sha256": "b75ffb1794977c5ef8606b4fc8e48c388051c132c61e721e169160d90cdb250b"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-02/summary.json",
      "role": "results",
      "sha256": "6eac80d70fe18ee62e7506ab8e6c7ee94079018a15b063351059cb45b51dadcd"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-02/frozen/scripts/profile_generation.py",
      "role": "source",
      "sha256": "1b22cd1f69721188c470fcf941782e12dcb2bf5b22c3a106371763825f738665"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-02/frozen/scripts/profile_native_core.cpp",
      "role": "source",
      "sha256": "27e3c3c41693776d433537a2614a8892b00766ccada2143f69f4c2cccd07a6ea"
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/controlled.json",
      "role": "config",
      "sha256": "fb53e4dc3242178f6cdb3bcb41e3acc5d7d3fa19b68759081b9c73f04bcd17af"
    },
    {
      "path": "artifacts/generation-profile-20260921/inputs/teacher.json",
      "role": "config",
      "sha256": "d3f0fc6394b9d1ae6237337431a93154809e6b223c214a982ab87dc04ad2d6d6"
    },
    {
      "path": "artifacts/generation-profile-20260921/controlled-01/failure.json",
      "role": "run",
      "sha256": "682a89c4daa7fdfb5b98aed64f32eafd52e8e7dd4a6f2dfa5c4c1cfd00b4ae48"
    },
    {
      "path": "artifacts/generation-profile-20260921/core-01/superseded.json",
      "role": "run",
      "sha256": "e969e6c09875c81a6b2ae59d9fe022d62ec8b4be240ef6457bcac8257bd3f4f0"
    },
    {
      "path": "artifacts/generation-profile-20260921/final-checks.json",
      "role": "run",
      "sha256": "409d138845bb706dc533bb37ae3a4f52e70883584d25e2957257eed45a4720f0"
    },
    {
      "path": "artifacts/generation-profile-20260921/cleanup-checks/verification.json",
      "role": "run",
      "sha256": "08a99baaa2799a66c4fc26eb6c87e68ee9376b9f27a23d5f25fcac781b88de57"
    }
  ],
  "prior_work": [
    {
      "id": "incremental-append-20260921",
      "relationship": "extends",
      "contribution": "Diagnoses remaining costs without changing production behavior."
    },
    {
      "id": "native-backends-20260921",
      "relationship": "challenges",
      "contribution": "Explains the difference between coarse native loop speed and maintained per-move integration."
    }
  ],
  "novelty": "Separates full pipeline costs, shared adapter overhead, native binding/core costs and teacher child resources after incremental append."
}
```
