import { useQuery } from "@tanstack/react-query";
import { read, type Schema } from "./api";
import { Button } from "./components/ui/button";
import "./benchmarks.css";

type Summary = Schema<"BenchmarkSummary">;
export type BenchmarkFilters = { run?: string; snapshot?: string };
export function parseBenchmarkFilters(
  search: Record<string, unknown>,
): BenchmarkFilters {
  const text = (value: unknown) =>
    typeof value === "string" && value.length > 0 && value.length <= 128
      ? value
      : undefined;
  return { run: text(search.run), snapshot: text(search.snapshot) };
}
const number = (value: number | null | undefined, digits = 0) =>
  value == null
    ? "—"
    : value.toLocaleString(undefined, { maximumFractionDigits: digits });

function Results({ data }: { data: Summary }) {
  const labels = data.entrants;
  const ratings = [...(data.fit?.ratings ?? [])].sort(
    (a, b) => (b.elo ?? -Infinity) - (a.elo ?? -Infinity),
  );
  return (
    <>
      {data.verification && (
        <p
          className={
            data.verification.status === "verified" ? "muted" : "card error"
          }
          role="status"
        >
          {data.verification.status === "verified"
            ? "Verified evidence"
            : "Unverified historical snapshot"}
          : {data.verification.reason}
        </p>
      )}
      <div className="benchmark-metrics" aria-label="Benchmark progress">
        <div className="card">
          <small>Games complete</small>
          <strong>
            {data.completed_games} / {data.planned_games}
          </strong>
        </div>
        <div className="card">
          <small>State</small>
          <strong>{data.status}</strong>
          <span>{data.running_games} running</span>
        </div>
        <div className="card">
          <small>Failed / interrupted attempts</small>
          <strong>
            {data.failed_attempts} / {data.interrupted_attempts}
          </strong>
        </div>
        <div className="card">
          <small>Reused games</small>
          <strong>{data.reused_games}</strong>
          <span>{data.pool_status}</span>
        </div>
      </div>
      {data.results_hidden ? (
        <p className="card" role="status">
          Locked-test results are hidden. Complete the planned games, then
          reveal the report through the CLI. Reveal retires this test pool.
        </p>
      ) : (
        <>
          <div className="page-heading">
            <div>
              <h2>Local Elo</h2>
              <p className="muted">
                {labels[data.anchor]} defines 1000.{" "}
                {data.status !== "complete" &&
                  "This run is unfinished; estimates are provisional."}
              </p>
            </div>
            <span className="badge">{data.fit?.method}</span>
          </div>
          <div className="benchmark-table">
            <table>
              <caption>Configured player ratings and uncertainty</caption>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Local Elo</th>
                  <th>95% interval</th>
                  <th>Games / families</th>
                </tr>
              </thead>
              <tbody>
                {ratings.map((row) => (
                  <tr key={row.entrant}>
                    <th scope="row">
                      {labels[row.entrant]}
                      <small>{row.interval_reason}</small>
                    </th>
                    <td>{number(row.elo)}</td>
                    <td>
                      {row.lower == null
                        ? "Unavailable"
                        : `${number(row.lower)} to ${number(row.upper)}`}
                    </td>
                    <td>
                      {row.games} / {row.families}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            {data.fit?.interval_kind}. Bootstrap fits:{" "}
            {data.fit?.bootstrap_successes} successful,{" "}
            {data.fit?.bootstrap_failures} unavailable.
          </p>
          {[false, true].map((diagnostic) => (
            <section key={String(diagnostic)}>
              <h2>
                {diagnostic ? "Standard-start checks" : "Matchup results"}
              </h2>
              <div className="benchmark-table">
                <table>
                  <caption>
                    {diagnostic
                      ? "Separate diagnostics, excluded from Elo"
                      : "W/D/L and score from the first player's perspective"}
                  </caption>
                  <thead>
                    <tr>
                      <th>Players</th>
                      <th>Pairs</th>
                      <th>W / D / L</th>
                      <th>Score</th>
                      <th>Endings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.matchups
                      ?.filter((m) => m.diagnostic === diagnostic)
                      .map((m) => (
                        <tr key={`${m.a}-${m.b}`}>
                          <th scope="row">
                            {labels[m.a]}
                            <small>vs {labels[m.b]}</small>
                          </th>
                          <td>
                            {m.completed_pairs} / {m.planned_pairs}
                          </td>
                          <td>
                            {m.wins} / {m.draws} / {m.losses}
                          </td>
                          <td>
                            {m.score_rate == null
                              ? "—"
                              : `${number(100 * m.score_rate, 1)}%`}
                          </td>
                          <td>
                            {Object.entries(m.termination_reasons ?? {})
                              .map(([reason, count]) => `${reason}: ${count}`)
                              .join(" · ") || "—"}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
          <h2>Observed resources</h2>
          <p className="muted">
            Complete rated pairs only, including reused measurements. Native
            nodes, qi visits and model calls retain different meanings.
          </p>
          <div className="benchmark-table">
            <table>
              <caption>Work and move latency by configured player</caption>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Moves</th>
                  <th>Mean move</th>
                  <th>qi visits</th>
                  <th>Engine nodes</th>
                  <th>Model calls</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.costs ?? {}).map(([id, cost]) => (
                  <tr key={id}>
                    <th scope="row">{labels[id]}</th>
                    <td>{number(cost.decisions)}</td>
                    <td>{number(cost.mean_move_ms, 2)} ms</td>
                    <td>{number(cost.qi_visits)}</td>
                    <td>
                      {cost.engine_decisions ? number(cost.engine_nodes) : "—"}
                      {!!cost.engine_nodes_unknown && (
                        <small>
                          {cost.engine_nodes_unknown} moves have unknown native
                          nodes
                        </small>
                      )}
                    </td>
                    <td>{number(cost.model_calls)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <details className="card">
        <summary>Interpretation and evidence</summary>
        <p>{data.heldout_evidence}</p>
        <ul>
          {data.notes?.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
        <small>
          Series {data.series_sha256}
          <br />
          Spec {data.spec_sha256}
          <br />
          Evidence {data.evidence_sha256}
          <br />
          {data.created_at}
        </small>
      </details>
    </>
  );
}

export function BenchmarksPage({
  filters,
  onFilters,
}: {
  filters: BenchmarkFilters;
  onFilters: (filters: BenchmarkFilters) => void;
}) {
  const snapshot = filters.snapshot ?? "";
  const catalog = useQuery({
    queryKey: ["benchmarks"],
    queryFn: ({ signal }) =>
      read<Schema<"BenchmarkCatalog">>("benchmarks", signal),
    refetchOnWindowFocus: false,
  });
  const id = filters.run || catalog.data?.entries?.[0]?.id || "";
  const report = useQuery({
    queryKey: ["benchmark", id],
    queryFn: ({ signal }) =>
      read<Schema<"BenchmarkReport">>(
        `benchmarks/${encodeURIComponent(id)}`,
        signal,
      ),
    enabled: !!id,
    retry: false,
    refetchOnWindowFocus: false,
    refetchInterval: (query) =>
      !snapshot &&
      query.state.data &&
      query.state.data.summary.status !== "complete"
        ? 15000
        : false,
  });
  const saved = useQuery({
    queryKey: ["benchmark-snapshot", id, snapshot],
    queryFn: ({ signal }) =>
      read<Summary>(
        `benchmarks/${encodeURIComponent(id)}/snapshots/${encodeURIComponent(snapshot)}`,
        signal,
      ),
    enabled: !!id && !!snapshot,
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const data = snapshot ? saved.data : report.data?.summary;
  return (
    <section className="benchmarks-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">PLAYER ITERATION</p>
          <h1>Benchmarks</h1>
          <p className="muted">
            Playing strength, matchup evidence, and the resources each player
            used.
          </p>
        </div>
        <Button
          onClick={() => {
            void catalog.refetch();
            void report.refetch();
            if (snapshot) void saved.refetch();
          }}
        >
          Refresh results
        </Button>
      </div>
      {catalog.isLoading && <p role="status">Finding local benchmarks…</p>}
      {catalog.error && <p role="alert">{catalog.error.message}</p>}
      {catalog.data?.issues?.map((issue) => (
        <p role="alert" key={issue}>
          {issue}
        </p>
      ))}
      {catalog.data && !catalog.data.entries?.length && (
        <article className="card">
          <h2>No benchmark runs yet</h2>
          <p>
            Run a reference benchmark with <code>qi bench run</code>. Saved runs
            in the configured benchmark directory appear here.
          </p>
          <p>
            Use <code>qi bench --help</code> for setup, preview, execution and
            recovery.
          </p>
        </article>
      )}
      {!!id && (
        <>
          <div className="benchmark-selectors">
            <label>
              Benchmark run
              <select
                aria-label="Benchmark run"
                value={id}
                onChange={(e) => {
                  onFilters({ run: e.target.value });
                }}
              >
                {catalog.data?.entries?.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.label} · {entry.mode} ·{" "}
                    {new Date(entry.created_at).toLocaleString()}
                  </option>
                ))}
              </select>
            </label>
            {!report.data?.summary.results_hidden && (
              <label>
                Rating snapshot
                <select
                  aria-label="Rating snapshot"
                  value={snapshot}
                  onChange={(e) =>
                    onFilters({
                      run: id,
                      snapshot: e.target.value || undefined,
                    })
                  }
                >
                  <option value="">Current evidence</option>
                  {report.data?.snapshots.map((sha) => (
                    <option key={sha} value={sha}>
                      Saved {sha.slice(0, 12)}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {(report.error || saved.error) && (
            <p role="alert">
              Evidence could not be validated:{" "}
              {(report.error || saved.error)?.message}
            </p>
          )}
          {(report.isLoading || (snapshot && saved.isLoading)) && (
            <p role="status">Validating recorded games…</p>
          )}
          {data && !(report.error || (snapshot && saved.error)) && (
            <Results data={data} />
          )}
          {report.data && (
            <details className="card">
              <summary>Player settings and opening source</summary>
              <p>{report.data.book_provenance}</p>
              <p>{report.data.book_selection}</p>
              <pre>{JSON.stringify(report.data.settings, null, 2)}</pre>
            </details>
          )}
        </>
      )}
    </section>
  );
}
