import type { Schema } from "./api";
export type Stats = Schema<"CollectionStats">;
export type Game = Schema<"GeneratedGame">;
export type Detail = Schema<"GeneratedGameDetail">;
export type Analysis = Schema<"StoredAnalysis">;
export type Occurrence = Schema<"StoredOccurrence">;
export const number = (n: number) => n.toLocaleString();
export const percent = (n: number, d: number) =>
  d ? `${((100 * n) / d).toFixed(1)}%` : "—";
export const title = (s: string) => s.replaceAll("_", " ").replaceAll("-", " ");
export const outcomeName = (g: Game) =>
  g.outcome === "unfinished"
    ? g.stop_reason === "ply-budget"
      ? "Ply budget · unfinished"
      : "Unfinished"
    : g.outcome === "draw"
      ? `Draw · ${title(g.outcome_reason ?? "unknown")}`
      : `${title(g.outcome)} win · ${g.outcome_reason}`;
export const scoreText = (a: Analysis) =>
  !a.score
    ? "Not reported"
    : `${a.score.bound === "lowerbound" ? "≥" : a.score.bound === "upperbound" ? "≤" : ""}${a.score.value > 0 ? "+" : ""}${a.score.value} ${a.score.kind}`;
export const label = (a: Analysis) =>
  `${number(a.nodes)} nodes · ${a.threads}T · PV ${a.multipv}`;
