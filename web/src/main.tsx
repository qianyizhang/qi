import { lazy, Suspense, useEffect, useMemo } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
  useMutation,
} from "@tanstack/react-query";
import {
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  Outlet,
  Link,
} from "@tanstack/react-router";
import {
  ArrowUpRight,
  FlaskConical,
  Home as HomeIcon,
  BookOpen,
  Swords,
} from "lucide-react";
import {
  read,
  request,
  type ReportData,
  type UnitDetail,
  type TracePage,
} from "./api";
import { jobsQuery, playersQuery, runsQuery } from "./queries";
import { SessionProvider, useSession } from "./session";
import { PlayPage } from "./play";
import { ReferencePage } from "./reference";
import type { Filters, ReportSource } from "./report";
import { Button } from "./components/ui/button";
import "./style.css";
const ReportView = lazy(() =>
  import("./report").then((module) => ({ default: module.ReportView })),
);
const navigation = [
  { to: "/", label: "Home", icon: HomeIcon },
  { to: "/play", label: "Play", icon: Swords },
  { to: "/experiments", label: "Experiments", icon: FlaskConical },
  { to: "/reference", label: "Reference", icon: BookOpen },
] as const;
function Shell() {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <header className="app-header">
        <Link to="/" className="wordmark">
          棋 <span>qi</span>
          <small>LEARNING LAB</small>
        </Link>
        <nav aria-label="Main navigation">
          {navigation.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} activeOptions={{ exact: to === "/" }}>
              <Icon size={17} />
              {label}
            </Link>
          ))}
        </nav>
        <span className="local-indicator">Local workspace</span>
      </header>
      <main id="main-content" tabIndex={-1}>
        <Outlet />
      </main>
      <footer>Qi · A place to play, inspect, and learn.</footer>
    </>
  );
}
function JobStatus() {
  const jobs = useQuery(jobsQuery),
    client = useQueryClient();
  const job = jobs.data?.[0];
  const cancel = useMutation({
    mutationFn: (id: string) => request(`trace-jobs/${id}/cancel`),
    retry: false,
    onSuccess: () => client.invalidateQueries({ queryKey: ["trace-jobs"] }),
  });
  useEffect(() => {
    if (job?.status === "succeeded")
      void client.invalidateQueries({
        queryKey: ["report", job.request.run_id],
      });
  }, [job?.id, job?.status, client]);
  if (jobs.error) return <p role="alert">{jobs.error.message}</p>;
  if (jobs.isLoading) return <p className="muted">Loading trace activity…</p>;
  if (!job) return <p className="muted">No trace jobs yet.</p>;
  return (
    <div className="job-status" role="status">
      {cancel.error && <p role="alert">{cancel.error.message}</p>}
      <span className="badge">Trace: {job.status}</span>
      <span>
        {job.message}
        {job.events != null &&
          ` ${job.events} events (${job.recording_complete ? "complete" : "capacity limited"} recording).`}
      </span>
      {job.status === "running" && (
        <>
          <span>Deadline {job.deadline_seconds}s</span>
          <Button
            size="sm"
            onClick={() => cancel.mutate(job.id)}
            disabled={cancel.isPending}
          >
            Cancel trace
          </Button>
        </>
      )}
    </div>
  );
}
function Home() {
  const game = useSession(),
    players = useQuery(playersQuery),
    runs = useQuery(runsQuery);
  return (
    <section>
      <div className="hero">
        <div>
          <p className="eyebrow">YOUR XIANGQI WORKSPACE</p>
          <h1>
            Make a move.
            <br />
            Understand the search.
          </h1>
          <p>
            Play against a policy or engine, watch two players compete, and
            examine the evidence behind their decisions.
          </p>
          <Button variant="default" asChild>
            <Link to="/play">
              {game.position?.ply
                ? `Open saved game · ply ${game.position.ply}`
                : "Open the board"}
              <ArrowUpRight size={18} />
            </Link>
          </Button>
        </div>
        <div className="hero-symbol" aria-hidden>
          棋<span>PLAY / OBSERVE / LEARN</span>
        </div>
      </div>
      <div className="two-columns">
        <article className="card">
          <h2>Available players</h2>
          <p className="muted">
            Each side can use its own checkpoint or engine.
          </p>
          {players.error && <p role="alert">{players.error.message}</p>}
          {players.isLoading && (
            <p className="muted">Loading configured players…</p>
          )}
          <ul className="clean-list">
            {players.data &&
              [...players.data]
                .sort(
                  (a, b) =>
                    Number(!!b.binding_sha256) - Number(!!a.binding_sha256),
                )
                .slice(0, 6)
                .map((player) => (
                  <li key={player.id}>
                    <span>
                      {player.label}
                      <small>{player.implementation_id}</small>
                    </span>
                    <span className="badge">
                      {player.available ? "Ready" : "Unavailable"}
                    </span>
                  </li>
                ))}
          </ul>
          {players.data && (
            <Link to="/play">
              Choose from {players.data.length} computer players →
            </Link>
          )}
        </article>
        <article className="card">
          <h2>Recent experiments</h2>
          <p className="muted">
            Saved runs discovered in configured artifact folders.
          </p>
          {runs.error && <p role="alert">{runs.error.message}</p>}
          {runs.isLoading && <p className="muted">Finding saved runs…</p>}
          {runs.data?.length === 0 && (
            <p>
              No saved runs found. Create search runs with the CLI, then refresh
              Experiments.
            </p>
          )}
          <ul className="clean-list">
            {runs.data?.slice(0, 6).map((run) => (
              <li key={run.id}>
                {run.error ? (
                  <span>
                    {run.name}
                    <small>{run.error}</small>
                  </span>
                ) : (
                  <Link to="/experiments/$runId" params={{ runId: run.id }}>
                    {run.name}
                    <small>{run.location}</small>
                  </Link>
                )}
                <span className="badge">{run.status}</span>
              </li>
            ))}
          </ul>
          <Link to="/experiments">Browse experiments →</Link>
        </article>
      </div>
      <article className="card">
        <h2>Trace activity</h2>
        <JobStatus />
      </article>
    </section>
  );
}
function Experiments() {
  const runs = useQuery(runsQuery);
  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">MEASURED WORK</p>
          <h1>Experiments</h1>
          <p className="muted">
            Inspect saved runs. Generate traces from compatible recorded
            decisions.
          </p>
        </div>
        <Button onClick={() => void runs.refetch()}>Refresh runs</Button>
      </div>
      <JobStatus />
      {runs.error && <p role="alert">{runs.error.message}</p>}
      {runs.isLoading && <p role="status">Finding saved runs…</p>}
      {runs.data?.length === 0 && (
        <div className="card">
          <h2>No saved runs found</h2>
          <p>
            The server discovers search runs under artifacts/experiments by
            default. QI_EXPERIMENT_ROOTS configures additional roots.
          </p>
          <p>
            Run <code>qi experiment run --plan … --output …</code> to create
            evidence.
          </p>
        </div>
      )}
      <div className="reference-grid">
        {runs.data?.map((run) => (
          <article className="card" key={run.id}>
            <span className="badge">
              {run.kind} · {run.status}
            </span>
            <h2>{run.name}</h2>
            <p className="muted">{run.location}</p>
            {run.error ? (
              <p className="error">{run.error}</p>
            ) : (
              <Link to="/experiments/$runId" params={{ runId: run.id }}>
                Inspect evidence →
              </Link>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
const rootRoute = createRootRoute({ component: Shell });
const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Home,
});
const playRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/play",
  component: PlayPage,
});
const experimentsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/experiments",
  component: Experiments,
});
const referenceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/reference",
  component: ReferencePage,
});
const reportRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/experiments/$runId",
  validateSearch: (search: Record<string, unknown>): Filters => ({
    player: typeof search.player === "string" ? search.player : undefined,
    budget:
      typeof search.budget === "string" || typeof search.budget === "number"
        ? String(search.budget)
        : undefined,
    opening: typeof search.opening === "string" ? search.opening : undefined,
    unit: typeof search.unit === "string" ? search.unit : undefined,
    ply: Number.isInteger(Number(search.ply))
      ? Math.max(0, Math.min(300, Number(search.ply)))
      : 0,
    trace: typeof search.trace === "string" ? search.trace : undefined,
  }),
  component: ExperimentDetail,
});
function ExperimentDetail() {
  const { runId } = reportRoute.useParams(),
    filters = reportRoute.useSearch(),
    navigate = reportRoute.useNavigate();
  const query = useQuery({
    queryKey: ["report", runId],
    queryFn: ({ signal }) => read<ReportData>(`experiments/${runId}`, signal),
    retry: false,
  });
  const client = useQueryClient();
  const source = useMemo<ReportSource>(
    () => ({
      key: `${runId}-${query.data?.presentation_sha256}`,
      unit: (id) => read<UnitDetail>(`experiments/${runId}/units/${id}`),
      trace: (id, options) => {
        const params = new URLSearchParams({
          offset: String(options.offset),
          view: options.view,
          show_work: String(options.show_work),
        });
        if (options.parent != null)
          params.set("parent", String(options.parent));
        return read<TracePage>(`experiments/${runId}/traces/${id}?${params}`);
      },
      evidenceLink: (href) => `/api/experiments/${runId}/evidence/${href}`,
      generate: async (unit, turn, limit) => {
        await request("trace-jobs", {
          run_id: runId,
          unit_id: unit.job.id,
          unit_sha256: unit.sha256,
          turn_index: turn,
          limit,
          request_id: crypto.randomUUID(),
        });
        await client.invalidateQueries({ queryKey: ["trace-jobs"] });
      },
    }),
    [runId, query.data?.presentation_sha256, client],
  );
  return (
    <>
      <div className="toolbar report-actions">
        <Link to="/experiments">← Experiments</Link>
        <Button onClick={() => void query.refetch()}>Refresh evidence</Button>
        <Button asChild>
          <a href={`/api/experiments/${runId}/export?format=html`}>
            Export offline HTML
          </a>
        </Button>
        <Button asChild>
          <a href={`/api/experiments/${runId}/export?format=md`}>
            Export Markdown
          </a>
        </Button>
      </div>
      <JobStatus />
      {query.error && (
        <p role="alert">
          This run could not be validated: {query.error.message}
        </p>
      )}
      {query.data && !query.error ? (
        <Suspense fallback={<p role="status">Loading report views…</p>}>
          <ReportView
            key={source.key}
            data={query.data}
            source={source}
            filters={filters}
            onFilters={(search) => void navigate({ search })}
          />
        </Suspense>
      ) : (
        query.isLoading && <p>Validating recorded evidence…</p>
      )}
    </>
  );
}
const router = createRouter({
  routeTree: rootRoute.addChildren([
    homeRoute,
    playRoute,
    experimentsRoute,
    reportRoute,
    referenceRoute,
  ]),
  defaultPreload: "intent",
});
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <SessionProvider>
      <RouterProvider router={router} />
    </SessionProvider>
  </QueryClientProvider>,
);
