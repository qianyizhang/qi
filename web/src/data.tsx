import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, RefreshCw, Search } from "lucide-react";
import { read, download, type Schema } from "./api";
import { Button } from "./components/ui/button";
import { readReviews, type DataFilters } from "./data-review";
import { number, title, outcomeName } from "./data-format";
import { Overview, QualityAudit } from "./data-overview";
import { GameInspector } from "./data-inspector";
import "./data.css";
export function DataPage({
  filters,
  onFilters,
}: {
  filters: DataFilters;
  onFilters: (v: DataFilters) => void;
}) {
  const client = useQueryClient();
  const catalog = useQuery({
    queryKey: ["collections"],
    queryFn: ({ signal }) =>
      read<Schema<"CollectionCatalog">>("collections", signal),
  });
  const collection =
    filters.collection || catalog.data?.collections[0]?.id || "";
  const [revision, setRevision] = useState(0),
    [search, setSearch] = useState(filters.q ?? "");
  useEffect(() => setSearch(filters.q ?? ""), [filters.q]);
  useEffect(() => {
    const change = () => setRevision((v) => v + 1);
    window.addEventListener("storage", change);
    return () => window.removeEventListener("storage", change);
  }, []);
  const stored = useMemo(() => readReviews(collection), [collection, revision]);
  const set = (v: Partial<DataFilters>) =>
    onFilters({ ...filters, collection, offset: 0, ...v });
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters))
    if (
      value !== undefined &&
      !["collection", "game", "ply", "review"].includes(key)
    )
      params.set(key, String(value));
  if (filters.review)
    params.set(
      "attempts",
      stored.reviews
        .filter((r) => filters.review === "all" || r.status === filters.review)
        .map((r) => r.attempt)
        .join(",") || "no-reviews",
    );
  const query = useQuery({
    queryKey: ["collection-page", collection, params.toString()],
    queryFn: ({ signal }) =>
      read<Schema<"CollectionPage">>(
        `collections/${collection}?${params}`,
        signal,
      ),
    enabled: !!collection,
  });
  const data = query.data;
  const saved = stored.reviews.find((r) => r.game_id === filters.game);
  const refresh = () =>
    void Promise.all([
      catalog.refetch(),
      client.invalidateQueries({ queryKey: ["collection-page"] }),
      client.invalidateQueries({ queryKey: ["collection-game"] }),
      client.invalidateQueries({ queryKey: ["collection-quality"] }),
      client.invalidateQueries({ queryKey: ["collection-position"] }),
    ]);
  const exportReviews = () =>
    download(`qi-review-${collection}.json`, {
      format: "qi-game-review",
      version: 1,
      exported_at: new Date().toISOString(),
      collection: data?.collection,
      observed_at: data?.as_of,
      filters,
      reviews: stored.reviews,
      meaning:
        "Human review suggestions only; not a training dataset or eligibility manifest.",
    });
  return (
    <section className="data-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">GENERATED GAME COLLECTIONS</p>
          <h1>From games to understanding.</h1>
          <p className="muted">
            Explore the batch, inspect the evidence, and save the examples worth
            a closer look.
          </p>
        </div>
        <Button onClick={refresh} disabled={query.isFetching}>
          <RefreshCw size={15} /> Refresh
        </Button>
      </div>
      {catalog.error && <p role="alert">{catalog.error.message}</p>}
      {catalog.isLoading && <p role="status">Finding generated collections…</p>}
      {catalog.data?.issues.map((issue) => (
        <p className="error" key={issue}>
          {issue}
        </p>
      ))}
      {catalog.data?.collections.length === 0 && (
        <div className="card">
          <h2>No generated collections found</h2>
          <p>Collections appear here after games are generated.</p>
          <details>
            <summary>Local source configuration</summary>
            <p>
              Discovery looks for SQLite collections under artifacts/learning.
              Set QI_COLLECTION_PATHS on the server to a path-separated list of
              collection files.
            </p>
          </details>
        </div>
      )}
      {collection && (
        <>
          <div className="data-source">
            <label>
              Collection
              <select
                value={collection}
                onChange={(e) => onFilters({ collection: e.target.value })}
              >
                {catalog.data?.collections.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} · {(c.bytes / 1e9).toFixed(2)} GB
                  </option>
                ))}
              </select>
            </label>
            <div>
              {data && (
                <>
                  <b>{number(data.overall.attempts)} recorded attempts</b>
                  <small>
                    Observed {new Date(data.as_of * 1000).toLocaleString()} ·
                    refresh to read new games
                  </small>
                </>
              )}
            </div>
            <Button
              onClick={exportReviews}
              disabled={!stored.reviews.length || !!stored.error}
            >
              <ArrowDownToLine size={15} /> Export reviews (
              {stored.reviews.length})
            </Button>
          </div>
          {stored.error && (
            <p role="alert" className="error">
              {stored.error}
            </p>
          )}
          <div className="data-filterbar">
            <label>
              Batch / logical run
              <select
                aria-label="Batch / logical run"
                value={filters.run ?? 0}
                onChange={(e) =>
                  set({ run: Number(e.target.value) || undefined })
                }
              >
                <option value={0}>All runs</option>
                {data?.runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} · run {r.id} · {r.status}
                    {r.continued_from ? ` · continues ${r.continued_from}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Policy
              <select
                value={filters.policy ?? ""}
                onChange={(e) => set({ policy: e.target.value || undefined })}
              >
                <option value="">All policies</option>
                {Object.keys(
                  data?.overall.policies ?? {
                    plausible: 0,
                    intervention: 0,
                    random: 0,
                  },
                ).map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Split
              <select
                value={filters.split ?? ""}
                onChange={(e) => set({ split: e.target.value || undefined })}
              >
                <option value="">Both splits</option>
                <option>train</option>
                <option>validation</option>
              </select>
            </label>
            <label>
              Disposition
              <select
                value={filters.disposition ?? ""}
                onChange={(e) =>
                  set({ disposition: e.target.value || undefined })
                }
              >
                <option value="">All attempts</option>
                {[
                  "accepted",
                  "rejected",
                  "running",
                  "interrupted",
                  "failed",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Outcome
              <select
                value={filters.outcome ?? ""}
                onChange={(e) => set({ outcome: e.target.value || undefined })}
              >
                <option value="">All outcomes</option>
                <option value="red">Red win</option>
                <option value="black">Black win</option>
                <option value="draw">All referee draws</option>
                {Object.keys(data?.overall.outcomes ?? {})
                  .filter((v) => v.startsWith("draw ·"))
                  .map((v) => (
                    <option key={v} value={v}>
                      {title(v)}
                    </option>
                  ))}
                <option value="unfinished">Unfinished</option>
              </select>
            </label>
            <label>
              Review shortlist
              <select
                value={filters.review ?? ""}
                onChange={(e) =>
                  set({
                    review:
                      (e.target.value as DataFilters["review"]) || undefined,
                  })
                }
              >
                <option value="">All games</option>
                <option value="all">All reviewed</option>
                <option value="keep">Keep examples</option>
                <option value="inspect">Inspect later</option>
                <option value="exclude">Exclude candidates</option>
              </select>
            </label>
          </div>
          <div className="data-lenses" aria-label="Exploration lenses">
            {(
              [
                { lens: "all", name: "All evidence" },
                { lens: "shortfall", name: "Sampling gaps" },
                { lens: "long", name: "Long games · 250+ plies" },
              ] as const
            ).map((v) => (
              <button
                key={v.lens}
                aria-pressed={(filters.lens ?? "all") === v.lens}
                onClick={() => set({ lens: v.lens, phase: undefined })}
              >
                {v.name}
              </button>
            ))}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onFilters({ collection })}
            >
              Reset filters
            </Button>
            {filters.phase && (
              <button onClick={() => set({ phase: undefined })}>
                Phase: {filters.phase} ×
              </button>
            )}
            <span>Metrics follow all filters</span>
          </div>
          {query.error && (
            <p className="error" role="alert">
              {query.error.message}
            </p>
          )}
          {query.isLoading && (
            <div className="card" role="status">
              Reading collection snapshot…
            </div>
          )}
          {data && (
            <>
              <Overview stats={data.filtered} set={set} />
              <QualityAudit
                collection={collection}
                openGame={(game, ply) => set({ game, ply })}
              />
              <div
                className={`data-workbench ${filters.game ? "with-inspector" : ""}`}
              >
                <div className="data-game-list">
                  <div className="data-list-heading">
                    <div>
                      <h2>Review the games</h2>
                      <p className="muted">
                        {number(data.total)} matching attempts · ordered
                        independently of generation
                      </p>
                    </div>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        set({ q: search || undefined });
                      }}
                      className="game-search"
                    >
                      <label className="sr-only" htmlFor="game-search">
                        Search games
                      </label>
                      <input
                        id="game-search"
                        placeholder="Game ID or source…"
                        maxLength={100}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                      <Button
                        size="icon"
                        aria-label="Search games"
                        type="submit"
                      >
                        <Search size={16} />
                      </Button>
                    </form>
                  </div>
                  <div className="data-list-tools">
                    <label>
                      Order
                      <select
                        value={filters.sort ?? "newest"}
                        onChange={(e) =>
                          set({ sort: e.target.value as DataFilters["sort"] })
                        }
                      >
                        <option value="newest">Newest first</option>
                        <option value="longest">Longest first</option>
                        <option value="shortfall">Largest shortfall</option>
                      </select>
                    </label>
                    <span className="muted">
                      Select a game to replay and review
                    </span>
                  </div>
                  {data.games.length === 0 ? (
                    <div className="card">
                      <h3>No games in this view</h3>
                      <p>
                        Try another filter or save a review to build your
                        shortlist.
                      </p>
                      <Button onClick={() => onFilters({ collection })}>
                        Show all games
                      </Button>
                    </div>
                  ) : (
                    <div className="scroll games-table">
                      <table>
                        <thead>
                          <tr>
                            <th>Game / source</th>
                            <th>Disposition / outcome</th>
                            <th>Policy / split</th>
                            <th>Plies</th>
                            <th>Selected / gap</th>
                            <th>Review</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.games.map((g) => {
                            const review = stored.reviews.find(
                              (r) =>
                                r.attempt === g.attempt &&
                                r.trajectory === g.trajectory,
                            );
                            return (
                              <tr
                                key={g.attempt}
                                className={
                                  filters.game === g.id ? "chosen" : ""
                                }
                              >
                                <td>
                                  <button
                                    className="game-open"
                                    aria-label={`Inspect game ${g.id}`}
                                    onClick={() =>
                                      set({
                                        game: g.id,
                                        ply: 0,
                                        offset: data.offset,
                                      })
                                    }
                                  >
                                    #{g.id}
                                    <small>{g.source}</small>
                                  </button>
                                </td>
                                <td>
                                  <span
                                    className={`badge disposition-${g.disposition}`}
                                  >
                                    {g.disposition}
                                  </span>
                                  <small>{outcomeName(g)}</small>
                                </td>
                                <td>
                                  {g.policy}
                                  <small>
                                    {g.split} · run {g.run_id}
                                  </small>
                                </td>
                                <td>{g.plies - g.start_ply}</td>
                                <td>
                                  {g.selected}
                                  <small>
                                    {g.shortfall
                                      ? `${g.shortfall} unfilled`
                                      : Object.keys(g.requested).length
                                        ? "quota met"
                                        : "not recorded"}
                                  </small>
                                </td>
                                <td>
                                  {review ? (
                                    <span
                                      className={`review-chip review-${review.status}`}
                                    >
                                      {review.status}
                                    </span>
                                  ) : (
                                    "—"
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="data-pagination">
                    <span>
                      {data.total
                        ? `${number(data.offset + 1)}–${number(Math.min(data.offset + data.limit, data.total))} of ${number(data.total)}`
                        : "0 games"}
                    </span>
                    <Button
                      size="sm"
                      disabled={data.offset === 0}
                      onClick={() =>
                        set({ offset: Math.max(0, data.offset - data.limit) })
                      }
                    >
                      Previous page
                    </Button>
                    <Button
                      size="sm"
                      disabled={data.offset + data.limit >= data.total}
                      onClick={() => set({ offset: data.offset + data.limit })}
                    >
                      Next page
                    </Button>
                  </div>
                  <details className="data-batch-notes">
                    <summary>Run boundaries and interpretation</summary>
                    <p className="muted">
                      Every row is one stored attempt. Continuation runs link to
                      prior evidence; inherited games stay in their original run
                      and are counted once. Planned run totals are not summed
                      across continuations. Review tags do not filter training
                      inputs.
                    </p>
                    <div className="scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Run</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Accepted / rejected</th>
                            <th>Selected occurrences</th>
                            <th>Shortfall games</th>
                            <th>Planned in run</th>
                            <th>Continues</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.runs.map((r) => (
                            <tr key={r.id}>
                              <td>{r.id}</td>
                              <td>{r.name}</td>
                              <td>{r.status}</td>
                              <td>
                                {number(data.run_stats[String(r.id)].accepted)}{" "}
                                /{" "}
                                {number(data.run_stats[String(r.id)].rejected)}
                              </td>
                              <td>
                                {number(data.run_stats[String(r.id)].selected)}
                              </td>
                              <td>
                                {number(
                                  data.run_stats[String(r.id)].shortfall_games,
                                )}
                              </td>
                              <td>{number(r.planned)}</td>
                              <td>{r.continued_from ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </div>
                {filters.game && (
                  <GameInspector
                    key={`${collection}-${filters.game}`}
                    collection={collection}
                    gameId={filters.game}
                    ply={filters.ply ?? 0}
                    onPly={(ply) => onFilters({ ...filters, collection, ply })}
                    openGame={(game) => set({ game, ply: 0 })}
                    saved={saved}
                    blocked={!!stored.error}
                    onSave={() => setRevision((v) => v + 1)}
                    close={() =>
                      set({
                        game: undefined,
                        ply: undefined,
                        offset: data.offset,
                      })
                    }
                  />
                )}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
