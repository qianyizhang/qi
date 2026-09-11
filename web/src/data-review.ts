export type ReviewStatus = "keep" | "inspect" | "exclude";
export type Review = {
  attempt: string;
  game_id: number;
  trajectory: string;
  status: ReviewStatus;
  note: string;
  ply: number;
  updated: string;
};
export const reviewPrefix = (collection: string) =>
  `qi.collection-review.v1:${collection}:`;
export function readReviews(collection: string): {
  reviews: Review[];
  error: string;
} {
  const reviews: Review[] = [];
  try {
    const prefix = reviewPrefix(collection);
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key?.startsWith(prefix)) continue;
      const value = JSON.parse(localStorage.getItem(key)!);
      if (
        !value ||
        typeof value.attempt !== "string" ||
        key !== prefix + value.attempt ||
        !Number.isInteger(value.game_id) ||
        typeof value.trajectory !== "string" ||
        !["keep", "inspect", "exclude"].includes(value.status) ||
        typeof value.note !== "string" ||
        value.note.length > 4000 ||
        !Number.isInteger(value.ply) ||
        value.ply < 0 ||
        value.ply > 300 ||
        typeof value.updated !== "string"
      )
        throw new Error("Invalid stored review");
      reviews.push(value as Review);
    }
    return { reviews, error: "" };
  } catch {
    return {
      reviews: [],
      error:
        "Browser reviews could not be read. Existing bytes are preserved; saving is disabled.",
    };
  }
}
export type DataFilters = {
  collection?: string;
  run?: number;
  policy?: string;
  split?: string;
  disposition?: string;
  outcome?: string;
  q?: string;
  phase?: string;
  lens?: "all" | "shortfall" | "long";
  sort?: "newest" | "longest" | "shortfall";
  review?: "all" | ReviewStatus;
  offset?: number;
  game?: number;
  ply?: number;
};
export function parseDataFilters(s: Record<string, unknown>): DataFilters {
  const integer = (v: unknown, max: number) => {
    const n = Number(v);
    return Number.isSafeInteger(n) && n >= 0 && n <= max ? n : undefined;
  };
  return {
    collection: typeof s.collection === "string" ? s.collection : undefined,
    run: integer(s.run, Number.MAX_SAFE_INTEGER),
    policy: typeof s.policy === "string" ? s.policy : undefined,
    split: ["train", "validation"].includes(String(s.split))
      ? String(s.split)
      : undefined,
    disposition: [
      "accepted",
      "rejected",
      "running",
      "failed",
      "interrupted",
    ].includes(String(s.disposition))
      ? String(s.disposition)
      : undefined,
    outcome: typeof s.outcome === "string" ? s.outcome : undefined,
    q: typeof s.q === "string" ? s.q.slice(0, 100) : undefined,
    phase: ["opening", "middlegame", "endgame", "unknown"].includes(
      String(s.phase),
    )
      ? String(s.phase)
      : undefined,
    lens: ["all", "shortfall", "long"].includes(String(s.lens))
      ? (s.lens as DataFilters["lens"])
      : undefined,
    sort: ["newest", "longest", "shortfall"].includes(String(s.sort))
      ? (s.sort as DataFilters["sort"])
      : undefined,
    review: ["all", "keep", "inspect", "exclude"].includes(String(s.review))
      ? (s.review as DataFilters["review"])
      : undefined,
    offset: integer(s.offset, Number.MAX_SAFE_INTEGER),
    game: integer(s.game, Number.MAX_SAFE_INTEGER),
    ply: integer(s.ply, 300),
  };
}
