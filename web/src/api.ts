export type Snapshot = {
  schema_version: 1;
  ruleset: "xiangqi-training-v1";
  initial_fen: string;
  moves: string[];
};
export type Position = {
  snapshot: Snapshot;
  board: string;
  turn: "red" | "black";
  ply: number;
  state_hash: string;
  legal_moves: string[];
  in_check: boolean;
  outcome: { winner: "red" | "black" | null; reason: string } | null;
};
export type PlayerInfo = {
  id: string;
  version: string;
  label: string;
  description: string;
  uses_search: boolean;
  default_nodes: number;
  default_depth: number;
  default_rollout_plies: number | null;
};
export type Choice = {
  move: string;
  player_version: string;
  nodes: number;
  completed_depth: number;
  seed: number;
  elapsed_ms: number;
  qnodes: number;
  max_qply: number;
  checkpoint_sha256: string | null;
  model_calls: number;
  mcts: {
    simulations: number;
    tree_visits: number;
    rollout_steps: number;
    terminal_simulations: number;
    rollout_cutoffs: number;
    budget_cutoffs: number;
    unfinished_simulations: number;
    max_tree_depth: number;
    leaf_nodes: number;
    leaf_aborts: number;
    root_moves: { move: string; visits: number; mean_value: number | null }[];
  } | null;
  search_stats: {
    cutoffs: number;
    see_nodes: number;
    extensions: number;
    max_extensions: number;
    tt_hits: number;
    tt_cutoffs: number;
  } | null;
  evaluation: {
    material: number;
    placement: number;
    mobility: number;
    king_safety: number;
  } | null;
};
export type OpponentResult = { position: Position; choice: Choice };

export async function request<T = Position>(
  path: string,
  data?: unknown,
  signal?: AbortSignal,
  method: "GET" | "POST" = "POST",
): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method,
    signal,
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      result.error?.message ?? "The request failed. Please try again.",
    );
  return result;
}
