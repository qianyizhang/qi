---
description: Local app, player selection, replay, saved sessions and experiment interfaces.
scope: local lab interfaces
status: stable
last_update: 2026-09-11
document_class: coordination
---

# Game interface

Files `a`–`i` run left to right from Red's view; ranks `0`–`9` run from
Red's home rank to Black's. A move concatenates source and destination, such as
`b2e2`. Uppercase pieces are Red; lowercase are Black. Piece letters are
`K A B N R C P` (general, advisor, elephant, horse, chariot, cannon, soldier).

Saved JSON contains `schema_version: 1`, `ruleset: "xiangqi-training-v1"`,
`initial_fen`, and ordered `moves`. This slice accepts the standard initial
position only. Replay reconstructs all derived state and rejects invalid history.
The snapshot is portable data, not a server session identifier.

Python owns referee operations. JSON CLI and HTTP are adapters. HTTP exposes
`POST /api/new`, `/api/inspect`, and `/api/apply`; API schemas are available at
`/docs`. Apply requires `expected_state_hash`, snapshot, and move. The hash covers
ruleset and full history, not just the board. Invalid actions return structured
errors and cannot change the input snapshot. Referee move operations are stateless.
Trace jobs have a separate server-owned
lifecycle; remote multiplayer is not implemented.

CLI stdout contains one JSON object; errors use a structured stderr object and
nonzero exit status. Save stdout to a different file from the input snapshot.
Browser exports use the same snapshot and import validates it before replacement.
Replay navigation is read-only; return to the last move to continue playing.

## Unified local app

Routes `/`, `/play`, `/data`, `/learn/generation`, `/experiments`, `/experiments/:runId`, and `/reference`
share a React/TypeScript/Vite frontend and FastAPI server. TanStack Router owns
navigation and report URL filters; TanStack Query owns server reads. Source-owned
shadcn/ui controls and Tailwind styles are shared with the offline report build.
`web/src/session.tsx` owns the active game through a reducer/context. The board
renders legal moves supplied by Python; it does not implement rules.

`web/openapi.json` and `web/src/generated-api.ts` derive from Python HTTP models.
Run `npm run generate:api --prefix web` after changing an API contract, then build.
The legacy `POST /api/opponent` remains available with depth 1–4 and nodes 1–512.
The new app uses `POST /api/play/choose` with an explicit controller selection.

## Players and settings

`GET /api/players` exposes implementation/version, binding ID/label, content
identity, availability, and capability-specific defaults, units and ceilings.
Each Red/Black controller is Human or a selected player. Named bindings permit
two independent trained checkpoints and explicit Pikafish participation.
[Player configuration](../src/qi/players/README.md#named-player-bindings) owns
server resource setup; HTTP accepts IDs and expected identities, never paths.

The server rejects unsupported settings and budgets outside the advertised
bounds. Random/MCTS seeds are base seeds; each decision adds its absolute ply.
Search uses qi visit budgets, while Pikafish reports native nodes/depth and
cp/mate scores separately, retaining unknown counters, bounds and perspective.
Pikafish has a finite per-move timeout; threads/hash/paths are server settings.
A policy checkpoint exposes no ineffective search controls.

## Play lifecycle and saved sessions

Numeric settings are edited together per side. Apply settings validates and saves
them as one configuration change; Discard restores the saved values. Step and
Resume wait while either side has unapplied settings.

Damaged local saves expose a recovery action that preserves the original bytes
in a separate local backup before starting a new session.

Resume enables automatic computer turns. Step makes one computer move. Pause,
leaving Play, hiding the browser tab, replay, restore, import, new game, settings
changes and errors invalidate pending results. Returning to live play requires
explicit Resume. An aborted request may finish on the server within its budget;
request generation and full-state hashes prevent its result from replacing a
newer session. Query retries/refocus never choose a move.

Players and settings can change while paused and affect only future moves.
One active session is saved in local storage under `qi.active-session.v1` after
accepted changes. Web Locks serialize writes across tabs, and saved revisions
reject stale tabs. A tab that observes another writer pauses and offers Load
saved session. Restore validates evidence through Python and always pauses;
unavailable or changed resources require explicit player reselection.

The `qi-game-session` version-1 format contains the referee snapshot, current
controllers, ordered configuration changes at ply boundaries, and contiguous
known move attribution. Each computer move retains its actual pinned config and
Choice; human moves are explicitly attributed. Snapshot-only imports record an
unknown prefix. `POST /api/play/session/inspect` validates complete replay and
history without resolving or loading live models. Session export/import and
snapshot export/import remain separate options. These exploratory sessions do
not satisfy the fixed-participant paired evaluation protocol.

## Experiment readers and trace jobs

The Experiments page uses `GET /api/experiment-catalog?q=...` for shared discovery
of teacher, learning, search, data and performance studies. It reads entries in
owning work items/reports under `QI_WORKSPACE` (default: checkout root). Detail,
owner and registered text-evidence routes live below `/api/experiment-catalog/{id}`.
These routes are read-only; `qi experiment record` appends validated owner revisions.
The [catalog contract](../src/qi/experiments/README.md#shared-catalog-and-recording)
owns fields, scope, revision rules and preview limits. Artifact availability is
separate from execution state and scientific conclusion.

For the Recorded search runs section, `GET /api/experiments` discovers runs under
`QI_EXPERIMENT_ROOTS` (a platform path-separated list; default
`artifacts/experiments`). Search runs have
a native reader; other formats are visibly unsupported. Invalid entries remain
isolated. Discovery skips source/dependency folders and symlinked directories.
Selected evidence is validated before derived data is returned. IDs resolve only
inside configured roots; referenced artifacts must stay inside their run.
Artifact folders supply data only; readers do not load executable plugins.

Report overview responses omit large unit histories and trace events. Separate
unit and paginated trace endpoints load those on demand. Native and standalone
HTML use the same React renderer and Python presentation contract. Optional
`narrative.md` is authored in an ordinary editor; rendering supports Markdown/GFM
without active HTML/MDX. JSON/Markdown evidence references stay inside the run.
The [experiment guide](../src/qi/experiments/README.md) owns exports and identities.

`POST /api/trace-jobs` accepts a selected run/unit digest/turn, event cap and
idempotency key. One child process runs at a time; its original decision config
and full history are fixed. Exact source/Python/package compatibility is checked
before launch and in the worker. `GET /api/trace-jobs` reports status; the cancel
endpoint terminates the owned worker. Browser navigation/closure does not cancel
an explicit trace job. Server shutdown terminates it; restart marks unfinished
metadata interrupted without resuming work.
An incompatible request never checks out historical code or reruns its benchmark.

`QI_TRACE_SECONDS` sets the finite server deadline (default 120, maximum 3600).
Recording defaults to 100000 events and accepts at most 1000000. Successful
parity-validated traces publish atomically under the run's traces directory.
Capacity-limited recordings retain their incomplete flag; killed or failed
computations publish nothing. Cancellation and success races resolve to one
terminal job state. Job metadata is bounded to 32 recent entries in
`QI_LAB_STATE` (default `artifacts/lab`) and kept separate from evidence. No queue,
experiment launcher, training launcher or background game execution is included.

## Generated game review

`/data` is the read-only collection workspace. `QI_COLLECTION_PATHS` explicitly
selects a platform path-separated list of SQLite files. Otherwise discovery checks
`artifacts/learning` under `QI_WORKSPACE`, including two directory levels, excluding
symlinks and execution/source directories. Invalid collections are isolated.
`src/qi/collection_view.py` owns the Python projections; HTTP only accepts discovered
collection IDs. Each response reads one SQLite snapshot with a finite query deadline,
without writer locks, recovery, schema changes or teacher execution.

The cohort filters cover logical run, policy, split, disposition, outcome, source,
review shortlist and sampling/length lenses. Counts follow those filters. Accepted
and duplicate-rejected attempts form the acceptance denominator; other failures,
interruptions and running attempts remain separate. Selected counts are occurrences,
not unique boards. Phase bars retain requested versus actual sampling totals for
accepted games with sampling evidence. Clicking a phase selects its shortfalls.
A generation ply-budget stop is unfinished; a referee ply-limit draw is a draw.
Continuation runs retain links and original game ownership, so inherited rows are
not counted again or combined into misleading planned totals.

The separately timestamped quality audit always covers the whole collection's
selected occurrences in accepted games. It reads stored learner-input identities,
counts within/across-split repetitions, provides bounded shared-input examples, and
counts successful analysis coverage by exact specification. Two distinct single-PV
node budgets means retained coverage, not label correctness. Thread settings and
other specification identities remain separate. The JSON audit export is descriptive
evidence, not an eligible training snapshot or exclusion manifest. Full collection
integrity, immutable training export and selection remain Training Data operations.

Select a game for referee-validated replay, actor/teacher move overlays, selected
position navigation and retained analysis inspection. Full raw analysis is loaded
and checked against its position/specification on demand. Score points show only
exact single-PV centipawn values converted to Red's perspective; bounds, mate and
missing scores remain explicit in the per-position comparison. Neither disagreement
nor generated outcomes establish player strength.

Keep/inspect/exclude reviews and notes are browser-owned suggestions. Explicit Save
stores one record per collection/game-attempt under `qi.collection-review.v1`, with
trajectory identity, current ply and timestamp. They do not write to the collection
or change training eligibility. Corrupt/unavailable browser storage blocks overwrite
and preserves the existing bytes. Review JSON and referee-snapshot exports are
separate formats. Reviews are local to this browser/origin; retain exports for a
portable copy. Filters, game and ply live in the URL. Refresh reads current evidence;
no background generation, auto-resume or curation-to-training promotion is provided.

## Generation learning walkthrough

`/learn/generation` teaches the path from actor policies through replay, board-based
phases, position sampling, teacher supervision, input-quality checks and frozen
dataset selection. The Learn navigation entry and links from Home, Data and
Reference make it discoverable. `?step=1` through `?step=7` supports direct links,
refresh and browser history; contextual terms use the shared bilingual glossary.

`src/qi/generation_lesson_example.json` retains a fixed teaching excerpt from
`overnight-batches-20260911`, game #6286, captured on 2026-09-11. It includes replay,
actor/sampling settings, selected single-PV score evidence, source identities and
separately identified historical batch counts. It is a teaching projection, not a
live collection, full raw-analysis archive or eligible training snapshot. Updating
it requires re-deriving the retained facts from the source evidence.

`GET /api/learn/generation` replays the excerpt through the referee and computes
phases through the Training Data classifier. The board is read-only. The sampling
exercise calls `GET /api/learn/generation/sampling` with bounded spacing and seed,
using the production sampler on that same fixed game. Practice results are labelled
separately from the recorded selection. Neither endpoint reads or writes a live
collection, starts an engine, generates games, nor launches training. The walkthrough
explains score bounds/mate omissions and distinguishes full-trajectory identity,
occurrence provenance and learner-input overlap. The generation policies remain
owned by the [generation guide](data-generation.md) and its Python implementation.
