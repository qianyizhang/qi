import type { Choice } from "./api";

export function ChoiceDetails({ choice }: { choice: Choice }) {
  return (
    <details>
      <summary>Last computer move</summary>
      <p>
        {choice.move} · {choice.player_version}
        <br />
        {choice.model_calls > 0
          ? `${choice.model_calls} model pass`
          : choice.mcts
            ? `${choice.mcts.simulations} simulations · ${choice.nodes} visits`
            : `${choice.nodes} nodes · depth ${choice.completed_depth}`}{" "}
        · {choice.elapsed_ms.toFixed(0)} ms · seed {choice.seed}
        {choice.checkpoint_sha256 && (
          <>
            <br />
            Checkpoint {choice.checkpoint_sha256.slice(0, 12)}
          </>
        )}
        {choice.qnodes > 0 && (
          <>
            <br />
            {choice.qnodes} quiescence nodes · up to {choice.max_qply} extra
            plies
          </>
        )}
      </p>
      {choice.search_stats && (
        <p>
          {choice.search_stats.cutoffs} alpha-beta cutoffs ·{" "}
          {choice.search_stats.see_nodes} exchange-analysis visits
          <br />
          {choice.search_stats.extensions} check extensions · at most{" "}
          {choice.search_stats.max_extensions} per path
          <br />
          {choice.search_stats.tt_hits} cache hits ·{" "}
          {choice.search_stats.tt_cutoffs} cached cutoffs
        </p>
      )}
      {choice.evaluation && (
        <div className="evaluation-terms">
          <p>Before-move static assessment · computer’s perspective</p>
          <dl>
            <dt>Material</dt>
            <dd>{choice.evaluation.material}</dd>
            <dt>Piece placement</dt>
            <dd>{choice.evaluation.placement}</dd>
            <dt>Mobility</dt>
            <dd>{choice.evaluation.mobility}</dd>
            <dt>King safety</dt>
            <dd>{choice.evaluation.king_safety}</dd>
            <dt>Total heuristic</dt>
            <dd>
              {Object.values(choice.evaluation).reduce((a, b) => a + b, 0)}
            </dd>
          </dl>
        </div>
      )}
      {choice.mcts && (
        <>
          <p>
            {choice.mcts.tree_visits} tree visits · {choice.mcts.rollout_steps}{" "}
            rollout steps
            {choice.mcts.leaf_nodes > 0 &&
              ` · ${choice.mcts.leaf_nodes} tactical leaf visits`}
            <br />
            {choice.mcts.terminal_simulations} terminal results ·{" "}
            {choice.mcts.rollout_cutoffs + choice.mcts.budget_cutoffs} heuristic
            cutoffs
            <br />
            Deepest tree path: {choice.mcts.max_tree_depth} plies.
            {choice.mcts.unfinished_simulations > 0 &&
              (choice.mcts.leaf_aborts > 0
                ? " Budget interrupted the final tactical evaluation; its value was discarded."
                : " Budget ended before another root move could be sampled.")}
          </p>
          <p>
            Estimates favor the computer when positive; they are not win
            probabilities. The most-visited move is chosen.
          </p>
          <div
            className="root-moves"
            tabIndex={0}
            role="region"
            aria-label="MCTS root move statistics"
          >
            <table>
              <caption>Root moves · computer’s perspective</caption>
              <thead>
                <tr>
                  <th scope="col">Move</th>
                  <th scope="col">Visits</th>
                  <th scope="col">Mean estimate</th>
                </tr>
              </thead>
              <tbody>
                {[...choice.mcts.root_moves]
                  .sort(
                    (a, b) =>
                      b.visits - a.visits ||
                      (b.mean_value ?? -2) - (a.mean_value ?? -2) ||
                      a.move.localeCompare(b.move),
                  )
                  .map((row) => (
                    <tr
                      key={row.move}
                      className={
                        row.move === choice.move ? "chosen" : undefined
                      }
                    >
                      <th scope="row">
                        {row.move}
                        {row.move === choice.move ? " ✓" : ""}
                      </th>
                      <td>{row.visits}</td>
                      <td>
                        {row.mean_value === null
                          ? "—"
                          : row.mean_value.toFixed(3)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </details>
  );
}
