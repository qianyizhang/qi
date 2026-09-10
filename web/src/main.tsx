import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { RequestGate } from "./request-gate";
import {
  request,
  type Choice,
  type OpponentResult,
  type PlayerInfo,
  type Position,
} from "./api";
import { Board, color, coord } from "./board";
import { ChoiceDetails } from "./choice-details";

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
            rollout_plies: selectedPlayer.default_rollout_plies ?? 8,
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
            <Board
              view={view}
              flipped={flipped}
              selected={selected}
              keyboardDisabled={busy || thinking || opponentTurn || reviewing}
              disabled={
                busy ||
                thinking ||
                opponentTurn ||
                reviewing ||
                !!view.outcome ||
                confirmNew
              }
              onChoose={choose}
            />
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
                    (selectedPlayer.default_rollout_plies != null
                      ? ` Up to ${selectedPlayer.default_nodes} visits; rollouts up to ${selectedPlayer.default_rollout_plies} plies.`
                      : ` Depth ${selectedPlayer.default_depth}, up to ${selectedPlayer.default_nodes} nodes.`)}
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
            {lastChoice && !reviewing && <ChoiceDetails choice={lastChoice} />}
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
