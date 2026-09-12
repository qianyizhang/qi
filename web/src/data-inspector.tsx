import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  X,
  FlipVertical2,
} from "lucide-react";
import { read, download, type Schema, type Position } from "./api";
import { Board } from "./board";
import { Button } from "./components/ui/button";
import type { Review } from "./data-review";
import { ReviewEditor } from "./review-editor";
import {
  number,
  outcomeName,
  label,
  scoreText,
  type Game,
  type Detail,
  type Occurrence,
} from "./data-format";
function ScorePlot({
  occurrences,
  maxPly,
  ply,
  choose,
}: {
  occurrences: Occurrence[];
  maxPly: number;
  ply: number;
  choose: (ply: number) => void;
}) {
  const series = [
    ...new Map(
      occurrences.flatMap((o) =>
        o.analyses
          .filter((a) => a.resolved && a.multipv === 1)
          .map((a) => [a.spec_id, a] as const),
      ),
    ).values(),
  ];
  const points = occurrences.flatMap((o) =>
    o.analyses
      .filter(
        (a) =>
          a.resolved &&
          a.multipv === 1 &&
          a.score?.kind === "cp" &&
          a.score.bound === "exact",
      )
      .map((a) => ({
        a,
        ply: o.ply,
        value: a.score!.value * (o.ply % 2 === 0 ? 1 : -1),
      })),
  );
  const extent = Math.max(100, ...points.map((p) => Math.abs(p.value)));
  const colors = ["#315c4c", "#b76d41", "#597da4", "#86577a"];
  if (!points.length)
    return (
      <p className="muted">
        No exact single-PV centipawn scores retained for this game.
      </p>
    );
  return (
    <div className="score-plot">
      <h3>Retained teacher scores</h3>
      <svg
        viewBox="0 0 620 180"
        role="img"
        aria-label="Exact teacher scores in engine centipawns, Red perspective. Points are clickable."
      >
        <line x1="50" x2="600" y1="80" y2="80" stroke="#c7d1c2" />
        <text x="2" y="19">
          +{extent}
        </text>
        <text x="18" y="84">
          0
        </text>
        <text x="2" y="154">
          −{extent}
        </text>
        <text x="50" y="177">
          0
        </text>
        <text x="552" y="177">
          {maxPly} ply
        </text>
        <line
          x1={50 + (550 * ply) / Math.max(1, maxPly)}
          x2={50 + (550 * ply) / Math.max(1, maxPly)}
          y1="10"
          y2="154"
          stroke="#a9b8a1"
          strokeDasharray="3 4"
        />
        {points.map((p) => (
          <circle
            key={`${p.ply}-${p.a.id}`}
            cx={50 + (550 * p.ply) / Math.max(1, maxPly)}
            cy={80 - (65 * p.value) / extent}
            r={p.ply === ply ? 5.5 : 3.8}
            fill={
              colors[
                series.findIndex((a) => a.spec_id === p.a.spec_id) %
                  colors.length
              ]
            }
            role="button"
            tabIndex={0}
            aria-label={`Ply ${p.ply}, ${label(p.a)}, Red score ${p.value} cp`}
            onClick={() => choose(p.ply)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                choose(p.ply);
              }
            }}
          >
            <title>{`Ply ${p.ply} · ${label(p.a)} · ${p.value} cp (Red)`}</title>
          </circle>
        ))}
      </svg>
      <div className="score-legend">
        {series.map((a, i) => (
          <span key={a.spec_id}>
            <i style={{ background: colors[i % colors.length] }} />
            {label(a)}
          </span>
        ))}
      </div>
      <p className="muted">
        Exact scores only, converted to Red’s perspective. Missing and bounded
        scores are omitted; points are sampled evidence, not a continuous
        evaluation.
      </p>
    </div>
  );
}
function RawAnalysis({
  collection,
  game,
  id,
}: {
  collection: string;
  game: number;
  id: number;
}) {
  const q = useQuery({
    queryKey: ["collection-analysis", collection, game, id],
    queryFn: ({ signal }) =>
      read<Schema<"AnalysisPayload">>(
        `collections/${collection}/games/${game}/analyses/${id}`,
        signal,
      ),
  });
  return (
    <div>
      {q.isLoading && <p role="status">Validating analysis evidence…</p>}
      {q.error && <p role="alert">{q.error.message}</p>}
      {q.data && (
        <>
          <Button
            size="sm"
            onClick={() =>
              download(`qi-game-${game}-analysis-${id}.json`, q.data)
            }
          >
            Export analysis JSON
          </Button>
          <pre>{JSON.stringify(q.data, null, 2)}</pre>
        </>
      )}
    </div>
  );
}
export function GameInspector({
  collection,
  gameId,
  ply,
  onPly,
  openGame,
  saved,
  blocked,
  onSave,
  close,
}: {
  collection: string;
  gameId: number;
  ply: number;
  onPly: (p: number) => void;
  openGame: (id: number) => void;
  saved?: Review;
  blocked: boolean;
  onSave: () => void;
  close: () => void;
}) {
  useEffect(() => {
    document
      .getElementById("data-game-inspector")
      ?.scrollIntoView({ block: "start" });
  }, [gameId]);
  const detail = useQuery({
    queryKey: ["collection-game", collection, gameId],
    queryFn: ({ signal }) =>
      read<Detail>(`collections/${collection}/games/${gameId}`, signal),
  });
  const [flipped, setFlipped] = useState(false),
    [raw, setRaw] = useState<number>(),
    [arrow, setArrow] = useState("actor");
  const value = detail.data;
  const cursor = Math.min(ply, value?.game.plies ?? 300);
  const position = useQuery({
    queryKey: ["collection-position", collection, gameId, cursor],
    queryFn: ({ signal }) =>
      read<Position>(
        `collections/${collection}/games/${gameId}/position?ply=${cursor}`,
        signal,
      ),
    enabled: !!value,
  });
  const occurrence = value?.occurrences.find((o) => o.ply === cursor);
  const chosen = occurrence?.analyses.find(
    (a) => a.spec_id === arrow && a.resolved,
  );
  const move =
    arrow === "actor" ? value?.snapshot.moves?.[cursor] : chosen?.move;
  const labelled = value?.occurrences.filter((o) => o.selected) ?? [];
  const disagreement =
    occurrence?.analyses.filter((a) => a.resolved && a.multipv === 1) ?? [];
  const distinct = new Set(disagreement.map((a) => a.move));
  return (
    <aside
      id="data-game-inspector"
      className="card game-inspector"
      aria-label={`Game ${gameId} inspector`}
    >
      <div className="inspector-heading">
        <div>
          <p className="eyebrow">GAME INSPECTOR</p>
          <h2>Game #{gameId}</h2>
        </div>
        <Button
          size="icon"
          variant="ghost"
          aria-label="Close game inspector"
          onClick={close}
        >
          <X size={18} />
        </Button>
      </div>
      {detail.error && <p role="alert">{detail.error.message}</p>}
      {detail.isLoading && <p role="status">Validating recorded game…</p>}
      {value && (
        <>
          <div className="toolbar">
            <span className={`badge disposition-${value.game.disposition}`}>
              {value.game.disposition}
            </span>
            <span className="badge">{value.game.policy}</span>
            <span className="badge">{value.game.split}</span>
          </div>
          <p className="muted">
            {outcomeName(value.game)} · {value.game.plies - value.initial_ply}{" "}
            generated plies
          </p>
          {value.failure && <p className="error">{value.failure}</p>}
          {value.duplicate_games.length > 0 && (
            <p className="muted">
              Same accepted full trajectory:{" "}
              {value.duplicate_games.map((id) => (
                <button
                  className="text-button"
                  key={id}
                  onClick={() => openGame(id)}
                >
                  #{id}
                </button>
              ))}
            </p>
          )}
          <div className="data-board-wrap">
            {position.error && <p role="alert">{position.error.message}</p>}
            {position.data ? (
              <Board
                view={position.data}
                flipped={flipped}
                selected={null}
                arrows={
                  move
                    ? [
                        {
                          move,
                          color: arrow === "actor" ? "#3e725a" : "#ad6535",
                        },
                      ]
                    : []
                }
              />
            ) : (
              <div className="board-loading" role="status">
                Loading position…
              </div>
            )}
          </div>
          <div className="data-replay-controls">
            <Button
              size="icon"
              aria-label="First ply"
              disabled={cursor === 0}
              onClick={() => onPly(0)}
            >
              <ChevronsLeft size={16} />
            </Button>
            <Button
              size="icon"
              aria-label="Previous ply"
              disabled={cursor === 0}
              onClick={() => onPly(cursor - 1)}
            >
              <ChevronLeft size={16} />
            </Button>
            <label className="sr-only" htmlFor="game-ply">
              Game ply
            </label>
            <input
              id="game-ply"
              aria-label="Game ply"
              type="range"
              min={0}
              max={value.game.plies}
              value={cursor}
              onChange={(e) => onPly(Number(e.target.value))}
            />
            <Button
              size="icon"
              aria-label="Next ply"
              disabled={cursor >= value.game.plies}
              onClick={() => onPly(cursor + 1)}
            >
              <ChevronRight size={16} />
            </Button>
            <Button
              size="icon"
              aria-label="Last ply"
              disabled={cursor >= value.game.plies}
              onClick={() => onPly(value.game.plies)}
            >
              <ChevronsRight size={16} />
            </Button>
            <Button
              size="icon"
              aria-label="Flip board"
              onClick={() => setFlipped(!flipped)}
            >
              <FlipVertical2 size={16} />
            </Button>
          </div>
          <div className="ply-heading">
            <strong>
              Ply {cursor} / {value.game.plies}
            </strong>
            <span>
              {position.data?.turn} to move
              {occurrence ? ` · ${occurrence.phase}` : ""}
            </span>
          </div>
          <label>
            Move overlay
            <select value={arrow} onChange={(e) => setArrow(e.target.value)}>
              <option value="actor">
                Recorded actor move
                {value.snapshot.moves?.[cursor]
                  ? ` · ${value.snapshot.moves[cursor]}`
                  : " · none"}
              </option>
              {occurrence?.analyses
                .filter((a) => a.resolved)
                .map((a) => (
                  <option key={a.id} value={a.spec_id}>
                    {label(a)} · {a.move}
                  </option>
                ))}
              {arrow !== "actor" && arrow !== "none" && !chosen && (
                <option value={arrow}>
                  This teacher specification was not retained here
                </option>
              )}
              <option value="none">No overlay</option>
            </select>
          </label>
          <div className="position-strip" aria-label="Selected positions">
            {labelled.map((o) => (
              <button
                key={o.id}
                className={`phase-${o.phase}`}
                aria-pressed={cursor === o.ply}
                onClick={() => {
                  onPly(o.ply);
                  setArrow("actor");
                  setRaw(undefined);
                }}
                title={`${o.phase} · selected occurrence`}
              >
                {o.ply}
              </button>
            ))}
          </div>
          <p className="muted">
            Jump to a selected position. A position occurrence keeps this game’s
            history with the board.
          </p>
          {occurrence ? (
            <div className="analysis-comparison">
              <h3>
                {occurrence.selected ? "Selected position" : "Actor audit"}
                {occurrence.intervention ? " · marked intervention" : ""}
              </h3>
              {distinct.size > 1 && (
                <p className="analysis-disagreement">
                  Single-PV analyses choose different moves here. Inspect their
                  specifications; disagreement does not establish which is
                  correct.
                </p>
              )}
              <p className="muted">
                Actor played <b>{occurrence.actor_move ?? "—"}</b>. Scores below
                are native to the side to move.
              </p>
              {occurrence.analyses.map((a) => (
                <div className="analysis-row" key={a.id}>
                  <div>
                    <b>{a.move ?? "No move"}</b>
                    <small>
                      {label(a)}
                      {a.depth_limit != null
                        ? ` · max depth ${a.depth_limit}`
                        : ""}
                    </small>
                    <small>
                      {a.status}
                      {a.resolved
                        ? " · first success for this spec"
                        : " · retained attempt"}
                    </small>
                  </div>
                  <div>
                    <b>{scoreText(a)}</b>
                    <small>
                      depth {a.reported_depth ?? "?"} ·{" "}
                      {a.reported_nodes == null
                        ? "?"
                        : number(a.reported_nodes)}{" "}
                      actual nodes
                    </small>
                    <button
                      className="text-button"
                      onClick={() => setRaw(raw === a.id ? undefined : a.id)}
                    >
                      {raw === a.id ? "Hide" : "Inspect"} evidence #{a.id}
                    </button>
                  </div>
                </div>
              ))}
              {occurrence.analyses.length === 0 && (
                <p className="muted">No analyses retained at this position.</p>
              )}
              {raw && occurrence.analyses.some((a) => a.id === raw) && (
                <RawAnalysis collection={collection} game={gameId} id={raw} />
              )}
            </div>
          ) : (
            <p className="muted">
              No analysis retained at ply {cursor}. Choose a numbered position
              above to compare teacher labels.
            </p>
          )}
          <ScorePlot
            occurrences={value.occurrences}
            maxPly={value.game.plies}
            ply={cursor}
            choose={onPly}
          />
          <ReviewEditor
            key={`${collection}-${value.game.attempt}-${value.game.trajectory}`}
            collection={collection}
            game={value.game}
            ply={cursor}
            saved={
              saved?.attempt === value.game.attempt &&
              saved.trajectory === value.game.trajectory
                ? saved
                : undefined
            }
            blocked={blocked}
            onSave={onSave}
          />
          <details>
            <summary>Game provenance and portable replay</summary>
            <p className="identity">
              Source: {value.game.source}
              <br />
              Attempt: {value.game.attempt}
              <br />
              Family: {value.family}
              <br />
              Trajectory: {value.game.trajectory}
            </p>
            <Button
              size="sm"
              onClick={() =>
                download(`qi-generated-game-${gameId}.json`, value.snapshot)
              }
            >
              Export referee snapshot
            </Button>
          </details>
        </>
      )}
    </aside>
  );
}
