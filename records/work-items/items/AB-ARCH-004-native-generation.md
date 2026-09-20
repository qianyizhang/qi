---
description: Integrate optional persistent C++ game execution and measure real generation costs.
scope: native trajectory integration
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-004
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, native, performance
depends_on: AB-ARCH-003
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-004 — Native trajectory integration

## Intent

Advance the minimal core from [AB-ARCH-003](AB-ARCH-003-native-backend-experiment.md)
into an optional package and the existing policy generation runner. The user
requested an unresolved-decision check followed by implementation if settled.
The accepted architecture and prior advancement decision leave no blocking
choice: C++ execution, explicit opt-in, Python actors/data ownership, exact
history semantics and retained reference validation already determine this slice.

## Acceptance Criteria

- Package-owned build dependencies; default installation needs no compiler.
- Persistent, exclusively owned native state; replay restoration, detached
  inspection, guarded stepping and caller-supplied atomic batches of 1..128 games.
- Frozen replay and complete differential trajectory conformance, rejection
  atomicity, resource cleanup, real generation actor/sampling/recovery parity.
- Preserve RNG streams, lexical actor move ordering, per-move durability and
  current sampler/teacher interfaces. Record backend identity independently of
  semantic actor/state identities. No search or scheduling redesign.
- Isolated package checks, sanitizer checks and applicable application gates.
- Retained source/config/binary identities and raw results; a catalog conclusion
  about integration throughput, distinct from prior native-only throughput.

## Context and Trade-offs

Native execution is explicit and does not change shared defaults. The independent
batch API is useful without committing to a concurrent generation scheduler.
Per-move collection validation may dominate this bounded integration; preserving
that durability and evidence boundary is part of the comparison, not a reason
to exclude its cost.

### Frozen comparison protocol

Predeclared before timing. Prior `native-backends-20260921` found a 3.91x median
gain for a complete controlled native game and 1.76x for scalar calls. It excluded
generation actors, teacher validation, sampling and storage. This extension tests
those actual costs; it does not presume the earlier gain survives them.

- Compare Python and optional C++ through the same persistent interface in the
  real `generate_policies` runner, fresh process and SQLite collection per cell.
  Also retain the pre-integration runner from commit `41fdb96` as a baseline
  control to detect overhead introduced by the new seam.
- Primary: 64 initial-position random-actor games, seed 29, maximum 300 plies,
  unchanged `policy-moves-v1` Python RNG and lexical action ordering, normal
  phase sampler (2 opening, 4 middlegame, 2 endgame), min spacing 4/min ply 1.
  A deterministic legal supervision fixture isolates referee/data costs; its
  labels have no teaching-quality interpretation. Three alternating rounds.
- Real-teacher pilot: four plausible-actor games capped at 32 plies, seed 29,
  local pinned Pikafish/NNUE, one thread, 1,000 nodes, one supervision recipe,
  otherwise the same pipeline. Two alternating paired rounds, diagnostic only.
- Frozen development controls precede timing. Clear reference caches before
  execution; normal within-run cache reuse is allowed. No parallel timing cells.
- Record wall/CPU time, peak RSS, legal plies and selected examples per second,
  outcomes, sampling shortfalls and semantic digests of trajectories, decisions,
  retained occurrences and supervision. Strip only runtime/provenance fields
  when comparing semantic results. Verify all final replays and SQLite integrity.
- Phase timers cover execution/inspection, per-move append and sampling;
  provider counters retain their existing scope. A separate post-hoc profile
  may explain the remainder; these timers do not exhaust wall time.
- Freeze sources, lock, extension and baseline copy before confirmation; retain
  raw attempts and fail on mismatch. Maximum 180 seconds per cell and 20 minutes
  total measured work; failure is evidence, not permission to relax equality.
- Exact conformance is mandatory. A median end-to-end gain of at least 1.2x
  with every primary round faster justifies further adoption work; otherwise
  retain opt-in status and identify the next measured bottleneck. Flag a median
  reference-interface regression above 5% against the old runner. These are
  engineering advancement rules, not a significance or strength claim.
- Batch stepping is independently verified. The existing runner remains serial
  and externally driven; this study does not claim the complete-loop performance
  of AB-ARCH-003 or evidence for a concurrent teacher scheduler.

## Execution Log

- Implementation and differential controls underway; historical sources unchanged.
- First confirmation: all nine workers matched 64 games, 17,169 plies and
  417 selected examples. Median old-Python/native speedup 0.810x; persistent
  Python adapter took 1.118x the original runtime. No throughput advancement.
- Before follow-up timing: preserve the direct Python default instead of adding
  the adapter's observed overhead. Recheck that correction with three alternating
  rounds of original runner, corrected default and explicit native, on identical
  frozen inputs. Use the corrected default in the two-round real-teacher pilot.
  This is a recorded implementation refinement, not a replacement for the first
  confirmation result. Keep both source snapshots and all raw cells.
- Follow-up confirmation: all nine cells retained exact parity; median native
  throughput 0.835x the corrected default, below the 1.2x threshold. Default
  runtime was 0.996x the old runner. All four real-teacher cells matched 128 plies
  and 20 selections, with a 1.030x paired native gain and opposite round winners.
  Keep native explicit/experimental. [The report](../../reports/2026-09-21-native-generation.md)
  owns measured interpretation and reproduction; no further owner decision was
  needed to preserve the direct default and record the negative result.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | Authorized native integration after resolving the decision frontier. |
| 2026-09-21 | GPT-6 | wip | done | Optional integration, conformance, isolated build, comparison and full application gates completed. |

## Implementation Ledger

- 2026-09-21: Added optional package, persistent execution boundary, supplied-action
  atomic batches, generation injection and run execution identity. Differential
  generation tests, isolated native wheel and standalone ASan/UBSan passed;
  confirmation timing and broader gates remain underway.
- **2026-09-21 — verification:** Full application gate passed (785 Python tests,
  one skip; five browser tests); native isolated wheel passed eight tests; core
  ASan/UBSan passed, including both terminal-precedence diagrams. Final default,
  persistent Python and native paths matched all three actor policies, sampling,
  supervision and resume. Source archives for all 22 confirmation workers verify.
  Historical AB-ARCH-003 files were preserved. **Review:** not-required.
- **2026-09-21 — finding:** Native execution does not advance the 1.2x full-pipeline
  criterion. A separate profile locates duplicate Python rule validation and
  persistence overhead; revisit the collection/sampling execution boundary before
  tuning native move generation. Linux CI is configured, not locally executed.
  **Review:** not-required.
- **2026-09-21 — closeout:** Isolated reference wheel passed 68 tests; the default
  install dry-run excludes the native package. All current study evidence hashes
  verify. Global evidence verification retains the previously known, unrelated
  AB-EVAL-005 digest mismatch for `scripts/import_benchmark_book.py`; that file
  was not changed here. **Review:** not-required.


```experiment
{
  "schema_version": 1,
  "id": "native-generation-20260921",
  "title": "Native trajectory generation integration",
  "question": "Does optional persistent C++ execution improve real policy generation while preserving its evidence?",
  "kind": "performance",
  "topics": [
    "native",
    "C++",
    "generation",
    "trajectory",
    "persistence"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "AB-ARCH-004: three alternating rounds of 64 controlled random-actor games, 300-ply cap, seed 29; pre-integration runner control; separate pinned real-teacher pilot.",
  "limitations": "",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "native-backends-20260921",
      "relationship": "extends",
      "contribution": "Tests the winning minimal C++ core inside actual actor, sampling, supervision and collection execution."
    }
  ],
  "novelty": "Adds persistent package lifecycle, caller-supplied atomic batches and actual generation cost/evidence parity."
}
```


```experiment
{
  "schema_version": 1,
  "id": "native-generation-20260921",
  "title": "Native trajectory generation integration",
  "question": "Does optional persistent C++ execution improve real policy generation while preserving its evidence?",
  "kind": "performance",
  "topics": [
    "native",
    "C++",
    "generation",
    "trajectory",
    "persistence"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "Optional C++ package and generation integration passed conformance. All 18 primary workers matched 64 trajectories/17169 plies/417 selections. Final native throughput was 0.835x the direct Python default; a detected Python-adapter regression was removed from the default. Four real-teacher cells matched 128 plies/20 selections with 1.030x paired gain and opposite round winners.",
  "conditions": "macOS ARM64, Python 3.12; three alternating rounds before and after preserving the direct default. Primary random actor uses existing Python RNG and sampler with deterministic fixture supervision. Separate two-round four-game/32-ply plausible-actor pilot uses pinned Pikafish, one thread, 1000 nodes. Fresh process and collection per cell; full raw semantic records and source/binary snapshots retained.",
  "limitations": "Finite conformance; short local timing windows and uncontrolled desktop load. Native batches independently tested but generation remains serial. Collection/sampling still execute Python rules. Fixture labels do not establish data quality. Worker CPU/RSS omit teacher child costs. Linux CI configured but not locally executed; no strength result.",
  "decision": "Keep direct Python as default and native explicitly experimental. Do not advance adoption: native fails the predeclared 1.2x end-to-end criterion. Preserve both confirmation attempts and their source snapshots.",
  "revisit": "Extend replaceable execution through incremental collection validation and sampler observations while preserving per-move durability, then rerun full-pipeline parity and throughput. Profiled append/validation duplication is the next target.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-native-generation.md",
      "role": "report",
      "sha256": "8cbd78d90633fdea5ea163fa0c337050de93a1f557fece9f7e2086a570ac1f5f"
    },
    {
      "path": "data/evaluation/native-generation-20260921.json",
      "role": "results",
      "sha256": "b39f964154b4b3cef5f2d0302735a5086837e9b6aa29dc00b5444e83355fa297"
    },
    {
      "path": "scripts/benchmark_native_generation.py",
      "role": "source",
      "sha256": "076066bb4f055610c083b15590a9fa626b86f2b255713bdde5070260abf261b9"
    },
    {
      "path": "src/qi/training_data/generation_runner.py",
      "role": "source",
      "sha256": "658b0c0b87cf8cd73f25ff77ee7bb191b91ed059b983c285b6285e733edf49fa"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "f902661cfca50e563cfba8192e08222104093343ba100f7c6937e275a545b1c6"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-02/summary.json",
      "role": "results",
      "sha256": "90f6e7e0124ba07abeabfe51d580f867b3c6988ebe82c846bd104418975118c0"
    },
    {
      "path": "artifacts/native-generation-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "2d48e961ce9fe01c642b1a71fd6df0e337dbdbd24c459a47cd1d0d711afacea1"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "87a5c0f52d84cb4a96e2b407a3dfec267b769c21e4136410ab403527109e889e"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-02/manifest.json",
      "role": "source",
      "sha256": "219284590250ef638a7fb6f43e0fe7fa403a7a5ad77ebf58af8a5aad0f9e6e9b"
    },
    {
      "path": "artifacts/native-generation-20260921/teacher-01/manifest.json",
      "role": "source",
      "sha256": "5e817bb63ba548da3392c3a69c873d9a9e7fef9bcf90bd161b24e8f1a316cb11"
    },
    {
      "path": "artifacts/native-generation-20260921/package-check.log",
      "role": "run",
      "sha256": "59f38f0ba5856965a0e323056fdd8281d6d3e83450672bb4a2a0683e37c87c72"
    },
    {
      "path": "artifacts/native-generation-20260921/reference-package-check.log",
      "role": "run",
      "sha256": "982b833f2de6cc63eefb3c7b75f93cad966a31dbe2f7b35328f3d5ebed4402aa"
    },
    {
      "path": "artifacts/native-generation-20260921/make-check.log",
      "role": "run",
      "sha256": "a85f04308187ee88687c1dd31fa06f75630b209fd78e7de99b73d009027e6407"
    },
    {
      "path": "artifacts/native-generation-20260921/profile-01/diagnostic.txt",
      "role": "run",
      "sha256": "9a9a4e18bb9c25f165a25d0814423cb34336e60b2a7e8e4d91175f0737b58595"
    }
  ],
  "prior_work": [
    {
      "id": "native-backends-20260921",
      "relationship": "extends",
      "contribution": "Tests the winning minimal C++ core inside actual actor, sampling, supervision and collection execution."
    }
  ],
  "novelty": "Adds persistent package lifecycle, caller-supplied atomic batches and actual generation cost/evidence parity."
}
```


```experiment
{
  "schema_version": 1,
  "id": "native-generation-20260921",
  "title": "Native trajectory generation integration",
  "question": "Does optional persistent C++ execution improve real policy generation while preserving its evidence?",
  "kind": "performance",
  "topics": [
    "native",
    "C++",
    "generation",
    "trajectory",
    "persistence"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "Optional C++ package and generation integration passed conformance. All 18 primary workers matched 64 trajectories/17169 plies/417 selections. Final native throughput was 0.835x the direct Python default; a detected Python-adapter regression was removed from the default. Four real-teacher cells matched 128 plies/20 selections with 1.030x paired gain and opposite round winners.",
  "conditions": "macOS ARM64, Python 3.12; three alternating rounds before and after preserving the direct default. Primary random actor uses existing Python RNG and sampler with deterministic fixture supervision. Separate two-round four-game/32-ply plausible-actor pilot uses pinned Pikafish, one thread, 1000 nodes. Fresh process and collection per cell; full raw semantic records and source/binary snapshots retained.",
  "limitations": "Finite conformance; short local timing windows and uncontrolled desktop load. Native batches independently tested but generation remains serial. Collection/sampling still execute Python rules. Fixture labels do not establish data quality. Worker CPU/RSS omit teacher child costs. Linux CI configured but not locally executed; no strength result. Evidence locator revision during AB-ARCH-005: the generation-runner source now points to its identical frozen confirmation-02 copy; original findings and retained source bytes are unchanged.",
  "decision": "Keep direct Python as default and native explicitly experimental. Do not advance adoption: native fails the predeclared 1.2x end-to-end criterion. Preserve both confirmation attempts and their source snapshots.",
  "revisit": "Extend replaceable execution through incremental collection validation and sampler observations while preserving per-move durability, then rerun full-pipeline parity and throughput. Profiled append/validation duplication is the next target.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-native-generation.md",
      "role": "report",
      "sha256": "8cbd78d90633fdea5ea163fa0c337050de93a1f557fece9f7e2086a570ac1f5f"
    },
    {
      "path": "data/evaluation/native-generation-20260921.json",
      "role": "results",
      "sha256": "b39f964154b4b3cef5f2d0302735a5086837e9b6aa29dc00b5444e83355fa297"
    },
    {
      "path": "scripts/benchmark_native_generation.py",
      "role": "source",
      "sha256": "076066bb4f055610c083b15590a9fa626b86f2b255713bdde5070260abf261b9"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-02/frozen/src/qi/training_data/generation_runner.py",
      "role": "source",
      "sha256": "658b0c0b87cf8cd73f25ff77ee7bb191b91ed059b983c285b6285e733edf49fa"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "f902661cfca50e563cfba8192e08222104093343ba100f7c6937e275a545b1c6"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-02/summary.json",
      "role": "results",
      "sha256": "90f6e7e0124ba07abeabfe51d580f867b3c6988ebe82c846bd104418975118c0"
    },
    {
      "path": "artifacts/native-generation-20260921/teacher-01/summary.json",
      "role": "results",
      "sha256": "2d48e961ce9fe01c642b1a71fd6df0e337dbdbd24c459a47cd1d0d711afacea1"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "87a5c0f52d84cb4a96e2b407a3dfec267b769c21e4136410ab403527109e889e"
    },
    {
      "path": "artifacts/native-generation-20260921/confirmation-02/manifest.json",
      "role": "source",
      "sha256": "219284590250ef638a7fb6f43e0fe7fa403a7a5ad77ebf58af8a5aad0f9e6e9b"
    },
    {
      "path": "artifacts/native-generation-20260921/teacher-01/manifest.json",
      "role": "source",
      "sha256": "5e817bb63ba548da3392c3a69c873d9a9e7fef9bcf90bd161b24e8f1a316cb11"
    },
    {
      "path": "artifacts/native-generation-20260921/package-check.log",
      "role": "run",
      "sha256": "59f38f0ba5856965a0e323056fdd8281d6d3e83450672bb4a2a0683e37c87c72"
    },
    {
      "path": "artifacts/native-generation-20260921/reference-package-check.log",
      "role": "run",
      "sha256": "982b833f2de6cc63eefb3c7b75f93cad966a31dbe2f7b35328f3d5ebed4402aa"
    },
    {
      "path": "artifacts/native-generation-20260921/make-check.log",
      "role": "run",
      "sha256": "a85f04308187ee88687c1dd31fa06f75630b209fd78e7de99b73d009027e6407"
    },
    {
      "path": "artifacts/native-generation-20260921/profile-01/diagnostic.txt",
      "role": "run",
      "sha256": "9a9a4e18bb9c25f165a25d0814423cb34336e60b2a7e8e4d91175f0737b58595"
    }
  ],
  "prior_work": [
    {
      "id": "native-backends-20260921",
      "relationship": "extends",
      "contribution": "Tests the winning minimal C++ core inside actual actor, sampling, supervision and collection execution."
    }
  ],
  "novelty": "Adds persistent package lifecycle, caller-supplied atomic batches and actual generation cost/evidence parity."
}
```
