import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowLeft,
  ArrowRight,
  Pause,
  Play as PlayIcon,
  SkipForward,
} from "lucide-react";
import { Board, color, coord } from "./board";
import { ChoiceDetails } from "./choice-details";
import { Button } from "./components/ui/button";
import {
  download,
  request,
  type Controller,
  type Controllers,
  type PlayerInfo,
  type Position,
  type Choice,
} from "./api";
import { useSession } from "./session";
import { human } from "./session-state";
import { playersQuery } from "./queries";
import { RequestGate } from "./request-gate";
function ControllerForm({
  side,
  controller,
  players,
  disabled,
  onChange,
  onDirty,
}: {
  side: "red" | "black";
  controller: Controller;
  players: PlayerInfo[];
  disabled: boolean;
  onChange: (controller: Controller) => void;
  onDirty: (dirty: boolean) => void;
}) {
  const info = players.find((entry) => entry.id === controller.player);
  const [draft, setDraft] = useState<Record<string, string> | null>(null);
  useEffect(() => {
    setDraft(null);
    onDirty(false);
  }, [controller]);
  const original = Object.fromEntries(
    Object.entries(info?.settings ?? {}).map(([key, setting]) => [
      key,
      String(controller.settings[key] ?? setting.default),
    ]),
  );
  const values = draft ?? original;
  const valid = Object.entries(info?.settings ?? {}).every(([key, setting]) => {
    const value = Number(values[key]);
    const steps = (value - setting.minimum) / setting.step;
    return (
      values[key] !== "" &&
      Number.isFinite(value) &&
      value >= setting.minimum &&
      value <= setting.maximum &&
      Math.abs(steps - Math.round(steps)) < 1e-8
    );
  });
  const discard = () => {
    setDraft(null);
    onDirty(false);
  };
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (draft && valid)
          onChange({
            ...controller,
            settings: Object.fromEntries(
              Object.entries(draft).map(([key, value]) => [key, Number(value)]),
            ),
          });
      }}
    >
      <fieldset
        disabled={disabled}
        className={`controller card controller-${side}`}
      >
        <legend>{side === "red" ? "Red" : "Black"} player</legend>
        <label>
          Controller
          <select
            aria-label={`${side} player`}
            value={controller.player}
            onChange={(event) => {
              const selected = players.find(
                (entry) => entry.id === event.target.value,
              );
              discard();
              onChange(
                selected
                  ? {
                      player: selected.id,
                      binding_sha256: selected.binding_sha256,
                      checkpoint_sha256: selected.checkpoint_sha256,
                      settings: Object.fromEntries(
                        Object.entries(selected.settings).map(
                          ([key, setting]) => [key, setting.default],
                        ),
                      ),
                    }
                  : human(),
              );
            }}
          >
            <option value="human">Human</option>
            {!info && controller.player !== "human" && (
              <option value={controller.player}>
                {controller.player} (unavailable)
              </option>
            )}
            {players.map((entry) => (
              <option
                key={entry.id}
                value={entry.id}
                disabled={!entry.available}
              >
                {entry.label}
                {entry.available ? "" : " (unavailable)"}
              </option>
            ))}
          </select>
        </label>
        {info && (
          <>
            <p className="muted">{info.description}</p>
            {!info.available && (
              <p className="error">{info.unavailable_reason}</p>
            )}
            {info.available &&
              (info.binding_sha256 !== controller.binding_sha256 ||
                info.checkpoint_sha256 !== controller.checkpoint_sha256) && (
                <Button
                  type="button"
                  onClick={() =>
                    onChange({
                      ...controller,
                      binding_sha256: info.binding_sha256,
                      checkpoint_sha256: info.checkpoint_sha256,
                    })
                  }
                >
                  Use current {side} player identity
                </Button>
              )}
            {info.checkpoint_sha256 && (
              <p className="identity">
                Checkpoint {info.checkpoint_sha256.slice(0, 16)}
              </p>
            )}
            <div className="settings">
              {Object.entries(info.settings).map(([key, setting]) => (
                <label key={`${controller.player}-${key}`}>
                  {setting.label}
                  <input
                    aria-label={`${side} ${setting.label}`}
                    type="number"
                    min={setting.minimum}
                    max={setting.maximum}
                    step={setting.step}
                    required
                    value={values[key]}
                    onChange={(event) => {
                      const next = { ...values, [key]: event.target.value };
                      const dirty = Object.keys(next).some(
                        (key) => next[key] !== original[key],
                      );
                      setDraft(dirty ? next : null);
                      onDirty(dirty);
                    }}
                  />
                  <small>
                    {setting.unit} · {setting.minimum}–{setting.maximum}
                  </small>
                </label>
              ))}
            </div>
            {draft && (
              <div className="settings-actions">
                <p className="muted" role="status">
                  {valid
                    ? "Apply these settings before the next move."
                    : "Enter values within the shown limits."}
                </p>
                <div className="toolbar">
                  <Button
                    type="submit"
                    variant="default"
                    disabled={!valid}
                    aria-label={`Apply ${side} settings`}
                  >
                    Apply settings
                  </Button>
                  <Button
                    type="button"
                    onClick={discard}
                    aria-label={`Discard ${side} settings`}
                  >
                    Discard
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </fieldset>
    </form>
  );
}
export function PlayPage() {
  const game = useSession();
  const catalog = useQuery(playersQuery);
  const [selected, setSelected] = useState<string | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [view, setView] = useState<Position | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [viewError, setViewError] = useState("");
  const [dirtySettings, setDirtySettings] = useState({
    red: false,
    black: false,
  });
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const replayGate = useRef(new RequestGate());
  useEffect(
    () => () => {
      game.pause();
      replayGate.current.cancel();
    },
    [game.pause],
  );
  useEffect(() => {
    replayGate.current.cancel();
    setViewError("");
    setSelected(null);
    setView(null);
    setReplaying(false);
  }, [game.position]);
  if (!game.position || !game.session)
    return (
      <section>
        <h1>Play</h1>
        <p role="status">{game.error || "Loading the saved game…"}</p>
        <div className="toolbar">
          <Button disabled={game.busy} onClick={() => void game.restore()}>
            Retry restore
          </Button>
          {game.error && (
            <Button disabled={game.busy} onClick={() => void game.recover()}>
              Back up saved data and start new
            </Button>
          )}
        </div>
      </section>
    );
  const position = view ?? game.position;
  const controllers = game.session.controllers as Controllers;
  const mismatch = ["red", "black"].flatMap((side) => {
    const controller = controllers[side as "red" | "black"] as Controller;
    if (controller.player === "human") return [];
    const info = catalog.data?.find((entry) => entry.id === controller.player);
    return !info ||
      !info.available ||
      info.binding_sha256 !== controller.binding_sha256 ||
      info.checkpoint_sha256 !== controller.checkpoint_sha256
      ? [
          `${side}: saved player is unavailable or its resources changed. Select a player explicitly.`,
        ]
      : [];
  });
  const humanTurn = controllers[game.position.turn]?.player === "human";
  const blocked =
    game.busy ||
    dirtySettings.red ||
    dirtySettings.black ||
    replaying ||
    !!view ||
    game.conflict ||
    !!game.position.outcome;
  const chooseSquare = (index: number) => {
    if (blocked || !humanTurn || importOpen) return;
    const square = coord(index),
      piece = position.board[index];
    if (selected && position.legal_moves.includes(selected + square)) {
      void game.move(selected + square);
      setSelected(null);
    } else
      setSelected(
        piece !== "." && color(piece) === position.turn ? square : null,
      );
  };
  const replay = async (ply: number) => {
    game.pause();
    setViewError("");
    setSelected(null);
    const ticket = replayGate.current.start();
    if (ply === game.position!.ply) {
      setView(null);
      setReplaying(false);
      return;
    }
    setReplaying(true);
    try {
      const result = await request(
        "inspect",
        {
          snapshot: {
            ...game.session!.snapshot,
            moves: game.session!.snapshot.moves!.slice(0, ply),
          },
        },
        ticket.signal,
      );
      if (replayGate.current.isCurrent(ticket)) setView(result);
    } catch (error) {
      if (replayGate.current.isCurrent(ticket)) setViewError(String(error));
    } finally {
      if (replayGate.current.isCurrent(ticket)) setReplaying(false);
    }
  };
  const last = game.session.history.find((entry) => entry.ply === position.ply);
  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">THE BOARD</p>
          <h1>Play & explore</h1>
          <p className="muted">
            Choose each side. Pause to change future moves.
          </p>
        </div>
        <div className="heading-actions">
          <span className="badge">
            {game.position.outcome
              ? "Finished"
              : game.paused
                ? "Paused"
                : "Playing"}
          </span>
          <Button
            disabled={game.busy && !game.thinking}
            onClick={() => void game.replace()}
          >
            New game
          </Button>
        </div>
      </div>
      {(game.error || viewError || catalog.error) && (
        <p role="alert" className="error">
          {game.error || viewError || catalog.error?.message}
        </p>
      )}
      {game.conflict && (
        <Button onClick={() => void game.restore()}>Load saved session</Button>
      )}
      {mismatch.map((message) => (
        <p className="error" key={message}>
          {message}
        </p>
      ))}
      <Button size="sm" onClick={() => void catalog.refetch()}>
        Refresh players
      </Button>
      <div className="play-layout">
        <div>
          <div className="board-status" role="status">
            {position.outcome
              ? `${position.outcome.winner ? `${position.outcome.winner === "red" ? "Red" : "Black"} wins` : "Draw"} · ${position.outcome.reason}`
              : `${position.turn === "red" ? "Red" : "Black"} to move${position.in_check ? " · Check" : ""}`}{" "}
            · Ply {position.ply}
            {game.busy && (game.thinking ? " · Thinking…" : " · Updating…")}
            {view && " · Replay"}
          </div>
          <Board
            view={position}
            flipped={flipped}
            selected={selected}
            disabled={blocked || !humanTurn}
            keyboardDisabled={importOpen}
            onChoose={chooseSquare}
          />
          <div className="toolbar">
            <Button
              onClick={() => void replay(Math.max(0, position.ply - 1))}
              disabled={position.ply === 0}
              aria-label="Previous position"
            >
              <ArrowLeft size={16} />
            </Button>
            <input
              aria-label="Replay position"
              type="range"
              min={0}
              max={game.position.ply}
              value={position.ply}
              onChange={(event) => void replay(Number(event.target.value))}
            />
            <Button
              aria-label="Next position"
              onClick={() =>
                void replay(Math.min(game.position!.ply, position.ply + 1))
              }
              disabled={position.ply === game.position.ply}
            >
              <ArrowRight size={16} />
            </Button>
            <Button
              onClick={() => {
                replayGate.current.cancel();
                setView(null);
                setReplaying(false);
              }}
              disabled={!view && !replaying}
            >
              Live position
            </Button>
          </div>
          <div className="toolbar">
            <Button onClick={() => setFlipped(!flipped)}>Flip board</Button>
            <span className="muted">
              {selected
                ? `${selected} selected`
                : view
                  ? "Reviewing an earlier position."
                  : humanTurn
                    ? "Select a piece to see legal moves."
                    : "Step once, or Resume to play automatically."}
            </span>
          </div>
          {last?.choice ? (
            <ChoiceDetails choice={last.choice as Choice} />
          ) : (
            position.ply > 0 && (
              <p className="muted">
                {position.ply <= game.session.unknown_prefix
                  ? "Player attribution unknown for imported history."
                  : "Human move."}
              </p>
            )
          )}
        </div>
        <aside>
          <div className="toolbar">
            <Button
              variant="default"
              onClick={game.paused ? game.resume : game.pause}
              disabled={
                game.paused && (blocked || mismatch.length > 0 || !catalog.data)
              }
            >
              {game.paused ? <PlayIcon size={16} /> : <Pause size={16} />}
              {game.paused ? "Resume" : "Pause"}
            </Button>
            <Button
              onClick={() => void game.step()}
              disabled={
                !game.paused ||
                blocked ||
                humanTurn ||
                mismatch.length > 0 ||
                !catalog.data
              }
            >
              <SkipForward size={16} />
              Step
            </Button>
            {game.thinking && game.paused && (
              <Button onClick={game.pause}>Cancel move</Button>
            )}
          </div>
          {(["red", "black"] as const).map((side) => (
            <ControllerForm
              key={side}
              side={side}
              controller={controllers[side] as Controller}
              players={catalog.data ?? []}
              disabled={
                !game.paused || game.conflict || (game.busy && !game.thinking)
              }
              onDirty={(dirty) =>
                setDirtySettings((previous) =>
                  previous[side] === dirty
                    ? previous
                    : { ...previous, [side]: dirty },
                )
              }
              onChange={(controller) => void game.configure(side, controller)}
            />
          ))}
          <div className="card">
            <h2>Session</h2>
            <p className="muted">
              Saved locally after every accepted move. Restoring always pauses.
            </p>
            <div className="toolbar">
              <Button onClick={() => download("qi-session.json", game.session)}>
                Export session
              </Button>
              <Button
                onClick={() => download("qi-game.json", game.session!.snapshot)}
              >
                Export snapshot
              </Button>
            </div>
            <Dialog.Root
              open={importOpen}
              onOpenChange={(open) => {
                game.pause();
                setImportOpen(open);
              }}
            >
              <Dialog.Trigger asChild>
                <Button>Import</Button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="dialog-overlay" />
                <Dialog.Content className="dialog-content">
                  <Dialog.Title>Import a session or game snapshot</Dialog.Title>
                  <Dialog.Description>
                    Imported sessions are validated by the referee and restored
                    paused. A snapshot has unknown earlier player attribution.
                  </Dialog.Description>
                  <textarea
                    aria-label="Imported JSON"
                    value={importText}
                    onChange={(event) => setImportText(event.target.value)}
                    rows={10}
                  />
                  <div className="toolbar">
                    <Button
                      onClick={() => {
                        try {
                          void game.replace(JSON.parse(importText));
                          setImportOpen(false);
                        } catch {
                          setViewError("Import must be valid JSON.");
                        }
                      }}
                    >
                      Load JSON
                    </Button>
                    <Dialog.Close asChild>
                      <Button>Close</Button>
                    </Dialog.Close>
                  </div>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
          <details>
            <summary>Configuration history</summary>
            {game.session.changes.map((change, index) => (
              <p key={index}>
                After ply {change.ply}: Red {change.controllers.red?.player},
                Black {change.controllers.black?.player}
              </p>
            ))}
            <p className="muted">
              Mixed settings are exploratory play. Use the paired evaluation
              protocol for benchmarks.
            </p>
          </details>
        </aside>
      </div>
    </section>
  );
}
