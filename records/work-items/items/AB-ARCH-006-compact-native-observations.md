---
description: Remove repeated wire-contract construction from native trajectory execution and measure full generation.
scope: native execution boundary
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-006
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, native, performance
depends_on: AB-ARCH-005
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-006 — Compact native observations

## Intent

Complete the authorized next slice from [AB-ARCH-005](AB-ARCH-005-shared-replay-execution.md):
return immutable observations directly from trajectories, avoiding per-move full
history export and `Position`/`Snapshot` reconstruction, with a dedicated scalar
native step. Existing decisions settle C++ ownership, explicit selection, direct
internal API migration, exact semantics and unchanged per-move durability. No
material owner choice remains; performance is the experiment's open question.

## Acceptance Criteria

- Trajectories return immutable views; public referee/HTTP results remain detached
  wire contracts. All maintained consumers migrate directly without a legacy shim.
- Native history/hash metadata follows successful transitions only; rejected
  scalar/batch actions preserve state, error precedence and exact replay hashes.
- Scalar stepping avoids the batch container path; batches retain all-or-nothing
  staging and caller order. Native allocation failures before commit remain atomic.
- No change to actor RNG, rules, selected examples, teacher evidence or storage
  transactions. Native remains explicitly selected.
- Exact differential, generation/recovery and API parity; isolated packages,
  native sanitizer and full application gates pass.
- Retain frozen controls, inputs, binary/source identity and all trial outcomes.

## Context and Trade-offs

AB-ARCH-005 removed duplicate Python rules, improving native throughput by 1.164x
over its previous integration but reaching only 0.984x default Python. Its profile
attributed 0.466 s to native contract inspection versus 0.144 s to native stepping.
These overlapping profiled costs motivate this bounded change; they do not prove
the gain. Collection serialization and commit frequency are outside this slice.

### Predeclared comparison

- Archive the entire `c4a8d91` runtime and its original extension before editing.
  Freeze current source, binary and lock before each confirmation attempt.
- Reuse the same 64 random-actor games, seed 29, 300-ply cap, phase quotas and
  deterministic legal fixture labels. Three alternating four-arm rounds compare
  old Python, old shared-native, current Python and compact native. Full historical
  runtime imports are asserted; old arms cannot inherit new consumer code.
- Reuse four plausible-actor games, 32 plies, pinned Pikafish/NNUE, one thread and
  1,000 nodes for two alternating current Python/native pilot rounds.
- Fresh process/collection per cell, serial execution, cleared reference caches;
  at most 180 seconds per cell and 20 minutes per comparison. Development parity
  precedes confirmation. No concurrent tests or builds during measured work.
- Require identical semantic projections of trajectories, decisions, outcomes,
  occurrences and supervision. Independent Python and SQLite verification follow
  timing. Runtime/provenance fields alone are excluded; raw data remains intact.
- Record wall/CPU, peak worker RSS, plies/s, selections/s and phase timers. A
  separate profile diagnoses remaining costs; it does not replace unprofiled data.
- At least 1.2x median paired throughput over current Python and a win in every
  controlled round permits further adoption work. Flag default runtime regression
  above 5%. Neither threshold changes backend defaults automatically. Preserve
  negative or inconclusive results and failed attempts.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User authorized implementation after a decision check; existing decisions settle scope. |
| 2026-09-21 | GPT-6 | wip | done | Compact observations, scalar native stepping, exact comparisons, isolated packages, sanitizer and full gates complete; native remains opt-in. |

## Implementation Ledger

- **2026-09-21 — decision:** Separate immutable trajectory observations from
  mutable interchange contracts; retain the referee's API conversion and all
  error/durability guarantees. Historical runtime and binary archived under
  `artifacts/compact-native-20260921/baseline-c4a8d91`. **Review:** not-required.
- **2026-09-21 — finding:** All 12 primary cells match 64 trajectories, 17,169
  plies and 417 labels. Native gains 1.102x paired throughput over Python and
  1.085x over previous native, winning all controlled rounds but missing the
  1.2x adoption threshold. Four teacher cells match 128 plies/20 selections with
  a 1.027x ratio. Keep native explicit; no strength conclusion. See the
  [report](../../reports/2026-09-21-compact-native-observations.md) and
  [compact cells](../../../data/evaluation/compact-native-20260921.json).
  **Review:** not-required.
- **2026-09-21 — verification:** `make check` passes 792 Python tests (one skip),
  five browser tests and all static/build gates. Isolated game/native packages
  pass 70/ten tests. ASan/UBSan exercises scalar staging and 128 games. Both
  304-file comparison manifests match frozen and post-gate runtime bytes;
  independent post-timing replay, labels and SQLite checks pass.
  **Review:** not-required.
- **2026-09-21 — deviation:** Initial native package isolation exposed an old
  smoke assertion expecting a wire contract. Migrate it to immutable moves and
  rerun successfully; preserve both logs. No timed attempt failed. The native
  profile has inconsistent scalar-call counts, so use paired unprofiled timing
  and phase counters for the conclusion, without per-step profile claims.
  **Review:** not-required.
- **2026-09-21 — handoff:** Referee-phase time falls from 0.488 s to 0.333 s
  by median; append remains 1.395 s. A subsequent experiment may target repeated
  payload decoding/serialization while retaining every-move durability. This
  hypothesis is not implemented here; broader migration remains routed through
  [AB-ARCH-001](AB-ARCH-001-modular-runtime.md). **Review:** not-required.


```experiment
{
  "schema_version": 1,
  "id": "compact-native-20260921",
  "title": "Compact native trajectory observations",
  "question": "Does removing per-move wire-contract construction make native generation faster end to end?",
  "kind": "performance",
  "topics": [
    "native",
    "generation",
    "binding",
    "trajectory",
    "serialization"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "AB-ARCH-006: three alternating four-arm rounds of the fixed 64-game workload using complete c4a8d91 controls, then two paired pinned real-teacher pilot rounds.",
  "limitations": "",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "shared-replay-20260921",
      "relationship": "extends",
      "contribution": "Tests compact immutable results and scalar native stepping after eliminating duplicate Python rules."
    }
  ],
  "novelty": "Measures conversion and scalar-call savings with unchanged actors, storage durability and independently verified outputs."
}
```


```experiment
{
  "schema_version": 1,
  "id": "compact-native-20260921",
  "title": "Compact native trajectory observations",
  "question": "Does removing per-move wire-contract construction make native generation faster end to end?",
  "kind": "performance",
  "topics": [
    "native",
    "generation",
    "binding",
    "trajectory",
    "serialization"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "Compact native observations achieve 1.102x paired throughput over direct Python and 1.085x over previous shared-native execution, winning all three controlled rounds. All 12 cells match 64 trajectories/17169 plies/417 fixture labels. Four real-teacher cells match 128 plies/20 selections with a 1.027x paired ratio. Native misses the 1.2x adoption threshold.",
  "conditions": "macOS ARM64/Python 3.12; three alternating four-arm rounds with entire archived c4a8d91 runtime and original binary controls, fixed random actor and fixture labels. Separate two-round four-game/32-ply plausible-actor pilot uses pinned Pikafish/NNUE, one thread and 1000 nodes. Fresh serial workers and collections; 304-file source/binary manifests; independent post-timing Python and SQLite verification.",
  "limitations": "Three short local controlled rounds and two small teacher rounds. Repeated fixed trajectories are not independent workload samples. Fixture labels do not establish teaching quality or strength. Worker CPU/RSS omit the teacher child and peak RSS includes verification. Native profile scalar-call counts are inconsistent, so no per-step profile claim. Linux configured but not locally executed.",
  "decision": "Retain compact observations and dedicated scalar execution with exact conformance. Keep native explicit/experimental because the 1.2x end-to-end adoption threshold is not met. Default paired runtime ratio 1.011x stays below the 5% regression flag. Preserve failed initial package smoke check and successful migrated rerun.",
  "revisit": "Measure a separately bounded reduction in repeated collection payload decoding/serialization while preserving per-move durability, then repeat the fixed full-pipeline comparison; append remains the larger measured phase.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-compact-native-observations.md",
      "role": "report",
      "sha256": "d0242376a1e430914ab447a10321f2c68a4293df6fbdc5039d22299b7f15e606"
    },
    {
      "path": "data/evaluation/compact-native-20260921.json",
      "role": "results",
      "sha256": "5eedcbebe485ebad8556dcf0c16215a3459b18df23a8d53b4ba819d66dac4920"
    },
    {
      "path": "artifacts/compact-native-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "fd88b2cfeabf44813cb470a71cee571d55f6af7fc95cf2bd8a53f0f8f56ea59b"
    },
    {
      "path": "artifacts/compact-native-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "98745057c7897a4ca31870778aaab18b6d81492f882ab9e875697b0f760ad90d"
    },
    {
      "path": "artifacts/compact-native-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "15c6d057c20f50c95720ab230415b928b5749c8932e1af085973aa27b8abb0cf"
    },
    {
      "path": "artifacts/compact-native-20260921/teacher-01/manifest.json",
      "role": "source",
      "sha256": "4616aece55765b5c18e96146acd43c0fe3d10a9a5c34c1e6991e760cbe65d5c2"
    },
    {
      "path": "artifacts/compact-native-20260921/confirmation-01/frozen/scripts/benchmark_compact_native.py",
      "role": "source",
      "sha256": "3e0baed697f2eac324c61dd71bab36b18adc5f61713fb4bf994f1bcf0cff29b6"
    },
    {
      "path": "artifacts/compact-native-20260921/source-verification.json",
      "role": "run",
      "sha256": "98e6e2465fea3172fdead7ada085298ad939b9f1d11245579b3a18aefc700bd6"
    },
    {
      "path": "artifacts/compact-native-20260921/profile-01/diagnostic.txt",
      "role": "run",
      "sha256": "2917ec597d0cd2dbfaff1362ef2d32352aa80ba37b5b731d1b05ed1c96b1c90a"
    },
    {
      "path": "artifacts/compact-native-20260921/reference-package-check.log",
      "role": "run",
      "sha256": "cb812f6e5dcf90d9e329abfdbc3bd6913c0a7ee135b26415aa7fe5c5860fc353"
    },
    {
      "path": "artifacts/compact-native-20260921/native-package-check.log",
      "role": "run",
      "sha256": "a7029c5163ab9672a14392686d0ee121738ac22ab1f1a6c564555bb137771fec"
    },
    {
      "path": "artifacts/compact-native-20260921/native-package-check-02.log",
      "role": "run",
      "sha256": "450666b17feda43d8d958bc80e137a39a68bafa31c66aab0a24ea3b624208e09"
    },
    {
      "path": "artifacts/compact-native-20260921/make-check.log",
      "role": "run",
      "sha256": "4f4967287dd9b6b331724b39161bfb26ea95e889a1113470b5d6a8fc4b19eebb"
    },
    {
      "path": "artifacts/compact-native-20260921/sanitizer-receipt.json",
      "role": "run",
      "sha256": "80b7ae45930695e921f65ac7c5c789329d5854c64c4b7e909b270c0872b7ab2b"
    },
    {
      "path": "artifacts/compact-native-20260921/native-conformance.log",
      "role": "run",
      "sha256": "6da2ae934a3ed246d107cade7c9222e32aae23e8b94ae636fdfac68953372cdd"
    },
    {
      "path": "artifacts/compact-native-20260921/development-01/summary.json",
      "role": "results",
      "sha256": "12402e8971cd8bc877ad37a9dccb08b9adb0207a6632dcf7cb9cc7e5cf37b526"
    }
  ],
  "prior_work": [
    {
      "id": "shared-replay-20260921",
      "relationship": "extends",
      "contribution": "Tests compact immutable results and scalar native stepping after eliminating duplicate Python rules."
    }
  ],
  "novelty": "Measures conversion and scalar-call savings with unchanged actors, storage durability and independently verified outputs."
}
```
