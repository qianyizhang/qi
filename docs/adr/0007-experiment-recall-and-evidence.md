---
description: Derive shared experiment discovery from evidence-linked entries in owning records.
scope: architecture decision
status: stable
last_update: 2026-09-10
document_class: coordination
---

# ADR-0007: Shared experiment recall and evidence-linked conclusions

- **Status**: accepted
- **Last Update**: 2026-09-10
- **Serves**: [Core model: experiment knowledge](../models.md#experiment-knowledge).

Keep each experiment's question, finding and decision in its existing work item
or report. Derive one catalog for CLI/API recall and the shared dashboard from
structured entries in those owners. Require agents to compare relevant previous
work before proposing a new experiment and record conclusions with evidence after
execution. The user accepted this boundary and authorized the skill, ADR, and
necessary tools after the September 9 teacher pilots were overlooked.

## Context

The teacher budget and MultiPV pilots already compared identical positions with
1M-node references. Their advisory and compact evidence survived, but discovery
was fragmented. The dashboard required a supported search manifest; learning
records used another index and teacher prototypes had no such manifest. A later
planning conversation read the advisory without reconciling its implications and
proposed overlapping work as new. Better search alone would not fix that behavior.

## Decision

- A stable experiment ID identifies a question/comparison; executions retain their
  original manifests, configs and status. The catalog does not convert prototype
  artifacts into supported runner formats or collapse multiple attempts into a run.
- Store versioned JSON `experiment` blocks in owning Markdown work items or
  reports. Each entry carries search topics, conditions, a contribution beyond
  prior work, execution state, conclusion, evidence references, decision and
  revisit trigger. Assessed findings must carry explicit limitations.
- CLI, HTTP and dashboard consume the same validated projection. Rich search
  replay/trace readers remain additional run views. Discovery must also work when
  local artifacts are absent or their formats are unsupported.
- Separate execution completion, scientific conclusion and local evidence
  availability. Negative, failed and partial work remains discoverable. Presence
  is not integrity verification; optional recorded SHA-256 checks report mismatch.
- Append conclusion revisions in the same owner, preserving earlier prose and
  blocks. Require the current owner hash before CLI writes. Last valid revision
  in one owner supplies the current view; cross-owner duplicate IDs and broken
  prior-work references are visible issues, never silent authority selection.
- The thin `experiment` skill routes agents through recall, comparison, authorized
  execution and evidence write-back. Recall applies before recommendation or
  decision grilling, not only before running. No-match results require searching
  owner prose and historical indexes before declaring work new.
- Use a repository check to validate the catalog; keep raw artifacts optional for
  portable checks. Keep HTTP read-only and evidence paths confined to declared
  references under the local workspace.

## Alternatives

A dashboard-only patch would leave agent recall separate. A new manually curated
registry or database would duplicate conclusion ownership and require another
synchronization step. Inferring conclusions from every discovered artifact would
mistake technical completion or a metric for scientific evidence. Requiring all
old studies to gain a common run manifest would hide useful unsupported history.
Structured blocks keep the catalog reconstructable from versioned owners while
supporting explicit validation and revision history without a database.

## Consequences and limits

New experiments need a small registration step and a clear comparison with prior
work. The catalog is only as complete as its registered owners; its scope and
issues remain visible, and a regression guards recall of the overlooked teacher
studies. Search is lexical over questions, topics, findings and limits; aliases
are authored topics, not an inference engine. The skill must read evidence and
explain comparability rather than treating a matching title as a settled answer.

Git retains owners and compact evidence; ignored raw runs still need their own
preservation. A hash cannot recover missing bytes. Append/CAS protects ordinary
owner revisions, not arbitrary concurrent filesystem writers or a tamper-proof
ledger. Historical registrations summarize existing evidence retrospectively;
they do not manufacture pre-registration or reproducibility.

The [experiment method](../experiments.md) owns the workflow;
[experiment module](../../src/qi/experiments/README.md) owns executable surfaces;
[AB-EXP-001](../../records/work-items/items/AB-EXP-001-experiment-recall.md)
owns implementation and verification.
