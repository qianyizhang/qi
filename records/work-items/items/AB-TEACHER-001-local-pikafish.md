---
description: Add a bounded local UCI teacher and validate pinned Pikafish.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-TEACHER-001
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-EVAL-001
residual_of: none
residual_items: none
---

# AB-TEACHER-001 — Local Pikafish teacher

## Intent

Query a replaceable local teacher without transferring referee authority.

## Acceptance Criteria

- Explicit executable/network identity, settings, and native budgets accompany analysis.
- Full replay history reaches the engine; qi rejects illegal proposals and terminal inputs.
- Deadline, output bounds, malformed response, crash, and process cleanup are tested.
- Pinned real Pikafish validates local integration; licenses and adjudication limits
  are documented. Default checks require no downloaded engine.

## Context and Trade-offs

User explicitly selected local Pikafish with a pinned release and bounded smoke
validation. Local noncommercial use fits this personal laboratory. Bundled weights
have a separate noncommercial restriction; future use outside that scope needs
review. Teacher labels do not enter the evaluation corpus or a training pipeline.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User confirmed local Pikafish scope |

| 2026-09-08 | Codex | wip | done | Full gate and twelve real-engine queries passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: official release metadata and extracted license texts; Apple Silicon
  executable identifies as Pikafish 2026-01-02 and accepts UCI options.
- Consequence: pin archive/binary/network hashes and preserve upstream license texts
  in ignored local artifacts. Keep native engine score semantics explicit.
- Follow-up: finish hermetic failure tests and multi-position real-engine smoke.
- Review: not-required.

### 2026-09-08 — verification

- Evidence: `make check` passed with 70 Python tests and the web/docs/build gates.
  Hermetic subprocess cases cover no-newline hangs, exit, output flood, missing
  options, malformed response, illegal/no moves, and reaped child processes.
  `scripts/check_teacher.py` passed twelve real queries over six replayable
  positions, including both turns and repeated-position history. Every proposal
  was legal and repeated fresh-process queries agreed; pinned hashes matched.
- Consequence: local analysis is usable without granting teacher access to players
  or claiming native scores obey qi adjudication. Setup validates archive hashes.
- Follow-up: browser baseline opponents. Training/redistribution remain future scope.
- Review: not-required.
