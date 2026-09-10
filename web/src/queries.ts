import { queryOptions } from "@tanstack/react-query";
import {
  read,
  type PlayerInfo,
  type RunEntry,
  type TraceJob,
  type Glossary,
} from "./api";
export const playersQuery = queryOptions({
  queryKey: ["players"],
  queryFn: ({ signal }) => read<PlayerInfo[]>("players", signal),
  staleTime: 15000,
});
export const runsQuery = queryOptions({
  queryKey: ["experiments"],
  queryFn: ({ signal }) => read<RunEntry[]>("experiments", signal),
  staleTime: 10000,
});
export const jobsQuery = queryOptions({
  queryKey: ["trace-jobs"],
  queryFn: ({ signal }) => read<TraceJob[]>("trace-jobs", signal),
  refetchInterval: (query) =>
    query.state.data?.some((job) => job.status === "running") ? 1000 : 15000,
});
export const glossaryQuery = queryOptions({
  queryKey: ["reference"],
  queryFn: ({ signal }) => read<Glossary>("reference", signal),
  staleTime: Infinity,
});
