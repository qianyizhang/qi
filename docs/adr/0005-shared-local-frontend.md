---
description: Use one local React frontend and extensible report projections over Python-owned evidence.
scope: architecture decision
status: stable
last_update: 2026-09-10
document_class: coordination
---

# ADR-0005: Shared local frontend and report projections

- **Status**: accepted
- **Last Update**: 2026-09-10

Extend the existing React/FastAPI app into one local frontend with Home, Play,
Experiments and Reference. Use shared native views and retain standalone offline
HTML plus Markdown summary export. The user accepted the stack and Markdown
authoring/export during the decision interview; Python-validated evidence feeds
every presentation format.

## Context

The game is served by FastAPI with a React/Vite frontend. Search reports are
separate standalone HTML files containing comparison, replay, tree inspection,
provenance and glossary views. Native integration creates shared navigation and
components, while offline export remains useful independently of the server.

Search experiments already own validation and summaries. CLI-created runs
remain usable inputs; discovery does not copy their evidence into another
authoritative store. Incomplete execution, invalid evidence and unsupported
formats need explicit presentation without being converted into results.

The local project has Python owners for rules, players, training, data and
evaluation. A frontend integration does not transfer these responsibilities.
Markdown supports authored narrative sections and summary export. Interactive
charts, boards and trees remain app-owned components over validated data;
report files do not execute JavaScript or acquire rules/measurement authority.

## Decision

- One local React/TypeScript/Vite application, served with the existing FastAPI
  backend. Route pages compose shared board, decision, glossary and report views.
- Use TanStack Router for typed navigation and URL filter state,
  TanStack Query for server reads, shadcn/ui and Tailwind for UI components.
  A React reducer/context owns active-game state and local restoration.
- Python readers validate supported experiment formats and derive their
  summaries. Native views and offline exports consume the same validated data;
  adding an output format does not create another computation pipeline.
- Separate supported experiment readers from presentation/output formats.
  Register additional readers and views explicitly as their contracts arrive.
  Markdown is narrative content and a static summary format; raw structured
  evidence retains its identity and machine-readable form.
- App navigation, cached server reads, and game execution have explicit,
  separate lifecycle owners. Existing state-hash checks and stale-response
  rejection remain necessary during player requests.

## Considered Options

- **Independent board and linked HTML reports**: least migration, but shared
  navigation, filters and cross-surface inspection remain fragmented. Suitable
  as an intermediate delivery stage, not the accepted final user experience.
- **One frontend with native views and offline exports**: selected to share
  interaction and components while retaining portable inspection. Requires an
  explicit shared report-data boundary and verification of rendering parity.
- **App-only reporting**: reduces export maintenance, but removes offline HTML
  use that the user explicitly retained.
- **A second application/backend for the lab**: permits independent development
  but duplicates navigation, API integration and deployment for a local project.
- **React Router/current CSS or minimal library additions**: viable smaller
  dependency changes; typed experiment URL state and owned reusable controls
  justify the selected router and component stack for the consolidated surface.
- **Executable Markdown/MDX report files**: unnecessary for narrative authoring;
  keep interactive behavior in tested application components and report content
  readable without a JavaScript execution environment.

## Consequences

The migration must preserve the board's request lifecycle, useful report
inspection, explicit evidence completeness, and offline report operation.
Evidence readers and metrics remain under their Python owners. Report
presentation may evolve without rewriting raw evidence or running players.

Experiment discovery is restricted to configured local artifact folders and
supported formats. It must not treat copied source trees or generated reports
as additional runs. Loading saved evidence does not activate checkpoints or
start experiments. The first UI may explicitly request a recorded decision's
trace; that is execution through the existing Python inspection boundary, not
an incidental effect of opening a report. Trace jobs and active games have
separate lifecycle contracts in the implementation specification.

The [work item](../../records/work-items/items/AB-UI-002-consolidated-lab.md)
owns the interview, delivery stages and acceptance criteria. Exact
dependency versions belong in the implementation lockfile after compatibility
checks, rather than being frozen by this decision. Acceptance defines the
architecture; the linked work item records implementation and verification.

## References

- [TanStack Router overview](https://tanstack.com/router/latest/docs/overview)
- [TanStack Query overview](https://tanstack.com/query/latest/docs/framework/react/overview)
- [shadcn/ui introduction](https://ui.shadcn.com/docs)
- [react-markdown](https://github.com/remarkjs/react-markdown)
