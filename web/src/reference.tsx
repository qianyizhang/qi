import { createContext, useContext, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import * as Tooltip from "@radix-ui/react-tooltip";
import * as Dialog from "@radix-ui/react-dialog";
import { glossaryQuery } from "./queries";
import type { Glossary } from "./api";
import { Button } from "./components/ui/button";
export const GlossaryContext = createContext<Glossary | null>(null);
export function Term({
  name,
  children,
}: {
  name: string;
  children?: ReactNode;
}) {
  const glossary = useContext(GlossaryContext);
  const entry = glossary?.entries.find((entry) =>
    [entry.term, ...entry.aliases].some(
      (alias) => alias.toLowerCase() === name.toLowerCase(),
    ),
  );
  if (!entry) return <>{children ?? name}</>;
  return (
    <Dialog.Root>
      <Tooltip.Provider>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <Dialog.Trigger className="term">{children ?? name}</Dialog.Trigger>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content className="tooltip" sideOffset={6}>
              {entry.chinese} · {entry.meaning}
              <Tooltip.Arrow />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <Dialog.Title>
            {entry.term} · {entry.chinese}
          </Dialog.Title>
          <Dialog.Description>{entry.meaning}</Dialog.Description>
          <p>{entry.avoid !== "—" && `Avoid: ${entry.avoid}`}</p>
          <Dialog.Close asChild>
            <Button>Close definition</Button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function ReferenceList({
  glossary,
  initialSearch = "",
}: {
  glossary: Glossary;
  initialSearch?: string;
}) {
  const [search, setSearch] = useState(initialSearch);
  const [category, setCategory] = useState("");
  const categories = [
    ...new Set(glossary.entries.map((entry) => entry.category)),
  ];
  const entries = glossary.entries.filter(
    (entry) =>
      (!category || entry.category === category) &&
      [entry.term, entry.chinese, entry.meaning, ...entry.aliases]
        .join(" ")
        .toLowerCase()
        .includes(search.trim().toLowerCase()),
  );
  return (
    <div id="glossary-reference">
      <div className="reference-tools">
        <label className="reference-search">
          Find a term, abbreviation, or field name
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Try TT, qnodes, or 搜索"
          />
        </label>
        <label>
          Topic
          <select
            aria-label="Reference topic"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="">All topics</option>
            {categories.map((category) => (
              <option key={category}>{category}</option>
            ))}
          </select>
        </label>
        {(search || category) && (
          <Button
            onClick={() => {
              setSearch("");
              setCategory("");
            }}
          >
            Clear filters
          </Button>
        )}
      </div>
      <p role="status" className="muted">
        {entries.length} of {glossary.entries.length} terms
      </p>
      {entries.length === 0 && (
        <div className="card">
          <h3>No matching terms</h3>
          <p>Try a shorter word, an abbreviation, or another topic.</p>
        </div>
      )}
      <div className="reference-grid">
        {entries.map((entry) => (
          <article className="card" key={entry.term}>
            <small>{entry.category}</small>
            <h3>
              {entry.term} <span className="muted">{entry.chinese}</span>
            </h3>
            <p>{entry.meaning}</p>
            {entry.avoid !== "—" && (
              <p className="muted">Avoid: {entry.avoid}</p>
            )}
            <small>{entry.aliases.join(" · ")}</small>
          </article>
        ))}
      </div>
      <p className="identity">
        Source: {glossary.source} · {glossary.glossary_sha256}
      </p>
    </div>
  );
}
export function ReferencePage() {
  const glossary = useQuery(glossaryQuery);
  return (
    <section>
      <p className="eyebrow">SHARED LANGUAGE</p>
      <h1>Reference</h1>
      <p>
        <Link to="/learn/generation">
          Learn how games become training examples →
        </Link>
      </p>
      <p>
        Players choose moves; the referee owns rules and outcomes. “Engine” is
        conventional for software that searches and evaluates positions. In Qi,
        Player is the broader interface, including random and learned policies.
      </p>
      {glossary.data ? (
        <ReferenceList glossary={glossary.data} />
      ) : (
        <p>{glossary.error?.message ?? "Loading reference…"}</p>
      )}
    </section>
  );
}
