import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import "./research-report.css";

type FacetValue = string | number;
type Metric = {
  key: string;
  label: string;
  /** Percent values are fractions: 0.2 displays as 20.00%. */
  format: "percent" | "decimal" | "integer";
  unit: string;
  note: string;
  precision?: number;
};
type Explorer = {
  id: string;
  title: string;
  description: string;
  caveat: string;
  facets: {
    key: string;
    label: string;
    values: FacetValue[];
    initial: FacetValue;
  }[];
  metrics: Metric[];
  rows: {
    label: string;
    facets: Record<string, FacetValue>;
    values: Record<string, number | null>;
    notes: Record<string, string>;
  }[];
};
type Resource = {
  path: string;
  sha256: string | null;
  mime: string;
  content: string | null;
  reason: string | null;
};
export type ResearchBundle = {
  kind: "research-report-v1";
  title: string;
  description: string;
  date: string;
  outcome: string;
  source: { path: string; sha256: string };
  summary: string;
  stats: { label: string; value: string; note: string }[];
  takeaways: { title: string; body: string }[];
  sections: { id: string; title: string; markdown: string; note?: string }[];
  explorers: Explorer[];
  resources: Record<string, Resource>;
  images: Record<string, string>;
};

function formatValue(value: number | null | undefined, metric: Metric) {
  if (value == null || !Number.isFinite(value)) return "Unknown";
  const number = new Intl.NumberFormat("en-US", {
    style: metric.format === "percent" ? "percent" : "decimal",
    minimumFractionDigits:
      metric.format === "integer" ? 0 : (metric.precision ?? 2),
    maximumFractionDigits:
      metric.format === "integer" ? 0 : (metric.precision ?? 2),
  }).format(value);
  return metric.unit && metric.format !== "percent"
    ? `${number} ${metric.unit}`
    : number;
}

function MetricExplorer({ explorer }: { explorer: Explorer }) {
  const [facets, setFacets] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      explorer.facets.map((facet) => [facet.key, String(facet.initial)]),
    ),
  );
  const [metricKey, setMetricKey] = useState(explorer.metrics[0]?.key ?? "");
  const metric = explorer.metrics.find((item) => item.key === metricKey);
  const rows = explorer.rows.filter((row) =>
    explorer.facets.every(
      (facet) => String(row.facets[facet.key]) === facets[facet.key],
    ),
  );
  if (!metric) return null;
  const values = rows
    .map((row) => row.values[metric.key])
    .filter(
      (value): value is number => value != null && Number.isFinite(value),
    );
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const span = high - low || 1;
  const zero = ((0 - low) / span) * 100;
  return (
    <section
      id={explorer.id}
      className="rr-explorer"
      data-testid="report-explorer"
      aria-labelledby={`${explorer.id}-title`}
    >
      <div className="rr-section-heading">
        <p className="rr-kicker">Explore the recorded evidence</p>
        <h2 id={`${explorer.id}-title`}>{explorer.title}</h2>
        <p>{explorer.description}</p>
      </div>
      <div className="rr-controls">
        {explorer.facets.map((facet) => (
          <label key={facet.key}>
            {facet.label}
            <select
              aria-label={facet.label}
              value={facets[facet.key]}
              onChange={(event) =>
                setFacets({ ...facets, [facet.key]: event.target.value })
              }
            >
              {facet.values.map((value) => (
                <option key={value} value={String(value)}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        ))}
        <label className="rr-metric-control">
          Metric
          <select
            aria-label={`${explorer.title} metric`}
            value={metricKey}
            onChange={(event) => setMetricKey(event.target.value)}
          >
            {explorer.metrics.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="rr-metric-context" aria-live="polite">
        <h3>{metric.label}</h3>
        <p>{metric.note}</p>
      </div>
      <div
        className="rr-table-scroll"
        role="region"
        aria-label={`${metric.label} comparison`}
        tabIndex={0}
      >
        <table className="rr-chart-table">
          <thead>
            <tr>
              <th scope="col">Model / condition</th>
              <th scope="col" className="rr-bar-column">
                Relative magnitude
              </th>
              <th scope="col">Recorded value</th>
              <th scope="col">Context / denominator</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const value = row.values[metric.key];
              const known = value != null && Number.isFinite(value);
              const start = known
                ? ((Math.min(value, 0) - low) / span) * 100
                : zero;
              const width = known ? (Math.abs(value) / span) * 100 : 0;
              return (
                <tr key={`${row.label}-${index}`}>
                  <th scope="row">{row.label}</th>
                  <td className="rr-bar-column" aria-hidden="true">
                    <div className="rr-bar-track">
                      <span
                        className="rr-bar-zero"
                        style={{ left: `${zero}%` }}
                      />
                      {known && (
                        <span
                          className="rr-bar"
                          style={{ left: `${start}%`, width: `${width}%` }}
                        />
                      )}
                      {!known && (
                        <span className="rr-bar-unknown">No value</span>
                      )}
                    </div>
                  </td>
                  <td className="rr-value">{formatValue(value, metric)}</td>
                  <td>{row.notes[metric.key] || row.notes.context || "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!rows.length && (
        <p className="rr-callout">No recorded rows match this selection.</p>
      )}
      <p className="rr-scale-note">
        Fixed source order. Bar scale follows the selected values and includes
        zero; it changes between metrics. Unknown values remain unknown.
      </p>
      <p className="rr-callout">{explorer.caveat}</p>
    </section>
  );
}

function downloadResource(resource: Resource) {
  if (resource.content == null) return;
  const blob = new Blob([resource.content], { type: resource.mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = resource.path.split("/").pop() || "evidence.txt";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function ResearchReport({ bundle }: { bundle: ResearchBundle }) {
  const [evidenceKey, setEvidenceKey] = useState<string | null>(null);
  const [imageKey, setImageKey] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const resource = evidenceKey ? bundle.resources[evidenceKey] : null;
  const image = imageKey ? bundle.images[imageKey] : null;
  const showingDialog = Boolean(resource || image);
  const closeDialog = () => {
    setEvidenceKey(null);
    setImageKey(null);
  };
  useEffect(() => {
    if (showingDialog) dialogRef.current?.showModal();
    else dialogRef.current?.close();
  }, [showingDialog]);

  // Keep element component identities stable so opening a preview preserves its
  // invoking link; native dialog focus restoration can then return to that node.
  const markdownComponents = useMemo<Components>(
    () => ({
      a: ({ href, children }) => {
        if (!href)
          return (
            <span title="This reference is not embedded; consult the source checkout.">
              {children}
            </span>
          );
        const key = href?.slice(1) ?? "";
        if (href?.startsWith("#") && bundle.resources[key]) {
          return (
            <a
              href={href}
              className="rr-evidence-link"
              onClick={(event) => {
                event.preventDefault();
                setImageKey(null);
                setEvidenceKey(key);
              }}
            >
              {children}
              <span aria-hidden="true"> ↗</span>
            </a>
          );
        }
        return (
          <a
            href={href}
            {...(href?.startsWith("http")
              ? { target: "_blank", rel: "noreferrer" }
              : {})}
          >
            {children}
          </a>
        );
      },
      img: ({ src, alt }) => {
        const key = src?.startsWith("#") ? src.slice(1) : "";
        const embedded = bundle.images[key];
        if (!embedded)
          return (
            <span className="rr-image-unavailable">
              Image unavailable: {alt || src}
            </span>
          );
        return (
          <button
            type="button"
            className="rr-image-button"
            aria-label={`Enlarge ${alt || "figure"}`}
            onClick={() => {
              setEvidenceKey(null);
              setImageKey(key);
            }}
          >
            <img src={embedded} alt={alt || "Report figure"} loading="lazy" />
            <span className="rr-image-caption">
              {alt || "Report figure"}
              <span aria-hidden="true"> · Open full size ↗</span>
            </span>
          </button>
        );
      },
      table: ({ children }) => (
        <div
          className="rr-table-scroll"
          role="region"
          aria-label="Report data table"
          tabIndex={0}
        >
          <table>{children}</table>
        </div>
      ),
    }),
    [bundle],
  );
  const markdown = (content: string) => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      urlTransform={(url) => {
        if (url.startsWith("#")) return url;
        return /^(https?:|mailto:)/i.test(url) ? url : "";
      }}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  );

  return (
    <div className="research-report" id="research-report">
      <a className="rr-skip" href="#report-content">
        Skip to report
      </a>
      <aside className="rr-sidebar" aria-label="Report navigation">
        <a className="rr-brand" href="#report-top">
          <span className="rr-brand-mark" aria-hidden="true">
            棋
          </span>
          <span>
            QI LAB<span className="rr-brand-subtitle">Research notebook</span>
          </span>
        </a>
        <div className="rr-sidebar-meta">
          <span className="rr-kicker">Field notes</span>
          <time>{bundle.date}</time>
        </div>
        <nav aria-label="Table of contents">
          <a href="#report-top">At a glance</a>
          {bundle.explorers.map((explorer) => (
            <a href={`#${explorer.id}`} key={explorer.id}>
              {explorer.title}
            </a>
          ))}
          {bundle.sections.map((section, index) => (
            <a href={`#${section.id}`} key={section.id}>
              <span className="rr-nav-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              {section.title}
            </a>
          ))}
          <a href="#report-provenance">Sources &amp; provenance</a>
        </nav>
        <div className="rr-sidebar-footer">
          <span className="rr-status">{bundle.outcome}</span>
          <p>
            A portable snapshot.
            <br />
            Read, compare, trace the evidence.
          </p>
          <button
            type="button"
            className="rr-button"
            onClick={() => window.print()}
          >
            Print / save PDF
          </button>
        </div>
      </aside>
      <main id="report-content" className="rr-main">
        <header id="report-top" className="rr-hero">
          <div className="rr-hero-meta">
            <p className="rr-kicker">QI / Learning research</p>
            <span>{bundle.date}</span>
          </div>
          <h1>{bundle.title}</h1>
          <p className="rr-description">{bundle.description}</p>
          {bundle.summary && (
            <div className="rr-thesis">
              <span className="rr-kicker">The working conclusion</span>
              <p>{bundle.summary}</p>
            </div>
          )}
          {bundle.stats.length > 0 && (
            <div className="rr-stats">
              {bundle.stats.map((stat) => (
                <div className="rr-stat" key={stat.label}>
                  <strong>{stat.value}</strong>
                  <span>{stat.label}</span>
                  <small>{stat.note}</small>
                </div>
              ))}
            </div>
          )}
        </header>
        {bundle.takeaways.length > 0 && (
          <section className="rr-takeaways" aria-label="Key findings">
            {bundle.takeaways.map((takeaway, index) => (
              <article key={takeaway.title}>
                <span className="rr-kicker">
                  Finding {String(index + 1).padStart(2, "0")}
                </span>
                <h2>{takeaway.title}</h2>
                <p>{takeaway.body}</p>
              </article>
            ))}
          </section>
        )}
        {bundle.explorers.map((explorer) => (
          <MetricExplorer key={explorer.id} explorer={explorer} />
        ))}
        <div className="rr-narrative-heading">
          <span className="rr-kicker">The full account</span>
          <p>
            Findings, competing explanations, and the limits of this evidence.
          </p>
        </div>
        {bundle.sections.map((section, index) => (
          <section
            className="rr-section"
            id={section.id}
            key={section.id}
            aria-labelledby={`${section.id}-title`}
          >
            <div className="rr-section-title">
              <span className="rr-section-number" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h2 id={`${section.id}-title`}>{section.title}</h2>
            </div>
            {section.note && (
              <p className="rr-callout rr-section-note">{section.note}</p>
            )}
            <div className="rr-prose">{markdown(section.markdown)}</div>
          </section>
        ))}
        <footer id="report-provenance" className="rr-provenance">
          <p className="rr-kicker">Sources &amp; provenance</p>
          <h2>A presentation of retained evidence</h2>
          <p>
            This HTML embeds the report and its selected evidence for offline
            reading. Generating this presentation does not rerun experiments or
            verify their conclusions. The source narrative and recorded
            conditions govern interpretation.
          </p>
          <dl>
            <dt>Canonical report</dt>
            <dd>{bundle.source.path}</dd>
            <dt>Source SHA-256</dt>
            <dd>
              <code>{bundle.source.sha256}</code>
            </dd>
          </dl>
          <p className="rr-scale-note">
            Evidence links open embedded previews with their source path and
            hash. Missing or oversized source material is identified explicitly.
            No external assets are required.
          </p>
          <details className="rr-source-list">
            <summary>
              Inspect sources and presentation specification (
              {Object.keys(bundle.resources).length})
            </summary>
            <ul>
              {Object.entries(bundle.resources).map(([key, item]) => (
                <li key={key}>
                  <a
                    href={`#${key}`}
                    onClick={(event) => {
                      event.preventDefault();
                      setImageKey(null);
                      setEvidenceKey(key);
                    }}
                  >
                    {item.path}
                  </a>
                  <span>
                    {item.content == null ? "Not embedded" : "Embedded copy"}
                  </span>
                </li>
              ))}
            </ul>
          </details>
        </footer>
      </main>
      <dialog
        ref={dialogRef}
        className={`rr-dialog${image ? " rr-dialog-image" : ""}`}
        onClose={closeDialog}
        onClick={(event) => {
          if (event.target === event.currentTarget) closeDialog();
        }}
        aria-labelledby="rr-dialog-title"
      >
        <div className="rr-dialog-header">
          <div>
            <p className="rr-kicker">
              {image ? "Report figure" : "Embedded evidence"}
            </p>
            <h2 id="rr-dialog-title">
              {resource?.path.split("/").pop() || "Figure detail"}
            </h2>
          </div>
          <button
            type="button"
            className="rr-button"
            onClick={closeDialog}
            autoFocus
          >
            Close <span aria-hidden="true">×</span>
          </button>
        </div>
        {resource && (
          <>
            <div className="rr-resource-meta">
              <dl>
                <dt>Source path</dt>
                <dd>{resource.path}</dd>
                <dt>SHA-256</dt>
                <dd>
                  <code>{resource.sha256 || "Not available"}</code>
                </dd>
              </dl>
              {resource.content != null && (
                <button
                  type="button"
                  className="rr-button"
                  onClick={() => downloadResource(resource)}
                >
                  Download embedded copy
                </button>
              )}
            </div>
            {resource.content == null ? (
              <p className="rr-callout">
                {resource.reason ||
                  "This source was not embedded in the HTML. Use the source path to inspect it locally."}
              </p>
            ) : (
              <div className="rr-resource-preview">
                {resource.mime.includes("markdown") ||
                /\.md$/i.test(resource.path) ? (
                  <div className="rr-prose">{markdown(resource.content)}</div>
                ) : (
                  <pre>
                    <code>{resource.content}</code>
                  </pre>
                )}
              </div>
            )}
          </>
        )}
        {image && <img src={image} alt="Enlarged report figure" />}
      </dialog>
    </div>
  );
}
