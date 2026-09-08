import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { RequestGate } from "./request-gate";

type Snapshot = {
  schema_version: 1;
  ruleset: "xiangqi-training-v1";
  initial_fen: string;
  moves: string[];
};
type Position = {
  snapshot: Snapshot;
  board: string;
  turn: "red" | "black";
  ply: number;
  state_hash: string;
  legal_moves: string[];
  in_check: boolean;
  outcome: { winner: "red" | "black" | null; reason: string } | null;
};
type PlayerInfo = {
  id: string;
  version: string;
  label: string;
  description: string;
  uses_search: boolean;
  default_nodes: number;
  default_depth: number;
};
type Choice = {
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
};
type OpponentResult = { position: Position; choice: Choice };
const symbols: Record<string, string> = {
  K: "帥",
  A: "仕",
  B: "相",
  N: "傌",
  R: "俥",
  C: "炮",
  P: "兵",
  k: "將",
  a: "士",
  b: "象",
  n: "馬",
  r: "車",
  c: "砲",
  p: "卒",
};
const names: Record<string, string> = {
  K: "general",
  A: "advisor",
  B: "elephant",
  N: "horse",
  R: "chariot",
  C: "cannon",
  P: "soldier",
};
const coord = (i: number) =>
  String.fromCharCode(97 + (i % 9)) + Math.floor(i / 9);
const color = (piece: string) =>
  piece === piece.toUpperCase() ? "red" : "black";
async function request<T = Position>(
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
function App() {
  const [live, setLive] = useState<Position | null>(null);
  const [view, setView] = useState<Position | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [flipped, setFlipped] = useState(false);
  const [confirmNew, setConfirmNew] = useState(false);
  const [opponent, setOpponent] = useState("human");
  const [players, setPlayers] = useState<PlayerInfo[]>([]);
  const [catalogError, setCatalogError] = useState("");
  const [catalogRetry, setCatalogRetry] = useState(0);
  const selectedPlayer = players.find((player) => player.id === opponent);
  const [humanSide, setHumanSide] = useState<"red" | "black">("red");
  const [thinking, setThinking] = useState(false);
  const [retry, setRetry] = useState(0);
  const [lastChoice, setLastChoice] = useState<Choice | null>(null);
  const gate = useRef(new RequestGate());
  const file = useRef<HTMLInputElement>(null);
  function accept(p: Position) {
    setLive(p);
    setView(p);
    setSelected(null);
    setConfirmNew(false);
  }
  function cancelWork() {
    gate.current.cancel();
    setThinking(false);
    setBusy(false);
    setSelected(null);
    setError("");
  }
  function run(
    action: (signal: AbortSignal) => Promise<Position | OpponentResult>,
    target: "live" | "view" | "opponent" = "live",
  ) {
    const ticket = gate.current.start();
    setBusy(target !== "opponent");
    setThinking(target === "opponent");
    setError("");
    void action(ticket.signal)
      .then((result) => {
        if (!gate.current.isCurrent(ticket)) return;
        const position = "position" in result ? result.position : result;
        if (target === "view") {
          setView(position);
          setSelected(null);
        } else {
          accept(position);
          setLastChoice("choice" in result ? result.choice : null);
        }
      })
      .catch((e: unknown) => {
        if (gate.current.isCurrent(ticket))
          setError(e instanceof Error ? e.message : "Unable to load game.");
      })
      .finally(() => {
        if (gate.current.isCurrent(ticket)) {
          setBusy(false);
          setThinking(false);
        }
      });
    return () => {
      if (gate.current.cancel(ticket)) {
        setBusy(false);
        setThinking(false);
      }
    };
  }
  useEffect(() => run((signal) => request("new", undefined, signal)), []);
  useEffect(() => {
    const controller = new AbortController();
    setCatalogError("");
    void request<PlayerInfo[]>("players", undefined, controller.signal, "GET")
      .then((catalog) => {
        if (!controller.signal.aborted) setPlayers(catalog);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setCatalogError("Unable to load computer players.");
      });
    return () => controller.abort();
  }, [catalogRetry]);
  const reviewing = !!(view && live && view.ply !== live.ply);
  const opponentTurn = !!(
    live &&
    selectedPlayer &&
    live.turn !== humanSide &&
    !live.outcome
  );
  useEffect(() => {
    if (!live || !selectedPlayer || !opponentTurn || reviewing || confirmNew)
      return;
    return run(
      (signal) =>
        request<OpponentResult>(
          "opponent",
          {
            snapshot: live.snapshot,
            expected_state_hash: live.state_hash,
            player: opponent,
            seed: 0,
            nodes: selectedPlayer.default_nodes,
            depth: selectedPlayer.default_depth,
          },
          signal,
        ),
      "opponent",
    );
  }, [live, opponent, humanSide, reviewing, retry, confirmNew, selectedPlayer]);
  function choose(i: number) {
    if (
      !view ||
      !live ||
      busy ||
      thinking ||
      reviewing ||
      view.outcome ||
      opponentTurn ||
      confirmNew
    )
      return;
    const target = coord(i),
      move = selected ? selected + target : "";
    if (view.legal_moves.includes(move)) {
      run((signal) =>
        request(
          "apply",
          {
            snapshot: live.snapshot,
            move,
            expected_state_hash: live.state_hash,
          },
          signal,
        ),
      );
    } else {
      setSelected(
        view.board[i] !== "." &&
          color(view.board[i]) === view.turn &&
          selected !== target
          ? target
          : null,
      );
    }
  }
  function review(ply: number) {
    if (!live) return;
    run(
      (signal) =>
        request(
          "inspect",
          {
            snapshot: {
              ...live.snapshot,
              moves: live.snapshot.moves.slice(0, ply),
            },
          },
          signal,
        ),
      "view",
    );
  }
  function download() {
    if (!live) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(live.snapshot, null, 2) + "\n"], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `qi-${live.ply}-plies.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  const status = view?.outcome
    ? view.outcome.winner
      ? `${view.outcome.winner === "red" ? "Red" : "Black"} wins`
      : "Draw"
    : `${view?.turn === "black" ? "Black" : "Red"} to move`;
  return (
    <main>
      <header>
        <a className="wordmark" href="/">
          棋 <span>qi</span>
        </a>
        <span className="eyebrow">A GAME-LEARNING LABORATORY</span>
        <span className="local">● Local play</span>
      </header>
      <section className="intro">
        <div>
          <p className="eyebrow">01 / XIANGQI</p>
          <h1>A meeting across the river.</h1>
          <p>Share the board, or play a local computer opponent.</p>
        </div>
        <button
          disabled={busy || !live}
          onClick={() => {
            cancelWork();
            setConfirmNew(true);
          }}
        >
          New game ↗
        </button>
      </section>
      {confirmNew && (
        <div className="notice">
          Start a fresh board? Export your current game first if you want to
          keep it. <button onClick={download}>Export game</button>
          <button
            disabled={busy}
            onClick={() => run((signal) => request("new", undefined, signal))}
          >
            Start new game
          </button>
          <button onClick={() => setConfirmNew(false)}>Cancel</button>
        </div>
      )}
      {error && (
        <div role="alert" className="notice error">
          {error}
          {!live && (
            <button
              disabled={busy}
              onClick={() => run((signal) => request("new", undefined, signal))}
            >
              Retry
            </button>
          )}
        </div>
      )}
      <div className="layout">
        <section className="board-panel" aria-label="Xiangqi board">
          <div className="board-top">
            <span>{flipped ? "RED · 紅方" : "BLACK · 黑方"}</span>
            <button className="quiet" onClick={() => setFlipped(!flipped)}>
              Flip board ⇅
            </button>
          </div>
          {!view ? (
            <p role="status">Preparing the board…</p>
          ) : (
            <svg
              viewBox="0 0 540 600"
              role="group"
              aria-label="Chinese chess board"
              className="board"
            >
              <rect
                x="0"
                y="0"
                width="540"
                height="600"
                rx="8"
                fill="#e9d6ae"
              />
              <g stroke="#81694b" strokeWidth="1" fill="none">
                {Array.from({ length: 10 }, (_, y) => (
                  <path key={`h${y}`} d={`M50 ${48 + y * 56}H498`} />
                ))}
                {Array.from({ length: 9 }, (_, x) => (
                  <path
                    key={`v${x}`}
                    d={
                      x === 0 || x === 8
                        ? `M${50 + x * 56} 48V552`
                        : `M${50 + x * 56} 48V272M${50 + x * 56} 328V552`
                    }
                  />
                ))}
                <path d="M218 48L330 160M330 48L218 160M218 440L330 552M330 440L218 552" />
              </g>
              <g fill="#8b714f" fontSize="20" textAnchor="middle">
                <text x="162" y="309">
                  楚 河
                </text>
                <text x="386" y="309">
                  漢 界
                </text>
              </g>
              {Array.from({ length: 9 }, (_, x) => (
                <text
                  key={x}
                  x={50 + x * 56}
                  y="588"
                  textAnchor="middle"
                  className="coordinate"
                >
                  {String.fromCharCode(97 + (flipped ? 8 - x : x))}
                </text>
              ))}
              {Array.from({ length: 10 }, (_, y) => (
                <text
                  key={y}
                  x="20"
                  y={53 + y * 56}
                  textAnchor="middle"
                  className="coordinate"
                >
                  {flipped ? y : 9 - y}
                </text>
              ))}
              {Array.from({ length: 90 }, (_, i) => {
                const x = 50 + (flipped ? 8 - (i % 9) : i % 9) * 56,
                  y =
                    48 +
                    (flipped ? Math.floor(i / 9) : 9 - Math.floor(i / 9)) * 56;
                const piece = view.board[i],
                  sq = coord(i),
                  active = selected === sq;
                const destination =
                  selected && view.legal_moves.includes(selected + sq);
                const last = view.snapshot.moves.at(-1);
                const recent =
                  last?.slice(0, 2) === sq || last?.slice(2) === sq;
                const label = `${sq}${piece === "." ? " empty" : ` ${color(piece)} ${names[piece.toUpperCase()]}`}${destination ? ", legal destination" : ""}`;
                return (
                  <g
                    key={i}
                    transform={`translate(${x},${y})`}
                    role="button"
                    tabIndex={
                      busy || thinking || opponentTurn || reviewing ? -1 : 0
                    }
                    aria-disabled={
                      busy ||
                      thinking ||
                      opponentTurn ||
                      reviewing ||
                      !!view.outcome ||
                      confirmNew
                    }
                    aria-label={label}
                    aria-pressed={active}
                    onClick={() => void choose(i)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        void choose(i);
                      }
                    }}
                    className="square"
                  >
                    <circle
                      r="26"
                      fill={recent ? "#c0a672" : "transparent"}
                      opacity="0.5"
                    />
                    {piece !== "." && (
                      <>
                        <circle
                          r="23"
                          fill="#f9ecd2"
                          stroke={active ? "#a4382d" : "#aa8b5a"}
                          strokeWidth={active ? 3 : 1.5}
                        />
                        <circle
                          r="19"
                          fill="none"
                          stroke={
                            color(piece) === "red" ? "#b54d3e" : "#484840"
                          }
                          opacity="0.5"
                        />
                        <text
                          y="9"
                          textAnchor="middle"
                          fontSize="28"
                          fill={color(piece) === "red" ? "#a4382d" : "#2b3532"}
                        >
                          {symbols[piece]}
                        </text>
                      </>
                    )}
                    {destination && (
                      <circle
                        r={piece === "." ? 7 : 25}
                        fill={piece === "." ? "#426954" : "none"}
                        stroke="#426954"
                        strokeWidth="3"
                      />
                    )}
                  </g>
                );
              })}
            </svg>
          )}
          <div className="board-bottom">
            <span>{flipped ? "BLACK · 黑方" : "RED · 紅方"}</span>
            <span>
              {opponent === "human"
                ? "Shared board · pass & play"
                : `You play ${humanSide}`}
            </span>
          </div>
        </section>
        <aside>
          <section className="opponent-controls" aria-label="Players">
            <label htmlFor="opponent">Opponent</label>
            <select
              id="opponent"
              value={opponent}
              disabled={busy}
              onChange={(e) => {
                cancelWork();
                setOpponent(e.target.value);
                setLastChoice(null);
              }}
            >
              <option value="human">Human · pass & play</option>
              {players.map((player) => (
                <option key={player.id} value={player.id}>
                  Computer · {player.label.toLowerCase()}
                </option>
              ))}
            </select>
            {catalogError && (
              <p role="alert">
                {catalogError}{" "}
                <button onClick={() => setCatalogRetry((n) => n + 1)}>
                  Retry player list
                </button>
              </p>
            )}
            {selectedPlayer && (
              <>
                <label htmlFor="human-side">You play</label>
                <select
                  id="human-side"
                  value={humanSide}
                  disabled={busy}
                  onChange={(e) => {
                    cancelWork();
                    setHumanSide(e.target.value as "red" | "black");
                    setLastChoice(null);
                  }}
                >
                  <option value="red">Red · moves first</option>
                  <option value="black">Black</option>
                </select>
                <p>
                  {selectedPlayer.description} Fixed seed.
                  {selectedPlayer.uses_search &&
                    ` Depth ${selectedPlayer.default_depth}, up to ${selectedPlayer.default_nodes} nodes.`}
                </p>
              </>
            )}
          </section>
          <section className="turn-card" aria-live="polite">
            <p className="eyebrow">{reviewing ? "REPLAY" : "AT THE BOARD"}</p>
            <h2>
              <i className={view?.turn ?? "red"} />
              {thinking ? "Computer is thinking…" : status}
            </h2>
            <p>
              {view?.outcome
                ? view.outcome.reason.replace("_", " ")
                : view?.in_check
                  ? "Check — protect your general."
                  : reviewing
                    ? "Viewing history. Return to the latest move to play."
                    : opponentTurn
                      ? thinking
                        ? "You can browse history or start a new game while it thinks."
                        : "The computer is waiting. Retry or change opponent."
                      : "Select a piece to see its legal moves."}
            </p>
            {opponentTurn &&
              !thinking &&
              !busy &&
              !reviewing &&
              !confirmNew &&
              error && (
                <button onClick={() => setRetry((n) => n + 1)}>
                  Retry opponent
                </button>
              )}
            {lastChoice && !reviewing && (
              <details>
                <summary>Last computer move</summary>
                <p>
                  {lastChoice.move} · {lastChoice.player_version}
                  <br />
                  {lastChoice.model_calls > 0
                    ? `${lastChoice.model_calls} model pass`
                    : `${lastChoice.nodes} nodes · depth ${lastChoice.completed_depth}`}{" "}
                  · {lastChoice.elapsed_ms.toFixed(0)} ms · seed{" "}
                  {lastChoice.seed}
                  {lastChoice.checkpoint_sha256 && (
                    <>
                      <br />
                      Checkpoint {lastChoice.checkpoint_sha256.slice(0, 12)}
                    </>
                  )}
                  {lastChoice.qnodes > 0 && (
                    <>
                      <br />
                      {lastChoice.qnodes} quiescence nodes · up to{" "}
                      {lastChoice.max_qply} extra plies
                    </>
                  )}
                </p>
              </details>
            )}
            <div className="meta">
              <span>MOVE HISTORY</span>
              <strong>
                {view?.ply ?? 0} <small>/ 300 plies</small>
              </strong>
            </div>
          </section>
          <section className="history">
            <div className="section-heading">
              <h3>The game so far</h3>
              <span>{live?.ply ?? 0} plies</span>
            </div>
            <div className="replay-controls">
              <button
                aria-label="Replay start"
                disabled={busy || !view || view.ply === 0}
                onClick={() => void review(0)}
              >
                ⇤
              </button>
              <button
                aria-label="Previous move"
                disabled={busy || !view || view.ply === 0}
                onClick={() => void review(view!.ply - 1)}
              >
                ←
              </button>
              <button
                aria-label="Next move"
                disabled={busy || !view || view.ply === live?.ply}
                onClick={() => void review(view!.ply + 1)}
              >
                →
              </button>
              <button
                aria-label="Latest move"
                disabled={busy || !live || view?.ply === live.ply}
                onClick={() => void review(live!.ply)}
              >
                ⇥
              </button>
            </div>
            <ol className="moves">
              {!live?.ply && (
                <p className="empty">
                  The first move is yours.
                  <br />
                  Red begins.
                </p>
              )}
              {live?.snapshot.moves.map((move, i) => (
                <li key={i}>
                  <button
                    className={view?.ply === i + 1 ? "current" : ""}
                    disabled={busy}
                    onClick={() => void review(i + 1)}
                  >
                    <span>{i + 1}</span>
                    <span>{i % 2 === 0 ? "Red" : "Black"}</span>
                    <strong>
                      {move.slice(0, 2)} → {move.slice(2)}
                    </strong>
                  </button>
                </li>
              ))}
            </ol>
          </section>
          <div className="file-actions">
            <button disabled={busy || !live} onClick={download}>
              Export game ↓
            </button>
            <button disabled={busy} onClick={() => file.current?.click()}>
              Import game ↑
            </button>
            <input
              ref={file}
              type="file"
              accept=".json,application/json"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f)
                  run(async (signal) => {
                    if (f.size > 100000)
                      throw new Error("Game file is too large.");
                    return request(
                      "inspect",
                      {
                        snapshot: JSON.parse(await f.text()),
                      },
                      signal,
                    );
                  });
              }}
            />
          </div>
          <details>
            <summary>About these rules</summary>
            <p>
              Standard piece movement. Repeating the same board and side to move
              three times draws, including checking or chasing loops. Games also
              draw at 300 plies; checkmate or stalemate takes precedence.
            </p>
            <p>
              Training rules: xiangqi-training-v1. Changes receive a new
              version.
            </p>
          </details>
        </aside>
      </div>
      <footer>
        <span>Built to play. Built to learn.</span>
        <span>象棋 / Chinese chess</span>
      </footer>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
