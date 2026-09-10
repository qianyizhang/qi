import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type {
  ReportData,
  UnitDetail,
  TracePage,
  TraceEvent,
  Choice,
  Schema,
} from "./api";
import { Board } from "./board";
import { ChoiceDetails } from "./choice-details";
import { Button } from "./components/ui/button";
import { GlossaryContext, ReferenceList, Term } from "./reference";
export type Filters = {
  player?: string;
  budget?: string;
  opening?: string;
  unit?: string;
  ply?: number;
  trace?: string;
};
export type TraceOptions = {
  parent: number | null;
  offset: number;
  view: "all" | "mcts-tree";
  show_work: boolean;
};
export type ReportSource = {
  key: string;
  unit: (id: string) => Promise<UnitDetail>;
  trace: (id: string, options: TraceOptions) => Promise<TracePage>;
  evidenceLink?: (href: string) => string;
  generate?: (
    unit: Schema<"UnitSummary">,
    turn: number,
    limit: number,
  ) => Promise<void>;
};
const fmt = (value: unknown) =>
  value == null
    ? "—"
    : typeof value === "number"
      ? Number.isInteger(value)
        ? String(value)
        : value.toFixed(2)
      : String(value);
function DataTable({ rows }: { rows: object[] }) {
  if (!rows.length)
    return <p className="muted">No completed samples for this filter.</p>;
  const keys = Object.keys(rows[0]);
  return (
    <div className="scroll" tabIndex={0}>
      <table>
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key}>
                <Term name={key}>{key.replaceAll("_", " ")}</Term>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {Object.values(row).map((value, cell) => (
                <td key={cell}>{fmt(value)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Bars({
  rows,
  metric,
  label,
}: {
  rows: Schema<"ProbeSummary">[];
  metric: "mean_ms" | "mean_nodes";
  label: string;
}) {
  const max = Math.max(1, ...rows.map((row) => row[metric]));
  return (
    <div className="card">
      <h3>{label}</h3>
      {rows.map((row) => (
        <div className="bar-row" key={`${row.player}-${row.budget}`}>
          <span>
            {row.player} · {row.budget}
          </span>
          <div>
            <span style={{ width: `${(100 * row[metric]) / max}%` }} />
          </div>
          <output>{fmt(row[metric])}</output>
        </div>
      ))}
    </div>
  );
}
function Timeline({
  unit,
  onSelect,
}: {
  unit: UnitDetail;
  onSelect: (ply: number) => void;
}) {
  const [metric, setMetric] = useState<"elapsed_ms" | "nodes" | "score">(
    "elapsed_ms",
  );
  const [side, setSide] = useState("red");
  const values = unit.turns.map((turn) =>
    metric === "score" && turn.side !== side ? null : turn.choice[metric],
  );
  const known = values.filter((value): value is number => value !== null);
  const lo = Math.min(0, ...known),
    hi = Math.max(1, ...known);
  return (
    <div>
      <div className="toolbar">
        <label>
          Chart
          <select
            aria-label="Chart"
            value={metric}
            onChange={(event) => setMetric(event.target.value as typeof metric)}
          >
            <option value="elapsed_ms">Decision time (ms)</option>
            <option value="nodes">Charged visits</option>
            <option value="score">Search score · one player</option>
          </select>
        </label>
        {metric === "score" && (
          <label>
            Score perspective
            <select
              aria-label="Score perspective"
              value={side}
              onChange={(event) => setSide(event.target.value)}
            >
              <option value="red">Red player's decisions</option>
              <option value="black">Black player's decisions</option>
            </select>
          </label>
        )}
      </div>
      <svg
        className="timeline"
        viewBox="0 0 560 170"
        aria-label={`${metric} timeline`}
        role="img"
      >
        <path d="M20 15V145H540" fill="none" stroke="currentColor" />
        {values.map((value, index) =>
          value === null ? null : (
            <g
              key={index}
              role="button"
              aria-label={`Inspect decision ${index + 1}`}
              tabIndex={0}
              onClick={() => onSelect(index + 1)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(index + 1);
                }
              }}
            >
              <circle
                cx={30 + (index * 500) / Math.max(1, values.length - 1)}
                cy={140 - (120 * (value - lo)) / (hi - lo)}
                r={5}
                fill={unit.turns[index].side === "red" ? "#a4382d" : "#426954"}
              />
              <title>
                {unit.turns[index].ply}: {fmt(value)}
              </title>
            </g>
          ),
        )}
      </svg>
      {metric === "score" && (
        <p className="muted">
          Only {side} decisions. Scores use that player's perspective; missing
          values stay unknown. Scores from different players need not share a
          scale.
        </p>
      )}
    </div>
  );
}
function Tree({
  source,
  trace,
  options,
  onOptions,
  onEvent,
}: {
  source: ReportSource;
  trace: string;
  options: TraceOptions;
  onOptions: (options: TraceOptions) => void;
  onEvent: (event: TraceEvent) => void;
}) {
  const [ancestors, setAncestors] = useState<(number | null)[]>([]);
  const query = useQuery({
    queryKey: ["report-tree", source.key, trace, options],
    queryFn: () => source.trace(trace, options),
    retry: false,
  });
  return (
    <div className="card tree">
      <div className="toolbar">
        <Button
          size="sm"
          onClick={() => {
            const parent = ancestors.at(-1) ?? null;
            setAncestors(ancestors.slice(0, -1));
            onOptions({ ...options, parent, offset: 0 });
          }}
          disabled={options.parent === null}
        >
          Parent
        </Button>
        <span>
          {options.parent === null
            ? "Root events"
            : `Children of event ${options.parent}`}
        </span>
      </div>
      {query.error && <p role="alert">{query.error.message}</p>}
      {query.isLoading && <p>Loading events…</p>}
      {query.data?.events.map((event) => (
        <div className="tree-row" key={event.id}>
          <Button variant="ghost" size="sm" onClick={() => onEvent(event)}>
            #{event.id} {event.kind}
            {event.move ? ` · ${event.move}` : ""}
            {event.value == null
              ? ""
              : ` · ${fmt(event.value)} (${event.value_perspective ?? "unknown perspective"}, ${event.bound ?? "bound unknown"})`}
          </Button>
          <Button
            size="sm"
            aria-label={`Expand event ${event.id}`}
            onClick={() => {
              setAncestors([...ancestors, options.parent]);
              onEvent(event);
              onOptions({ ...options, parent: event.id, offset: 0 });
            }}
          >
            →
          </Button>
        </div>
      ))}
      {query.data?.total === 0 && <p>No recorded children in this view.</p>}
      <div className="toolbar">
        <Button
          size="sm"
          disabled={options.offset === 0}
          onClick={() =>
            onOptions({ ...options, offset: Math.max(0, options.offset - 100) })
          }
        >
          Previous events
        </Button>
        <span>
          {options.offset + (query.data?.events.length ? 1 : 0)}–
          {options.offset + (query.data?.events.length ?? 0)} /{" "}
          {query.data?.total ?? "…"}
        </span>
        <Button
          size="sm"
          disabled={!query.data || options.offset + 100 >= query.data.total}
          onClick={() =>
            onOptions({ ...options, offset: options.offset + 100 })
          }
        >
          More events
        </Button>
      </div>
    </div>
  );
}
export function ReportView({
  data,
  source,
  filters,
  onFilters,
}: {
  data: ReportData;
  source: ReportSource;
  filters: Filters;
  onFilters: (filters: Filters) => void;
}) {
  const [treeOptions, setTreeOptions] = useState<TraceOptions>({
    parent: null,
    offset: 0,
    view: "all",
    show_work: false,
  });
  const [event, setEvent] = useState<TraceEvent | null>(null);
  const [traceLimit, setTraceLimit] = useState(100000);
  const [traceMessage, setTraceMessage] = useState("");
  const [starting, setStarting] = useState(false);
  const summary = filters.opening
    ? (data.by_position[filters.opening] ?? data.summary)
    : data.summary;
  const probes = summary.probes.filter(
    (row) =>
      (!filters.player || row.player === filters.player) &&
      (!filters.budget || row.budget === Number(filters.budget)),
  );
  const matches = summary.matches.filter(
    (row) =>
      (!filters.player ||
        row.a === filters.player ||
        row.b === filters.player) &&
      (!filters.budget || row.budget === Number(filters.budget)),
  );
  const visibleUnits = data.units.filter(
    (unit) =>
      (!filters.opening || unit.job.opening === filters.opening) &&
      (!filters.budget || unit.job.a.nodes === Number(filters.budget)) &&
      (!filters.player ||
        unit.job.a.kind === filters.player ||
        unit.job.b?.kind === filters.player),
  );
  const unitId =
    visibleUnits.find((unit) => unit.job.id === filters.unit)?.job.id ??
    visibleUnits[0]?.job.id;
  const detail = useQuery({
    queryKey: ["report-unit", source.key, unitId],
    queryFn: () => source.unit(unitId!),
    enabled: !!unitId,
    retry: false,
  });
  const unit = detail.data;
  const ply = Math.max(
    0,
    Math.min(filters.ply ?? 0, (unit?.frames.length ?? 1) - 1),
  );
  const frame = unit?.frames[ply];
  const turn = unit?.turns[ply > 0 ? ply - 1 : 0];
  const traceId =
    data.traces.find((trace) => trace.id === filters.trace)?.id ??
    data.traces[0]?.id;
  const trace = data.traces.find((trace) => trace.id === traceId);
  useEffect(() => {
    setTreeOptions((options) => ({ ...options, parent: null, offset: 0 }));
    setEvent(null);
  }, [traceId]);
  const patch = (values: Partial<Filters>) =>
    onFilters({ ...filters, ...values });
  return (
    <GlossaryContext value={data.glossary}>
      <section className="report">
        <p className="eyebrow">SEARCH EVIDENCE</p>
        <h1>{data.plan.name}</h1>
        <p className="lead">{data.plan.question}</p>
        <div className="toolbar">
          <span className="badge">{data.status}</span>
          <span>
            {data.completed}/{data.planned} completed units
          </span>
        </div>
        {data.warnings.map((warning) => (
          <p className="error" key={warning}>
            {warning}
          </p>
        ))}
        <details className="card">
          <summary>New here? A guide to reading this report</summary>
          <ol>
            <li>
              Choose a visit budget and position to compare matching samples.
            </li>
            <li>
              Read decision time and charged visits together. Equal visits are
              not equal compute.
            </li>
            <li>
              Paired-color outcomes exclude missing partners; partial runs have
              missing evidence.
            </li>
            <li>
              Inspect a decision, then explore its recorded branches. Check
              score perspective and bound.
            </li>
          </ol>
          <p>Tap an underlined term for its English / 中文 definition.</p>
        </details>
        {data.narrative && (
          <article className="card narrative">
            <h2>Authored narrative</h2>
            <Markdown
              remarkPlugins={[remarkGfm]}
              skipHtml
              components={{
                a: ({ href, children }) => (
                  <a
                    href={
                      href && !/^(https?:|mailto:|#)/i.test(href)
                        ? (source.evidenceLink?.(href) ?? href)
                        : href
                    }
                    rel="noreferrer"
                  >
                    {children}
                  </a>
                ),
                img: ({ alt }) => (
                  <span>
                    [Image: {alt}; images are not included in narrative reports]
                  </span>
                ),
              }}
            >
              {data.narrative}
            </Markdown>
          </article>
        )}
        <section>
          <h2>Compare evidence</h2>
          <p className="muted">
            Fixed-position <Term name="probe">probes</Term> isolate decisions.
            Small exploratory samples do not establish general playing strength.
          </p>
          <div className="toolbar">
            <label>
              Visit budget
              <select
                aria-label="Visit budget"
                value={filters.budget ?? ""}
                onChange={(e) => patch({ budget: e.target.value })}
              >
                <option value="">All budgets</option>
                {data.plan.budgets.map((budget) => (
                  <option key={budget}>{budget}</option>
                ))}
              </select>
            </label>
            <label>
              Player
              <select
                aria-label="Player"
                value={filters.player ?? ""}
                onChange={(e) => patch({ player: e.target.value })}
              >
                <option value="">All players</option>
                {data.plan.players.map((player) => (
                  <option key={player}>{player}</option>
                ))}
              </select>
            </label>
            <label>
              Position
              <select
                aria-label="Position"
                value={filters.opening ?? ""}
                onChange={(e) => patch({ opening: e.target.value })}
              >
                <option value="">All positions</option>
                {data.plan.corpus.openings.map((opening) => (
                  <option key={opening.id} value={opening.id}>
                    {opening.id}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="two-columns">
            <Bars
              rows={probes}
              metric="mean_ms"
              label="Mean decision time (ms)"
            />
            <Bars
              rows={probes}
              metric="mean_nodes"
              label="Search work (charged visits)"
            />
          </div>
          <DataTable rows={probes} />
          <h3>Paired-color outcomes</h3>
          <p className="muted">
            {summary.unpaired_completed_games} completed games lack their color
            partner and are excluded. Unknown scores appear as —.
          </p>
          <DataTable rows={matches} />
        </section>
        <section>
          <h2>Inspect a position or game</h2>
          <label>
            Recorded unit
            <select
              aria-label="Recorded unit"
              value={unitId ?? ""}
              onChange={(e) => patch({ unit: e.target.value, ply: 0 })}
            >
              {visibleUnits.map((unit) => (
                <option key={unit.job.id} value={unit.job.id}>
                  {unit.job.id} · {unit.job.opening} · {unit.job.a.kind} ·{" "}
                  {unit.status}
                </option>
              ))}
            </select>
          </label>
          {detail.error && <p role="alert">{detail.error.message}</p>}
          {unit && (
            <div className="inspection">
              <div>
                {frame && (
                  <Board
                    view={{
                      board: frame.board,
                      legal_moves: [],
                      snapshot: {
                        ...unit.snapshot,
                        moves: unit.snapshot.moves!.slice(
                          0,
                          (unit.turns[0]?.ply ?? 1) - 1 + ply,
                        ),
                      },
                    }}
                    selected={null}
                    flipped={false}
                    disabled
                    keyboardDisabled
                    onChoose={() => {}}
                  />
                )}
                <div className="toolbar">
                  <Button
                    aria-label="Previous report position"
                    disabled={ply === 0}
                    onClick={() => patch({ ply: ply - 1 })}
                  >
                    ←
                  </Button>
                  <input
                    aria-label="Report replay position"
                    type="range"
                    min={0}
                    max={unit.frames.length - 1}
                    value={ply}
                    onChange={(e) => patch({ ply: Number(e.target.value) })}
                  />
                  <Button
                    aria-label="Next report position"
                    disabled={ply === unit.frames.length - 1}
                    onClick={() => patch({ ply: ply + 1 })}
                  >
                    →
                  </Button>
                </div>
                <p>
                  {frame?.side} to move · Recorded position {ply}/
                  {unit.frames.length - 1}
                </p>
              </div>
              <div>
                <Timeline unit={unit} onSelect={(ply) => patch({ ply })} />
                {turn && <ChoiceDetails choice={turn.choice as Choice} />}
                <details>
                  <summary>Raw decision evidence</summary>
                  <pre>{JSON.stringify(turn ?? unit, null, 2)}</pre>
                </details>
                <h3>Generate a trace</h3>
                {source.generate ? (
                  <>
                    <p className="muted">
                      {data.trace_unavailable_reason ??
                        "Reproduce this saved decision in a bounded background job. Its original settings and history are fixed."}
                    </p>
                    <label>
                      Event limit
                      <input
                        type="number"
                        min={1}
                        max={1000000}
                        value={traceLimit}
                        onChange={(e) => setTraceLimit(e.target.valueAsNumber)}
                      />
                    </label>
                    <Button
                      disabled={
                        !!data.trace_unavailable_reason ||
                        !turn ||
                        starting ||
                        !(
                          Number.isInteger(traceLimit) &&
                          traceLimit >= 1 &&
                          traceLimit <= 1000000
                        )
                      }
                      onClick={async () => {
                        setStarting(true);
                        try {
                          await source.generate!(
                            data.units.find((row) => row.job.id === unitId)!,
                            ply > 0 ? ply - 1 : 0,
                            traceLimit,
                          );
                          setTraceMessage(
                            "Trace requested. Status is shown above and on Home.",
                          );
                        } catch (error) {
                          setTraceMessage(String(error));
                        } finally {
                          setStarting(false);
                        }
                      }}
                    >
                      Generate trace
                    </Button>
                    <p role="status">{traceMessage}</p>
                  </>
                ) : (
                  <p className="muted">
                    Open this run in the app to generate a trace, or use qi
                    experiment inspect with this unit and decision index{" "}
                    {ply > 0 ? ply - 1 : 0}. Offline reports display saved
                    traces.
                  </p>
                )}
              </div>
            </div>
          )}
        </section>
        <section>
          <h2>Explore searched branches</h2>
          <p className="muted">
            Iterative-deepening passes, simulation work and retained MCTS trees
            keep their own labels. Unsearched moves have no invented scores.
          </p>
          {trace ? (
            <>
              <div className="toolbar">
                <label>
                  Trace
                  <select
                    aria-label="Trace"
                    value={traceId}
                    onChange={(e) => {
                      patch({ trace: e.target.value });
                      setTreeOptions({
                        ...treeOptions,
                        parent: null,
                        offset: 0,
                      });
                      setEvent(null);
                    }}
                  >
                    {data.traces.map((trace) => (
                      <option key={trace.id} value={trace.id}>
                        {trace.id} · {trace.unit_id} decision {trace.turn_index}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  View
                  <select
                    aria-label="View"
                    value={treeOptions.view}
                    onChange={(e) => {
                      setEvent(null);
                      setTreeOptions({
                        ...treeOptions,
                        parent: null,
                        offset: 0,
                        view: e.target.value as TraceOptions["view"],
                      });
                    }}
                  >
                    <option value="all">All explored work</option>
                    <option value="mcts-tree">Final MCTS tree</option>
                  </select>
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={treeOptions.show_work}
                    onChange={(e) =>
                      setTreeOptions({
                        ...treeOptions,
                        offset: 0,
                        show_work: e.target.checked,
                      })
                    }
                  />
                  Show individual work charges
                </label>
              </div>
              <p>
                {trace.complete
                  ? "Complete recording"
                  : "Incomplete recording (capacity limit)"}{" "}
                · {trace.events} events · {trace.dropped_events} dropped ·
                Decision parity verified
              </p>
              <div className="inspection">
                <Tree
                  key={`${traceId}-${treeOptions.view}`}
                  source={source}
                  trace={trace.id}
                  options={treeOptions}
                  onOptions={setTreeOptions}
                  onEvent={setEvent}
                />
                <div>
                  {event?.board && (
                    <Board
                      view={{
                        board: event.board,
                        legal_moves: [],
                        snapshot: { moves: event.move ? [event.move] : [] },
                      }}
                      selected={null}
                      flipped={false}
                      disabled
                      keyboardDisabled
                      onChoose={() => {}}
                    />
                  )}
                  <pre>
                    {event
                      ? JSON.stringify(event, null, 2)
                      : "Select an event to inspect its board and details."}
                  </pre>
                </div>
              </div>
            </>
          ) : (
            <p>No verified traces saved for this run.</p>
          )}
        </section>
        <section>
          <h2>Provenance & limits</h2>
          <p>
            {data.validation}. File hashes identify content, not authorship.
          </p>
          <details>
            <summary>Plan and environment</summary>
            <pre>
              {JSON.stringify(
                {
                  plan: data.plan,
                  provenance: data.provenance,
                  evidence_sha256: data.evidence_sha256,
                  presentation_sha256: data.presentation_sha256,
                  narrative_sha256: data.narrative_sha256,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </section>
        <details>
          <summary>Beginner glossary · English / 中文</summary>
          <ReferenceList glossary={data.glossary} />
        </details>
      </section>
    </GlossaryContext>
  );
}
