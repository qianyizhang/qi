import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { catalogQuery } from "./queries";
import { Button } from "./components/ui/button";

export function ExperimentCatalogView() {
  const [query, setQuery] = useState("");
  const result = useQuery(catalogQuery(query));
  return (
    <div className="experiment-catalog">
      <div className="catalog-search">
        <label>
          Find prior experiments
          <input
            type="search"
            value={query}
            placeholder="teacher quality, stronger teacher, 1M reference…"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <Button onClick={() => void result.refetch()}>Refresh catalog</Button>
      </div>
      {result.error && <p role="alert">{result.error.message}</p>}
      {result.isLoading && <p role="status">Finding experiments…</p>}
      {result.data && (
        <>
          <p className="muted">{result.data.scope}</p>
          {result.data.issues.length > 0 && (
            <div role="alert" className="card">
              <h2>Catalog needs attention</h2>
              <ul>
                {result.data.issues.map((issue, index) => (
                  <li key={index}>
                    {issue.owner}: {issue.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p role="status">{result.data.entries.length} matching experiments</p>
          {result.data.entries.length === 0 && (
            <p>
              No registered matches. Broaden the search and check the historical
              index before concluding that work is new.
            </p>
          )}
          {result.data.entries.map((entry) => {
            const prefix = `/api/experiment-catalog/${entry.id}`;
            return (
              <article
                className="card catalog-entry"
                key={entry.id}
                id={entry.id}
              >
                <span className="badge">
                  {entry.kind} · Execution: {entry.execution} · Conclusion:{" "}
                  {entry.conclusion}
                </span>
                <h2>{entry.title}</h2>
                <p>{entry.question}</p>
                <p className="catalog-finding">
                  {entry.finding || "No finding recorded yet."}
                </p>
                <p className="muted">{entry.topics.join(" · ")}</p>
                <details>
                  <summary>Conditions, decision and evidence</summary>
                  <dl>
                    <dt>Conditions</dt>
                    <dd>{entry.conditions}</dd>
                    <dt>Limitations</dt>
                    <dd>{entry.limitations || "Not assessed yet."}</dd>
                    <dt>Decision</dt>
                    <dd>{entry.decision || "No decision recorded yet."}</dd>
                    <dt>Revisit when</dt>
                    <dd>{entry.revisit || "Not recorded yet."}</dd>
                    <dt>Contribution beyond prior work</dt>
                    <dd>{entry.novelty}</dd>
                  </dl>
                  <ul>
                    {entry.prior_work?.map((prior) => (
                      <li key={prior.id}>
                        {prior.relationship}{" "}
                        <a href={`/experiments#${prior.id}`}>{prior.id}</a>:{" "}
                        {prior.contribution}
                      </li>
                    ))}
                  </ul>
                  <h3>Evidence availability</h3>
                  <p className="muted">
                    Availability only indicates local presence. It does not
                    verify a finding or an evidence hash.
                  </p>
                  <ul>
                    {entry.evidence_locations.map((ref, index) => (
                      <li key={index}>
                        {ref.role}:{" "}
                        {ref.previewable ? (
                          <a
                            href={`${prefix}/evidence/${index}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {ref.path}
                          </a>
                        ) : (
                          <span>
                            {ref.path} —{" "}
                            {ref.available
                              ? "available locally; no text preview"
                              : "unavailable locally"}
                          </span>
                        )}
                        {ref.sha256 && (
                          <small>Recorded SHA-256: {ref.sha256}</small>
                        )}
                      </li>
                    ))}
                  </ul>
                  <p>
                    <a
                      href={`${prefix}/owner`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Read owning record
                    </a>{" "}
                    ·{" "}
                    <a href={prefix} target="_blank" rel="noreferrer">
                      Catalog JSON
                    </a>{" "}
                    · revision {entry.revision}
                  </p>
                  <small>{entry.owner}</small>
                </details>
              </article>
            );
          })}
        </>
      )}
    </div>
  );
}
