import { abortable } from "./request-gate";
import type { components } from "./generated-api";
export type Schema<K extends keyof components["schemas"]> =
  components["schemas"][K];
export type Snapshot = Schema<"Snapshot">;
export type Position = Schema<"Position">;
export type Choice = Required<Schema<"Choice">>;
export type PlayerInfo = Required<Schema<"PlayerInfo">>;
export type Controller = Required<Schema<"Controller">>;
export type Controllers = Required<Schema<"Controllers">>;
export type GameSession = Required<Schema<"GameSession">>;
export type PlayResult = Schema<"PlayResult">;
export type ReportData = Schema<"ReportData">;
export type ReportBundle = Schema<"ReportBundle">;
export type UnitDetail = Schema<"UnitDetail">;
export type TracePage = Schema<"TracePage">;
export type TraceEvent = Schema<"TraceEvent">;
export type Glossary = Schema<"Glossary">;
export type RunEntry = Schema<"RunEntry">;
export type TraceJob = Schema<"TraceJob">;
export async function request<T = Position>(
  path: string,
  data?: unknown,
  signal?: AbortSignal,
  method: "GET" | "POST" = "POST",
): Promise<T> {
  const operation = (async () => {
    const response = await fetch(`/api/${path}`, {
      method,
      signal,
      headers: { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    let result;
    try {
      result = await response.json();
    } catch (error) {
      if (signal?.aborted) throw error;
      throw new Error(
        `The server returned ${response.status} ${response.statusText || "response"} without valid JSON. Check that the local server is running and try again.`,
      );
    }
    if (!response.ok)
      throw new Error(
        result?.error?.message ??
          `The request failed (HTTP ${response.status}). Please try again.`,
      );
    return result as T;
  })();
  return signal ? abortable(operation, signal) : operation;
}
export const read = <T>(path: string, signal?: AbortSignal) =>
  request<T>(path, undefined, signal, "GET");
export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export type ExperimentCatalog = Schema<"ExperimentCatalog">;
