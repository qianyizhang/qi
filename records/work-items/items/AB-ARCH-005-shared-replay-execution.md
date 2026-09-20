---
description: Share selected referee results through collection, sampling and teacher validation without duplicate Python rules.
scope: generation execution boundary
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-005
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, native, performance
depends_on: AB-ARCH-004
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-005 — Shared replay execution

## Intent

Complete the authorized next slice from
[AB-ARCH-004](AB-ARCH-004-native-generation.md): a selected backend's immutable
results serve generation, collection validation, sampling and teacher checks.
Prior architecture already gives the referee rules authority; no new policy
decision is needed. Preserve per-move durability, source/split guards, exact
replay identities and independently executable Python verification.

## Acceptance Criteria

- One run-owned, bounded replay session supplies validated immutable views;
  consumers cannot insert arbitrary views into its cache. Uncached histories
  are fully validated by the selected backend. Invalid moves remain atomic.
- Collection legality reuse never substitutes for persisted-prefix, lifecycle,
  split or SQL checks. Failed transactions, recovery and retries remain correct.
- Sampler, teacher and evidence validation consume the selected backend without
  reentering Python rules for generated native positions. No global selector.
- Identical actors, RNG streams, outcomes, selected rows and semantic supervision
  across default Python, previous native integration and shared native execution.
- Keep native opt-in; preserve historical evidence and compare fresh processes.
- Relevant unit/integration, package isolation and full application gates pass.

## Context and Trade-offs

`native-generation-20260921` measured native at 0.835x default throughput. Its
profile found collection append/validation at about 58% of profiled function
time, with Python rules still executed after native transitions. This study
extends that result by removing the duplicated rules, not by weakening writes
or moving domain policies into C++.

The replay session owns one current backend cursor and at most 301 immutable
views (one maximum-length game). Cache keys include complete move history under
the supported ruleset/start. A cached result proves legality only; SQLite remains
the authority for persisted progress. Scope is synchronous generation, not a
shared server cache or concurrent writer design.

### Predeclared comparison

- Freeze executed sources and current native binary before confirmation.
- Reuse AB-ARCH-004 controlled inputs: 64 random-actor games, seed 29, at most
  300 plies, unchanged phase quotas and deterministic legal supervision fixture.
  Labels are controls, not a teaching-quality result.
- Three alternating rounds: original direct Python runner at `92943ff`, its
  original native integration, current direct default and shared native execution.
  Historical runner/store/consumer sources must be retained and executed together
  so the old-native arm does not accidentally inherit the new validation path.
- Separate real-teacher diagnostic: four plausible-actor games, 32 plies,
  one thread/1,000 nodes using the same pinned Pikafish assets; two alternating
  current default/native rounds. No strength claim.
- Fresh worker/collection per cell, clear reference caches at worker start,
  serial timing, at most 180 seconds per cell and 20 minutes measured total.
- Require exact trajectory, actor decision, outcome, occurrence and supervision
  projections; remove only runtime and execution-provenance fields. Verify
  final data independently with Python after timing; retain failed attempts.
- Record wall/worker CPU, process peak RSS, plies/s, selections/s and phase costs.
  A separate profile and rule-call guard establish whether duplication is removed.
- Advance further adoption work only with at least 1.2x median paired native
  throughput and every controlled round faster than the current default. Keep
  explicit selection even if this threshold passes. Flag default runtime
  regression above 5% against its original runner. These are engineering gates.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User authorized the next execution-boundary slice; existing decisions settle its scope. |
| 2026-09-21 | GPT-6 | wip | done | Shared validation implemented; fixed comparison, independent parity, isolation and full gates pass. Native remains opt-in after missing the adoption threshold. |

## Implementation Ledger

- **2026-09-21 — decision:** Add immutable views and a bounded replay session;
  inject it explicitly through collection, sampler, teacher and evidence checks.
  Preserve the direct Python default and all SQL durability/structural guards.
  **Review:** not-required.
- **2026-09-21 — finding:** All 12 controlled cells match 64 trajectories,
  17,169 plies and 417 fixture labels; four real-teacher cells match 128 plies
  and 20 selections. Native Python rule misses fall from 17,131 to one initial
  preflight check. Median paired throughput improves 1.164x over previous native
  but is 0.984x current Python, failing the 1.2x adoption rule. Keep native
  explicit. The real-teacher result is 1.009x with opposite round winners.
  See the [report](../../reports/2026-09-21-shared-replay-execution.md) and
  [compact cells](../../../data/evaluation/shared-replay-20260921.json).
  **Review:** not-required.
- **2026-09-21 — deviation:** Two development verifier mistakes are retained
  under `artifacts/shared-replay-20260921/development-01` and `development-02`;
  corrected four-arm parity passed before confirmation. Historical controls
  use the entire archived runtime, and both 302-file frozen manifests verify.
  AB-ARCH-004 receives an append-only evidence locator revision to its identical
  frozen runner, preserving its earlier observations. **Review:** not-required.
- **2026-09-21 — verification:** `make check` passes 792 Python tests (one
  skipped), five browser tests, lint/docs/catalog/OpenAPI/types and browser build.
  Isolated game/native sdist and wheel checks pass 70/eight tests. Transaction
  failures, retries, recovery, invalid prefixes and forged views remain guarded.
  **Review:** not-required.
- **2026-09-21 — handoff:** The profile now points to durable collection writes,
  payload serialization and contract construction. Any later performance trial
  should reduce those costs while preserving per-move recovery, then repeat the
  fixed full-pipeline comparison. This is a hypothesis, not an adoption result;
  broader migration remains under [AB-ARCH-001](AB-ARCH-001-modular-runtime.md).
  **Review:** not-required.


```experiment
{
  "schema_version": 1,
  "id": "shared-replay-20260921",
  "title": "Shared referee validation across generation consumers",
  "question": "Does removing duplicate Python rule execution improve full native generation without weakening data integrity?",
  "kind": "performance",
  "topics": [
    "native",
    "generation",
    "replay",
    "validation",
    "sampling"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "AB-ARCH-005: three alternating four-arm rounds on 64 fixed random-actor games, plus two paired real-teacher pilot rounds. Frozen entire 92943ff runtime supplies historical controls.",
  "limitations": "",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "native-generation-20260921",
      "relationship": "extends",
      "contribution": "Eliminates repeated Python rule validation through a bounded run-owned referee session shared across data consumers."
    }
  ],
  "novelty": "Measures full-pipeline backend substitution with unchanged per-move durability and independent post-run verification."
}
```


```experiment
{
  "schema_version": 1,
  "id": "shared-replay-20260921",
  "title": "Shared referee validation across generation consumers",
  "question": "Does removing duplicate Python rule execution improve full native generation without weakening data integrity?",
  "kind": "performance",
  "topics": [
    "native",
    "generation",
    "replay",
    "validation",
    "sampling"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "Shared replay validation removes repeated Python rules: native records one initial preflight legal-move cache miss instead of 17131. All 12 primary cells match 64 trajectories/17169 plies/417 fixture labels. Native gains 1.164x over the prior integration but reaches only 0.984x current Python throughput, losing two of three rounds. Four real-teacher cells match 128 plies/20 selections at 1.009x paired throughput with opposite round winners.",
  "conditions": "macOS ARM64/Python 3.12; three alternating four-arm rounds with complete archived 92943ff runtime controls, fixed random actor and fixture labels. Two paired four-game/32-ply plausible-actor rounds with pinned Pikafish, one thread and 1000 nodes. Fresh serial workers/collections; identical native binary; independent post-timing replay and SQLite verification; 302-file frozen source manifests for each comparison.",
  "limitations": "Finite local conformance and short desktop timing windows. Repeated fixed trajectories are not independent workload samples. Native generation remains serial. CPU/RSS omit teacher child costs; peak RSS includes verification. Fixture labels do not establish teaching quality. Linux configured but not locally executed. Two failed development verifier attempts are retained and excluded from confirmation.",
  "decision": "Keep the completed shared execution boundary and native explicit/experimental. Do not promote native: it misses the predeclared 1.2x gain and every-round win requirement. Default runtime ratio 1.020x stays below the 5% regression flag.",
  "revisit": "A future bounded trial may reduce contract construction and collection payload serialization while preserving per-move durability, then repeat identical pipeline parity and throughput. The profile identifies those costs; it does not establish the gain from a proposed replacement.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-shared-replay-execution.md",
      "role": "report",
      "sha256": "2455c2eb0fa6ac66f708f1fbc9075722b5e9fa0f84c17468e2797a7abba756db"
    },
    {
      "path": "data/evaluation/shared-replay-20260921.json",
      "role": "results",
      "sha256": "53a810cc7ae365a167fc725436ed09ff7a0b5a39d288a0202b223be541556f4b"
    },
    {
      "path": "artifacts/shared-replay-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "ca9d12965d3bf854e69eb190aaca9fd4d098c2e0ea59bf1824f04c472c610c9f"
    },
    {
      "path": "artifacts/shared-replay-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "b30801d84310fc7200a4a3c35a46485b71d235e1a98901d514b0ceaba8af9dcb"
    },
    {
      "path": "artifacts/shared-replay-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "0f25547543f4d167f0f4adce0c3cc8e1406f3141e45be5b608c854f1d0caccd9"
    },
    {
      "path": "artifacts/shared-replay-20260921/teacher-01/manifest.json",
      "role": "source",
      "sha256": "8c20003ebee445c644446b459ba2f94f73bb2627c330f3883fd0e4c101c2a85a"
    },
    {
      "path": "artifacts/shared-replay-20260921/confirmation-01/frozen/scripts/benchmark_shared_execution.py",
      "role": "source",
      "sha256": "399247d26d31026a23bc20ec2db47b08d3939f1a9dfe9a04b733f98473439e2e"
    },
    {
      "path": "artifacts/shared-replay-20260921/source-verification.json",
      "role": "run",
      "sha256": "89536596e46b91e374c4a36484496940e2a7d20779215a623e521c211eb5e0a9"
    },
    {
      "path": "artifacts/shared-replay-20260921/profile-01/diagnostic.txt",
      "role": "run",
      "sha256": "71f85d0e37d007922938901adf03bf07961d3317542b79cc9bca1c66f7af3491"
    },
    {
      "path": "artifacts/shared-replay-20260921/reference-package-check.log",
      "role": "run",
      "sha256": "943e470a62cde3bc63dbf0e6c55e26e3cb2ae8e20b7bf4e94e0b73bcae8125e3"
    },
    {
      "path": "artifacts/shared-replay-20260921/native-package-check.log",
      "role": "run",
      "sha256": "7799ae39cbbb5b007f12d6940a7e8b553d331b979f19abfe1c7011c53c3d9c17"
    },
    {
      "path": "artifacts/shared-replay-20260921/make-check.log",
      "role": "run",
      "sha256": "39748a5565b868f23e4848f3f2062e089e2305c88e7155a5233301da6b79cf5f"
    },
    {
      "path": "artifacts/shared-replay-20260921/development-01/round-1-old-default.log",
      "role": "run",
      "sha256": "bf4fb1feb82300fc7c33dd961b655fbf12d42c368cb2ce06bc24ece574e8b131"
    },
    {
      "path": "artifacts/shared-replay-20260921/development-02/round-1-old-default.log",
      "role": "run",
      "sha256": "4022783c6d3d9a3f64faa6c1285eac86e8c29d03731986256db937d987f9959f"
    },
    {
      "path": "artifacts/shared-replay-20260921/development-03/summary.json",
      "role": "results",
      "sha256": "97fffc3181d6baa4bb6de65965927f50c9608d058a34e430e9d8df63e0638c81"
    }
  ],
  "prior_work": [
    {
      "id": "native-generation-20260921",
      "relationship": "extends",
      "contribution": "Eliminates repeated Python rule validation through a bounded run-owned referee session shared across data consumers."
    }
  ],
  "novelty": "Measures full-pipeline backend substitution with unchanged per-move durability and independent post-run verification."
}
```
