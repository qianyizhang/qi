import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

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
async function request(path: string, data?: unknown): Promise<Position> {
  const response = await fetch(`/api/${path}`, {
    method: "POST",
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
  const file = useRef<HTMLInputElement>(null);
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load game.");
    } finally {
      setBusy(false);
    }
  }
  function accept(p: Position) {
    setLive(p);
    setView(p);
    setSelected(null);
    setConfirmNew(false);
  }
  useEffect(() => {
    void run(async () => accept(await request("new")));
  }, []);
  const reviewing = !!(view && live && view.ply !== live.ply);
  async function choose(i: number) {
    if (!view || !live || busy || reviewing || view.outcome) return;
    const target = coord(i),
      move = selected ? selected + target : "";
    if (view.legal_moves.includes(move)) {
      await run(async () =>
        accept(
          await request("apply", {
            snapshot: live.snapshot,
            move,
            expected_state_hash: live.state_hash,
          }),
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
  async function review(ply: number) {
    if (!live) return;
    await run(async () => {
      setView(
        await request("inspect", {
          snapshot: {
            ...live.snapshot,
            moves: live.snapshot.moves.slice(0, ply),
          },
        }),
      );
      setSelected(null);
    });
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
          <p>Two players. One board. Take your time.</p>
        </div>
        <button disabled={busy || !live} onClick={() => setConfirmNew(true)}>
          New game ↗
        </button>
      </section>
      {confirmNew && (
        <div className="notice">
          Start a fresh board? Export your current game first if you want to
          keep it. <button onClick={download}>Export game</button>
          <button
            disabled={busy}
            onClick={() => void run(async () => accept(await request("new")))}
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
              onClick={() => void run(async () => accept(await request("new")))}
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
                    tabIndex={busy ? -1 : 0}
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
            <span>Shared board · pass & play</span>
          </div>
        </section>
        <aside>
          <section className="turn-card" aria-live="polite">
            <p className="eyebrow">{reviewing ? "REPLAY" : "AT THE BOARD"}</p>
            <h2>
              <i className={view?.turn ?? "red"} />
              {status}
            </h2>
            <p>
              {view?.outcome
                ? view.outcome.reason.replace("_", " ")
                : view?.in_check
                  ? "Check — protect your general."
                  : reviewing
                    ? "Viewing history. Return to the latest move to play."
                    : "Select a piece to see its legal moves."}
            </p>
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
                  void run(async () => {
                    if (f.size > 100000)
                      throw new Error("Game file is too large.");
                    const p = await request("inspect", {
                      snapshot: JSON.parse(await f.text()),
                    });
                    accept(p);
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
