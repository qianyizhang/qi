import { useQuery } from "@tanstack/react-query";
import { ArrowDownToLine, RefreshCw } from "lucide-react";
import { read, download, type Schema } from "./api";
import { Button } from "./components/ui/button";
import type { DataFilters } from "./data-review";
import { number, percent, title, type Stats } from "./data-format";
function Bars({
  values,
  denominator,
  onSelect,
}: {
  values: Record<string, number>;
  denominator: number;
  onSelect?: (key: string) => void;
}) {
  return (
    <div className="data-bars">
      {Object.entries(values).map(([key, value]) => (
        <button
          key={key}
          type="button"
          disabled={!onSelect}
          onClick={() => onSelect?.(key)}
          className="data-bar"
        >
          <span>{title(key)}</span>
          <span className="data-bar-track">
            <i
              style={{
                width: `${denominator ? (value / denominator) * 100 : 0}%`,
              }}
            />
          </span>
          <span>
            {number(value)} <small>{percent(value, denominator)}</small>
          </span>
        </button>
      ))}
    </div>
  );
}
export function Overview({
  stats,
  set,
}: {
  stats: Stats;
  set: (v: Partial<DataFilters>) => void;
}) {
  const disposed = stats.accepted + stats.rejected;
  return (
    <>
      <div className="data-metrics" aria-label="Filtered cohort statistics">
        <article>
          <span>Accepted games</span>
          <strong>{number(stats.accepted)}</strong>
          <small>
            {percent(stats.accepted, disposed)} of {number(disposed)} accepted +
            rejected
          </small>
        </article>
        <article>
          <span>Selected positions</span>
          <strong>{number(stats.selected)}</strong>
          <small>Occurrences in accepted games · not unique boards</small>
        </article>
        <article>
          <span>Mean game length</span>
          <strong>
            {stats.mean_plies?.toFixed(1) ?? "—"}
            <em> plies</em>
          </strong>
          <small>New half-moves per accepted game</small>
        </article>
        <article>
          <span>Sampling shortfalls</span>
          <strong>{number(stats.shortfall_games)}</strong>
          <small>
            of {number(stats.sampling_games)} accepted games with sampling
            evidence
          </small>
        </article>
      </div>
      <div className="data-charts">
        <article className="card">
          <p className="eyebrow">COMPOSITION</p>
          <h2>How games were made</h2>
          <Bars
            values={stats.policies}
            denominator={stats.accepted}
            onSelect={(policy) => set({ policy })}
          />
          <div className="data-split">
            <Bars
              values={stats.splits}
              denominator={stats.accepted}
              onSelect={(split) => set({ split })}
            />
          </div>
          <p className="muted">
            Accepted games. Click a row to narrow the cohort.
          </p>
        </article>
        <article className="card">
          <p className="eyebrow">COVERAGE</p>
          <h2>Positions by game phase</h2>
          <div className="data-bars">
            {["opening", "middlegame", "endgame"].map((phase) => {
              const actual = stats.actual[phase] ?? 0,
                requested = stats.requested[phase] ?? 0;
              return (
                <button
                  className="data-bar phase-bar"
                  key={phase}
                  onClick={() =>
                    set({ lens: "shortfall", phase, sort: "shortfall" })
                  }
                >
                  <span>{phase}</span>
                  <span className="data-bar-track">
                    <i
                      style={{
                        width: `${requested ? Math.min(100, (actual / requested) * 100) : 0}%`,
                      }}
                    />
                  </span>
                  <span>
                    {number(actual)}
                    <small> / {number(requested)}</small>
                  </span>
                </button>
              );
            })}
          </div>
          <p className="muted">
            Retained / requested across accepted games. Phase is classified from
            the board. Click to inspect shortfall games.
          </p>
        </article>
        <article className="card">
          <p className="eyebrow">REFEREE OUTCOMES</p>
          <h2>How games ended</h2>
          <Bars
            values={stats.outcomes}
            denominator={stats.accepted}
            onSelect={(outcome) => set({ outcome })}
          />
          <p className="muted">
            Exploratory generation outcomes; these are not player-strength
            estimates.
          </p>
        </article>
      </div>
      <div className="data-insights">
        <span>
          <b>{number(stats.rejected)}</b> duplicate-rejected attempts
        </span>
        <span>
          <b>{number(stats.other)}</b> running, interrupted or other failed
          attempts
        </span>
        <span>
          <b>{number(stats.accepted - stats.unique_trajectories)}</b> repeated
          accepted full trajectories
        </span>
        <span>
          Shared-board overlap and training eligibility require a separate
          selection audit.
        </span>
      </div>
    </>
  );
}

export function QualityAudit({
  collection,
  openGame,
}: {
  collection: string;
  openGame: (game: number, ply: number) => void;
}) {
  const query = useQuery({
    queryKey: ["collection-quality", collection],
    queryFn: ({ signal }) =>
      read<Schema<"CollectionQuality">>(
        `collections/${collection}/quality`,
        signal,
      ),
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });
  const q = query.data;
  return (
    <article className="card quality-audit">
      <div className="quality-heading">
        <div>
          <p className="eyebrow">COLLECTION-WIDE QUALITY AUDIT</p>
          <h2>Can these inputs stay independent?</h2>
        </div>
        <Button
          size="sm"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw size={14} /> Recheck quality
        </Button>
      </div>
      <p className="muted">
        All selected occurrences from accepted games in this collection, across
        both splits. This audit stays collection-wide when the game filters
        change.
      </p>
      {query.isLoading && (
        <p role="status">
          Checking learner-input overlap and retained analysis coverage…
        </p>
      )}
      {query.error && <p role="alert">{query.error.message}</p>}
      {q && (
        <>
          <div className="quality-cards">
            <div>
              <strong>{number(q.unique_inputs)}</strong>
              <span>unique learner inputs</span>
              <small>
                of {number(q.selected_occurrences)} selected occurrences;{" "}
                {number(q.selected_occurrences - q.unique_inputs)} repeats
              </small>
            </div>
            <div className={q.cross_split_inputs ? "quality-attention" : ""}>
              <strong>{number(q.cross_split_inputs)}</strong>
              <span>inputs appear in both splits</span>
              <small>
                {number(q.affected_train)} train +{" "}
                {number(q.affected_validation)} validation occurrences affected
              </small>
            </div>
            <div>
              <strong>
                {percent(
                  q.single_pv_budget_coverage["2"] ?? 0,
                  q.selected_occurrences,
                )}
              </strong>
              <span>have 2+ single-PV node budgets</span>
              <small>
                {number(q.single_pv_budget_coverage["1"] ?? 0)} have one ·{" "}
                {number(q.single_pv_budget_coverage["0"] ?? 0)} have none
              </small>
            </div>
          </div>
          <p className={q.cross_split_inputs ? "quality-finding" : "muted"}>
            {q.cross_split_inputs
              ? "Shared learner inputs are present across train and validation. Review the examples and resolve exclusions before freezing a training dataset."
              : "No cross-split learner-input overlap found among these selected occurrences."}{" "}
            Full-trajectory rejection alone does not check intermediate learner
            inputs.
          </p>
          {q.overlap_examples.length > 0 && (
            <details>
              <summary>
                Inspect shared-input examples ({q.overlap_examples.length} of{" "}
                {number(q.cross_split_inputs)} inputs)
              </summary>
              <div className="scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Learner input</th>
                      <th>Train occurrence</th>
                      <th>Validation occurrence</th>
                      <th>Train / validation occurrences</th>
                    </tr>
                  </thead>
                  <tbody>
                    {q.overlap_examples.map((e) => (
                      <tr key={e.input_hash}>
                        <td>
                          <code title={e.input_hash}>
                            {e.input_hash.slice(0, 12)}…
                          </code>
                        </td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => openGame(e.train_game, e.train_ply)}
                          >
                            Game #{e.train_game} · ply {e.train_ply}
                          </button>
                        </td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() =>
                              openGame(e.validation_game, e.validation_ply)
                            }
                          >
                            Game #{e.validation_game} · ply {e.validation_ply}
                          </button>
                        </td>
                        <td>
                          {e.train_occurrences} / {e.validation_occurrences}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted">
                Examples rank by affected occurrences. One representative game
                per split is shown; this is not an exclusion manifest.
              </p>
            </details>
          )}
          <details>
            <summary>Analysis coverage by specification</summary>
            <p className="muted">
              Counts include selected occurrences with at least one successful
              analysis for that exact specification. Settings such as threads
              remain separate. Two node budgets do not establish label
              correctness or teacher strength.
            </p>
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Requested nodes</th>
                    <th>Depth limit</th>
                    <th>Threads / MultiPV</th>
                    <th>Occurrences</th>
                    <th>Spec identity</th>
                  </tr>
                </thead>
                <tbody>
                  {q.specs.map((s) => (
                    <tr key={s.identity}>
                      <td>{number(s.nodes)}</td>
                      <td>{s.depth ?? "none"}</td>
                      <td>
                        {s.threads} / {s.multipv}
                      </td>
                      <td>{number(s.occurrences)}</td>
                      <td>
                        <code
                          title={`Engine ${s.engine}; network ${s.network}`}
                        >
                          {s.identity.slice(0, 12)}…
                        </code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <div className="quality-footer">
            <span>
              Observed {new Date(q.as_of * 1000).toLocaleString()} · input
              identity from the collection
            </span>
            <Button
              size="sm"
              onClick={() =>
                download(`qi-quality-${collection}.json`, { collection, ...q })
              }
            >
              <ArrowDownToLine size={14} /> Export quality audit
            </Button>
          </div>
        </>
      )}
    </article>
  );
}
