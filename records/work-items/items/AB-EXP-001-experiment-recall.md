---
description: Share experiment recall across agents and the dashboard and preserve evidence-linked conclusions.
scope: backlog item
status: stable
last_update: 2026-09-10
document_class: work_record
work_id: AB-EXP-001
work_status: done
work_kind: build
added: 2026-09-10
tags: hygiene, frontend
depends_on: none
residual_of: none
residual_items: none
---

# AB-EXP-001 — Experiment recall and conclusion recording

## Intent

Prevent new ideas from overlooking previous experiments. Make the shared dashboard
and agent CLI read the same evidence-linked catalog, with a thin workflow that
requires prior-work comparison and records new findings in their owning records.

## Acceptance Criteria

- One validated catalog spans teacher, learning, search, data and performance work,
  including unsupported raw formats and absent local artifacts.
- CLI search/show/owner/template/record/check surfaces and HTTP/dashboard read
  the same projection. Updates retain original owner bytes and reject stale edits.
- Execution status, conclusion and evidence availability remain distinct; negative,
  partial and inconclusive findings remain discoverable with conditions and limits.
- The `experiment` skill and repository routing require recall before proposing or
  grilling new experimental work and evidence write-back after authorized execution.
- An accepted ADR records authority and discovery boundaries. Historical teacher
  budget and MultiPV studies are found by teacher quality / stronger teacher /
  1M reference queries. Existing indexed learning studies receive entries too.
- Repository and browser checks verify discovery, write-back and evidence navigation.

## Context and Trade-offs

[ADR-0007](../../../docs/adr/0007-experiment-recall-and-evidence.md) records the
accepted boundary. Catalog entries live in existing owners. This scaffolding
commissions no new teacher audit, student training or default change.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | wip | User authorized skill, ADR and shared CLI/dashboard scaffolding after the teacher-pilot recall failure. |

| 2026-09-10 | Codex | wip | done | Shared catalog, skill/ADR, fifteen historical registrations and CLI/dashboard recording workflow passed repository and desktop/mobile checks. |

## Implementation Ledger

### 2026-09-10 — decision: shared discovery with owner-based write-back

- Evidence: the prior teacher advisory and compact receipts survived while native
  dashboard discovery required supported search manifests. Planning failed to
  compare the advisory with the proposed study.
- Consequence: structured owner entries drive the common catalog; the workflow
  requires an explicit prior-work/contribution comparison before new proposals.
- Follow-up: validate CLI/API parity, missing-evidence recall and browser navigation.
- Review: ratified by the user's scaffolding authorization; no open scientific protocol decisions.


### 2026-09-10 — verification: recall, recording and dashboard

- Evidence: `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed:
  472 Python tests, one opt-in GPU skip, five browser request tests, docs/lint,
  type checks and production builds. `npm run test:e2e --prefix web` passed all
  44 desktop/mobile checks; the sandbox-only port-binding restriction required
  the approved local-server test lane. Catalog screenshots were inspected.
- Evidence: `qi experiment check-catalog --verify-evidence --summary` reports
  fifteen entries and no issues. Registered compact and available supplied raw
  hashes match. Tests cover CLI record → HTTP parity, preserved original bytes,
  stale-owner rejection, invalid entries, duplicate IDs, missing predecessors,
  path escape, missing artifacts and negative/partial conclusions.
- Evidence: regression queries teacher quality / stronger teacher / 1M reference
  all retrieve the September 9 budget and MultiPV pilots. The browser fixture
  verifies discovery without manifests, missing-evidence labels, source-owner
  links and text evidence on desktop/mobile. Historical learning-index rows are
  represented by study entries, retaining interrupted attempts and shortfalls in
  their owning histories and linked compact evidence.
- Skill validation: repository governance/frontmatter checks passed. The generic
  skill validator passed on standard name/description/body metadata; repo-only
  version/scope/status/date/class fields remain validated by `check_docs.py`.
  Its YAML dependency was loaded from the existing local cache without adding a
  project dependency. Authoring check returned advisory findings only.
- Consequence: the catalog supplies common discovery, while the skill and root
  routing require evidence comparison before a proposal and write-back after
  authorized experiments. No new experiment or scientific default is chosen here.
- Follow-up: register future experiments and recovered history in their owners;
  empty searches still require owner/index fallback. Revisit the schema when a
  concrete experiment cannot express its question, execution history or evidence.
- Review: not-required; verified local implementation of the accepted ADR.


### 2026-09-10 — verification: retire stale discovery guidance

- Evidence: active app/module descriptions still characterized all experiment
  discovery as search-manifest discovery; the interface guide omitted catalog
  routes, and the learning recipe guide repeated a persistent-teacher finding.
- Consequence: corrected current routes and module scope, removed the obsolete
  renderer migration sentence, and replaced duplicated findings with owner/catalog
  links. Recipe mappings, historical scripts and native search replay remain useful
  evidence surfaces and were retained. No artifact or measured history was deleted.
- Evidence: a fresh-checkout check exposed eight pre-existing Markdown links to
  ignored UI verification files. Their owning frontend records now retain explicit
  local artifact paths, preserving the references without broken portable links.
- Verification: `make check` passed on an isolated copy of the exact commit
  contents (464 passed, 1 skipped, one opt-in GPU skip, five browser unit
  tests, docs/lint/type checks and production builds), without local artifacts or
  concurrent teacher-quality source changes.
- Follow-up: commit the catalog slice independently of concurrent teacher-quality
  implementation; keep current source guides aligned with their owning APIs.
- Review: not-required; user-authorized cleanup against ADR-0007.
