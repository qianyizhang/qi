---
description: Compare an imported C++ engine with a minimal C++ implementation for controlled Qi trajectories.
scope: native backend experiment
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-003
work_status: done
work_kind: research
added: 2026-09-21
tags: domain, native, performance
depends_on: AB-ARCH-002
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-003 — Imported versus minimal native execution

## Intent

Compare direct reuse of Fairy-Stockfish through pinned `pyffish==0.0.90`
with a small Qi-specific C++ implementation. Keep the current Python referee
as the differential reference. The user authorized both experimental approaches;
this study does not promote a production backend or replace search algorithms.

## Acceptance Criteria

- Retain runnable candidate sources, exact dependency/binary/build identities,
  frozen inputs, raw validation and timing records, including failures.
- Compare ordered moves, board/turn, checks, full-history adjudication, hashes,
  errors and atomicity; exercise the existing frozen referee fixtures.
- Compare controlled trajectories at the same per-game RNG and action ordering;
  test scalar and coarse native execution with different batch groupings.
- Record time, legal plies/s, completed games, workload truncations, startup and
  process peak RSS. Separate conformance from speed and learning/playing strength.
- Publish a catalog finding and a measured next decision. No default changes.

## Context and Trade-offs

[The architecture](AB-ARCH-001-modular-runtime.md) selected native batched
trajectories as the first acceptance workload. `movegen-layout-20260915`
established finite Python equivalence and speedups, and rejected one per-position
NumPy prototype. It did not test native implementations or training throughput.
This study extends those controls to a different language and compares reuse
with minimal reimplementation. [The game package](../../../packages/qi-game/README.md)
supplies contracts and the Python oracle; its injection alone does not replace
the generation/search loops.

### Frozen protocol, before candidate timing

- Baseline: current Python immutable `Game`, including its normal legal cache.
- Import: unmodified pinned pyffish binary; native legal/FEN/check operations,
  thin Python coordinate/order conversion and Qi repetition/ply adjudication.
  Retain current FEN rather than replaying the complete history every step.
- Minimal: C++17 compact board, native legality/transitions, exact repetition
  counts and Qi outcome precedence. No search, evaluator, teacher or neural model.
  Test scalar calls and full controlled-trajectory batches using the same core.
- Frozen controls: existing ten replay fixtures and two terminal diagrams;
  64 deterministic trajectories capped at 96 plies, independent confirmation
  seeds for timing, depth-three start-position perft, malformed/illegal moves,
  post-terminal rejection, stale guards, invalid-history rejection and input/result
  isolation. Batch versus scalar must match complete trajectory records.
- Actor: explicit unsigned xorshift32, one independent nonzero seed per game;
  choose by RNG modulo source-major/target-major ordered legal moves. No external
  teacher. RNG state persists per game and is independent of batch grouping.
- Timing: 128 confirmation games, at most 300 legal plies each; three isolated
  rounds with alternating candidate order. Native batch sizes 1, 8, 32, 128;
  imported and Python scalar execution use identical games. Startup measured
  separately; wall/CPU generation time includes final trajectory materialization.
  Clear Python reference caches at worker start; allow normal within-trial reuse.
- Run limit: 120 seconds per timing worker, 30 minutes total measured execution;
  retain failures/timeouts and do not rank a nonconforming arm. Candidate debugging
  uses development controls; freeze source/binaries before confirmation timing.
- Decision: a feasible candidate needs exact controlled conformance. Advance a
  native option only if each timing round improves over Python and median
  throughput gain is at least 2x on this workload. Favor direct reuse if within
  20% of the best minimal implementation; otherwise retain the maintenance/speed
  trade-off explicitly. These are exploratory advancement rules, not significance.
- Implementation effort: report source scope, dependency footprint and required
  rule adaptation. Do not infer speed from language or generalized superiority.

Teacher calls, production sampling/persistence, learned actors, native search,
Linux execution and default promotion are outside this first bounded comparison.
The host is Apple Silicon macOS. A native simulation result alone cannot establish
retained training examples/s or playing strength. Arbitrary diagrams are separate
controls, not an extension of the replay-only public Snapshot format.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User authorized direct import versus minimal implementation; protocol recorded before timing. |
| 2026-09-21 | GPT-6 | wip | done | Both candidates passed finite conformance; all 21 timing workers matched; results and next decision retained. |

## Implementation Ledger

- **2026-09-21 — decision:** Isolate optional dependencies and builds under
  `artifacts/native-backends-20260921`; retain new study sources under
  `data/experiments/native_backends_v1`. Preserve historical study sources and
  the supported workspace dependency graph. **Review:** not-required.
- **2026-09-21 — deviation:** Initial sandboxed dependency download failed due
  to restricted networking. Approved retry installed pyffish 0.0.90 from PyPI in
  the isolated target. This is setup evidence, not a candidate failure.
  **Review:** not-required.
- **2026-09-21 — verification:** Both backends matched ten frozen replays,
  two terminal diagrams, error/history/isolation controls and 6,075 development
  positions. Minimal native perft was 79,666; four batch sizes reproduced all
  64 development trajectories. Five focused tests passed, including the real
  HTTP boundary; ASan/UBSan passed. An initial HTTP test used a malformed hash
  and correctly received schema rejection; the test was corrected to use a
  well-formed stale hash. This was a test-fixture issue, not a backend failure.
  **Review:** not-required.
- **2026-09-21 — finding:** All 21 workers completed without timeouts or failures;
  every arm/round produced the same 128 games and 34,491 plies. Median times:
  Python 0.624 s, direct import 79.648 s, minimal scalar 0.356 s, minimal full-game
  call 0.160 s, 128-game native batch 0.192 s. The minimal full-game call improved
  paired throughput 3.80–3.91x and passed the predeclared advancement rule.
  [Report](../../reports/2026-09-21-native-backends.md) and
  [compact results](../../../data/evaluation/native-backends-20260921.json)
  retain all conditions, denominators and timing rows. **Review:** not-required.
- **2026-09-21 — finding:** A post-hoc four-game profile attributed 96.4% of
  measured time to the imported native legal/FEN API calls. Repeated variant
  initialization is an upstream-source-informed hypothesis, not verified native
  instruction-level attribution for the measured wheel. The frozen comparison
  was not changed after observing results. **Review:** not-required.
- **2026-09-21 — decision:** Advance the minimal C++ coarse loop to a realistic
  generation integration study; preserve the Python reference and current
  defaults. Revisit direct reuse with a persistent/coarse engine-core binding.
  This study establishes controlled trajectory execution only, not production
  training throughput, native search, Linux support or playing strength.
  **Review:** not-required.
- **2026-09-21 — verification:** Study lint/format, 137-document hygiene and
  ordinary catalog validation passed; the completed finding is discoverable.
  Recomputed all 28 live/frozen file identities and all 21 raw trajectory digests;
  every new catalog evidence digest matches. Global `--verify-evidence` reports
  one pre-existing mismatch for `scripts/import_benchmark_book.py` in AB-EVAL-005.
  That file is byte-identical to HEAD and was not changed by this task; the old
  evidence record remains untouched. Hardware sysctl queries were sandbox-denied;
  the retained manifest reports OS/ARM64, Python and compiler identity without
  inventing a CPU model or RAM capacity. **Review:** not-required.
- **2026-09-21 — verification:** Cleanup shortened the report and reproduction
  guide and made optional test dependencies candidate-specific. All five tests
  pass with the native artifacts; with neither candidate installed, the evidence
  guard passes and only four backend tests skip. The measured runner, C++ core,
  inputs, outputs and all 28 frozen file identities are unchanged; the original
  test file remains in the frozen tree. Pre-cleanup report bytes are retained,
  and a catalog revision refreshes editorial evidence hashes without changing
  the finding. **Review:** not-required.


```experiment
{
  "schema_version": 1,
  "id": "native-backends-20260921",
  "title": "Imported versus minimal C++ game execution",
  "question": "Which native replacement preserves Qi semantics and improves controlled trajectory throughput?",
  "kind": "performance",
  "topics": [
    "native",
    "C++",
    "referee",
    "pyffish",
    "batch trajectories"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "AB-ARCH-003 frozen protocol: pinned direct import vs minimal C++17, Python oracle, 64 development trajectories and 128 confirmation games, three isolated rounds.",
  "limitations": "Controlled random actors only; no production teacher/storage/training or playing-strength evidence. Apple Silicon host.",
  "decision": "Run conformance before ranking; no default promotion.",
  "revisit": "After the frozen comparison.",
  "evidence": [],
  "prior_work": [
    {
      "id": "movegen-layout-20260915",
      "relationship": "extends",
      "contribution": "Test native reuse versus minimal native implementation with full-history and trajectory controls."
    }
  ],
  "novelty": "Different-language execution and binding/batch costs, not another Python move-generation tuning study."
}
```


```experiment
{
  "schema_version": 1,
  "id": "native-backends-20260921",
  "title": "Imported versus minimal C++ game execution",
  "question": "Which native replacement preserves Qi semantics and improves controlled trajectory throughput?",
  "kind": "performance",
  "topics": [
    "native",
    "C++",
    "referee",
    "pyffish",
    "batch trajectories"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "Both backends passed 6075 development positions and frozen rule/history controls. All 21 isolated workers matched 128 games/34491 plies. Median paired speedups: minimal full-game C++ call 3.91x, native batch 128 3.22x, scalar C++ 1.76x; direct pyffish 0.0.90 import 0.00783x. Five HTTP/atomicity/evidence tests and native ASan/UBSan passed.",
  "conditions": "Apple Silicon macOS; identical xorshift32 controlled actors, ordered actions and 128 confirmation seeds; 300-ply ruleset; three alternating isolated rounds. Time includes final trajectory materialization. Source, binaries, inputs and raw results frozen. Post-hoc four-game imported-call diagnostic separate.",
  "limitations": "Finite conformance and short native timing windows; uncontrolled desktop load. Imported wheel compiler/flags unknown. Import API and minimal loop have different boundaries. No persistent wrapper around Fairy-Stockfish core, production teacher/storage/training, native search, Linux or strength measurement.",
  "decision": "Advance minimal C++ coarse trajectory execution to realistic generation integration; retain Python oracle and current defaults. Direct unmodified import failed the speed criterion.",
  "revisit": "Production generation workload and Linux/lifecycle checks before adoption; reconsider reuse with a persistent coarse engine-core binding.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-native-backends.md",
      "role": "report",
      "sha256": "bde31d52a5a05bb80acdf62acf6b00cd090a7059e14adcfe69052f0d3f30e256"
    },
    {
      "path": "data/evaluation/native-backends-20260921.json",
      "role": "results",
      "sha256": "047387748e16ab67db5387e41d5a432dd2279b133f85485168b531ba43d3deae"
    },
    {
      "path": "data/experiments/native_backends_v1/study.py",
      "role": "source",
      "sha256": "518ac185345575db5d36f16f783c18b99f9fdfe8c4f5bc06ac32bf76215eef05"
    },
    {
      "path": "data/experiments/native_backends_v1/minimal.cpp",
      "role": "source",
      "sha256": "20bd0b97b31e62a1fb208d6ae4dd7fe8b175693faa625f0d36891518ce738942"
    },
    {
      "path": "data/experiments/native_backends_v1/requirements.txt",
      "role": "config",
      "sha256": "da0dea8ed81169b5249b944e7bbfc4b635f9e05dfd6102bc2eda32124e89801a"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/inputs.json",
      "role": "config",
      "sha256": "2878d19824577e624c57b8a7233d7f53b5c5e114804e3c43727cb13a61ed10b4"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "0dca3b06a397371788e0fd33d4bcbf9f13386f2b345495476acda8f8eedcfdad"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/validation.json",
      "role": "results",
      "sha256": "8468e09ffe8d6473d72256854e5270bfad2340402e4ff3a140ebedb17cf55817"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "262faab96ea7f2d46f9b65198bb23e44a6843abf4be356c09c15097ea1850070"
    },
    {
      "path": "artifacts/native-backends-20260921/import-diagnostic.txt",
      "role": "results",
      "sha256": "3a32c58ae7e8be3a9cf77d9e74f49a5807f16f971920e476ba49b07da346ca5b"
    }
  ],
  "prior_work": [
    {
      "id": "movegen-layout-20260915",
      "relationship": "extends",
      "contribution": "Test native reuse versus minimal native implementation with full-history and trajectory controls."
    }
  ],
  "novelty": "Different-language execution and binding/batch costs, not another Python move-generation tuning study."
}
```


```experiment
{
  "schema_version": 1,
  "id": "native-backends-20260921",
  "title": "Imported versus minimal C++ game execution",
  "question": "Which native replacement preserves Qi semantics and improves controlled trajectory throughput?",
  "kind": "performance",
  "topics": [
    "native",
    "C++",
    "referee",
    "pyffish",
    "batch trajectories"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "Both backends passed 6075 development positions and frozen rule/history controls. All 21 isolated workers matched 128 games/34491 plies. Median paired speedups: minimal full-game C++ call 3.91x, native batch 128 3.22x, scalar C++ 1.76x; direct pyffish 0.0.90 import 0.00783x. Five HTTP/atomicity/evidence tests and native ASan/UBSan passed.",
  "conditions": "Apple Silicon macOS; identical xorshift32 controlled actors, ordered actions and 128 confirmation seeds; 300-ply ruleset; three alternating isolated rounds. Time includes final trajectory materialization. Source, binaries, inputs and raw results frozen. Post-hoc four-game imported-call diagnostic separate.",
  "limitations": "Finite conformance and short native timing windows; uncontrolled desktop load. Imported wheel compiler/flags unknown. Import API and minimal loop have different boundaries. No persistent wrapper around Fairy-Stockfish core, production teacher/storage/training, native search, Linux or strength measurement.",
  "decision": "Advance minimal C++ coarse trajectory execution to realistic generation integration; retain Python oracle and current defaults. Direct unmodified import failed the speed criterion.",
  "revisit": "Production generation workload and Linux/lifecycle checks before adoption; reconsider reuse with a persistent coarse engine-core binding.",
  "evidence": [
    {
      "path": "records/reports/2026-09-21-native-backends.md",
      "role": "report",
      "sha256": "c8dba4c239e3a6b358a45c39d2b35132a2381c82085c2a7c09a59bfb7863e9c2"
    },
    {
      "path": "data/evaluation/native-backends-20260921.json",
      "role": "results",
      "sha256": "047387748e16ab67db5387e41d5a432dd2279b133f85485168b531ba43d3deae"
    },
    {
      "path": "data/experiments/native_backends_v1/study.py",
      "role": "source",
      "sha256": "518ac185345575db5d36f16f783c18b99f9fdfe8c4f5bc06ac32bf76215eef05"
    },
    {
      "path": "data/experiments/native_backends_v1/minimal.cpp",
      "role": "source",
      "sha256": "20bd0b97b31e62a1fb208d6ae4dd7fe8b175693faa625f0d36891518ce738942"
    },
    {
      "path": "data/experiments/native_backends_v1/requirements.txt",
      "role": "config",
      "sha256": "da0dea8ed81169b5249b944e7bbfc4b635f9e05dfd6102bc2eda32124e89801a"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/inputs.json",
      "role": "config",
      "sha256": "2878d19824577e624c57b8a7233d7f53b5c5e114804e3c43727cb13a61ed10b4"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/manifest.json",
      "role": "source",
      "sha256": "0dca3b06a397371788e0fd33d4bcbf9f13386f2b345495476acda8f8eedcfdad"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/validation.json",
      "role": "results",
      "sha256": "8468e09ffe8d6473d72256854e5270bfad2340402e4ff3a140ebedb17cf55817"
    },
    {
      "path": "artifacts/native-backends-20260921/confirmation-01/summary.json",
      "role": "results",
      "sha256": "262faab96ea7f2d46f9b65198bb23e44a6843abf4be356c09c15097ea1850070"
    },
    {
      "path": "artifacts/native-backends-20260921/import-diagnostic.txt",
      "role": "results",
      "sha256": "3a32c58ae7e8be3a9cf77d9e74f49a5807f16f971920e476ba49b07da346ca5b"
    },
    {
      "path": "artifacts/native-backends-20260921/cleanup-01/report-before.md",
      "role": "report",
      "sha256": "bde31d52a5a05bb80acdf62acf6b00cd090a7059e14adcfe69052f0d3f30e256"
    },
    {
      "path": "artifacts/native-backends-20260921/cleanup-01/verification.json",
      "role": "results",
      "sha256": "75adb51a7ce58680b21ede6a69d887a75fea0bcd9718ef028fa4ce95799719cd"
    }
  ],
  "prior_work": [
    {
      "id": "movegen-layout-20260915",
      "relationship": "extends",
      "contribution": "Test native reuse versus minimal native implementation with full-history and trajectory controls."
    }
  ],
  "novelty": "Different-language execution and binding/batch costs, not another Python move-generation tuning study."
}
```
