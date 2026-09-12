import { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReportBundle } from "./api";
import { ReportView, type Filters, type ReportSource } from "./report";
import { ResearchReport, type ResearchBundle } from "./research-report";
import "./style.css";
const payload: ReportBundle | ResearchBundle = JSON.parse(
  document.getElementById("data")!.textContent!,
);
function searchSource(bundle: ReportBundle): ReportSource {
  return {
    key: bundle.data.evidence_sha256,
    unit: async (id) => {
      const unit = bundle.units.find((unit) => unit.job.id === id);
      if (!unit) throw new Error("Recorded unit not found.");
      return unit;
    },
    trace: async (id, options) => {
      const trace = bundle.traces.find((trace) => trace.summary.id === id);
      if (!trace) throw new Error("Trace not found.");
      const events = trace.events.filter(
        (event) =>
          event.parent === options.parent &&
          (options.show_work || event.kind !== "work") &&
          (options.view === "all" ||
            options.parent !== null ||
            event.kind === "mcts-tree"),
      );
      return {
        events: events.slice(options.offset, options.offset + 100),
        offset: options.offset,
        total: events.length,
      };
    },
  };
}
function Offline({ bundle }: { bundle: ReportBundle }) {
  const [filters, setFilters] = useState<Filters>({});
  const source = useMemo(() => searchSource(bundle), [bundle]);
  return (
    <main className="offline">
      <p className="eyebrow">QI / OFFLINE REPORT</p>
      <ReportView
        data={bundle.data}
        source={source}
        filters={filters}
        onFilters={setFilters}
      />
    </main>
  );
}
const client = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: Infinity, refetchOnWindowFocus: false },
  },
});
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={client}>
    {"kind" in payload && payload.kind === "research-report-v1" ? (
      <ResearchReport bundle={payload} />
    ) : (
      <Offline bundle={payload as ReportBundle} />
    )}
  </QueryClientProvider>,
);
