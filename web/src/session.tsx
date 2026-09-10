import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import {
  request,
  type Controllers,
  type GameSession,
  type PlayResult,
  type Position,
  type Schema,
  type Controller,
} from "./api";
import { RequestGate } from "./request-gate";
import {
  appendMove,
  changeControllers,
  initialState,
  newSession,
  sessionReducer,
  type SessionState,
} from "./session-state";
export const SESSION_KEY = "qi.active-session.v1";
type Envelope = { revision: string; session: GameSession };
type Service = SessionState & {
  thinking: boolean;
  pause: () => void;
  resume: () => void;
  step: () => Promise<void>;
  move: (move: string) => Promise<void>;
  configure: (side: "red" | "black", controller: Controller) => Promise<void>;
  replace: (data?: unknown) => Promise<void>;
  restore: () => Promise<void>;
  recover: () => Promise<void>;
};
const SessionContext = createContext<Service | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(sessionReducer, initialState);
  const current = useRef(state);
  current.current = state;
  const gate = useRef(new RequestGate());
  const revision = useRef<string | null>(null);
  const active = useRef(false);
  const pause = useCallback(() => {
    gate.current.cancel();
    dispatch({ type: "pause" });
  }, []);
  const fail = (error: unknown) => {
    if (!(error instanceof DOMException && error.name === "AbortError"))
      dispatch({
        type: "error",
        error: error instanceof Error ? error.message : String(error),
      });
  };
  const stored = (): Envelope | null => {
    const data = localStorage.getItem(SESSION_KEY);
    if (!data) return null;
    const value = JSON.parse(data);
    if (!value || typeof value.revision !== "string" || !value.session)
      throw new Error(
        "The saved session has an invalid format. Back it up before starting a new game.",
      );
    return value;
  };
  const lock = async (work: () => Promise<void>) => {
    if (!navigator.locks)
      throw new Error(
        "This browser needs Web Locks to safely edit the shared session.",
      );
    await navigator.locks.request(SESSION_KEY, async () => {
      if ((stored()?.revision ?? null) !== revision.current) {
        dispatch({
          type: "error",
          error:
            "Another tab saved a newer session. Load its saved session before continuing.",
          conflict: true,
        });
        return;
      }
      await work();
    });
  };
  const persist = (session: GameSession, position?: Position) => {
    const next = crypto.randomUUID();
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ revision: next, session }),
    );
    revision.current = next;
    current.current = sessionReducer(current.current, {
      type: "saved",
      session,
      position,
    });
    dispatch({ type: "saved", session, position });
  };
  const restore = async () => {
    pause();
    const ticket = gate.current.start();
    dispatch({ type: "busy", busy: true });
    try {
      const value = stored();
      if (value) {
        const result = await request<Schema<"SessionResult">>(
          "play/session/inspect",
          value.session,
          ticket.signal,
        );
        if (!gate.current.isCurrent(ticket)) return;
        if (stored()?.revision !== value.revision) {
          dispatch({
            type: "error",
            error: "The saved session changed during restore. Load it again.",
            conflict: true,
          });
          return;
        }
        revision.current = value.revision;
        dispatch({
          type: "loaded",
          session: result.session as GameSession,
          position: result.position,
        });
      } else {
        const position = await request("new", undefined, ticket.signal);
        if (!gate.current.isCurrent(ticket)) return;
        revision.current = null;
        dispatch({ type: "loaded", session: newSession(position), position });
      }
    } catch (error) {
      if (gate.current.isCurrent(ticket)) fail(error);
    } finally {
      if (gate.current.isCurrent(ticket))
        dispatch({ type: "busy", busy: false });
    }
  };
  const recover = async () => {
    pause();
    const ticket = gate.current.start();
    dispatch({ type: "busy", busy: true });
    try {
      const original = localStorage.getItem(SESSION_KEY);
      if (!navigator.locks)
        throw new Error(
          "This browser needs Web Locks to safely edit the shared session.",
        );
      await navigator.locks.request(SESSION_KEY, async () => {
        if (localStorage.getItem(SESSION_KEY) !== original)
          throw new Error(
            "Another tab changed the saved data. Retry restore before replacing it.",
          );
        const position = await request("new", undefined, ticket.signal);
        if (!gate.current.isCurrent(ticket)) return;
        if (original)
          localStorage.setItem(
            `${SESSION_KEY}.backup.${crypto.randomUUID()}`,
            original,
          );
        const session = newSession(position);
        persist(session, position);
        dispatch({ type: "loaded", session, position });
      });
    } catch (error) {
      if (gate.current.isCurrent(ticket)) fail(error);
    } finally {
      if (gate.current.isCurrent(ticket))
        dispatch({ type: "busy", busy: false });
    }
  };
  useEffect(() => {
    void restore();
    const updated = (event: StorageEvent) => {
      if (event.key === SESSION_KEY) {
        pause();
        dispatch({
          type: "error",
          error: "Another tab changed the saved session. Load it to continue.",
          conflict: true,
        });
      }
    };
    const hidden = () => {
      if (document.visibilityState === "hidden") pause();
    };
    window.addEventListener("storage", updated);
    document.addEventListener("visibilitychange", hidden);
    window.addEventListener("pagehide", pause);
    return () => {
      gate.current.cancel();
      window.removeEventListener("storage", updated);
      document.removeEventListener("visibilitychange", hidden);
      window.removeEventListener("pagehide", pause);
    };
  }, [pause]);
  const advance = async (humanMove?: string) => {
    if (active.current || current.current.conflict) return;
    const { position, session } = current.current;
    if (!position || !session || position.outcome) return;
    const controller = session.controllers[position.turn] as Controller;
    if ((controller.player === "human") !== (humanMove !== undefined)) return;
    active.current = true;
    const ticket = gate.current.start();
    dispatch({ type: "busy", busy: true });
    try {
      await lock(async () => {
        if (!gate.current.isCurrent(ticket)) return;
        if (current.current.session !== session)
          throw new Error(
            "Session settings changed before this move. Step or Resume again.",
          );
        let next: Position, attribution: Schema<"SessionMove">;
        if (humanMove) {
          next = await request(
            "apply",
            {
              snapshot: position.snapshot,
              expected_state_hash: position.state_hash,
              move: humanMove,
            },
            ticket.signal,
          );
          attribution = {
            ply: next.ply,
            side: position.turn,
            controller,
            choice: null,
            config: null,
          };
        } else {
          const result = await request<PlayResult>(
            "play/choose",
            {
              snapshot: position.snapshot,
              expected_state_hash: position.state_hash,
              controller,
            },
            ticket.signal,
          );
          next = result.position;
          if (result.choice.state_hash !== position.state_hash)
            throw new Error("Player response refers to a stale position.");
          attribution = {
            ply: next.ply,
            side: position.turn,
            controller,
            choice: result.choice,
            config: result.config,
          };
        }
        if (
          gate.current.isCurrent(ticket) &&
          current.current.position?.state_hash === position.state_hash
        )
          persist(appendMove(session, next, attribution), next);
      });
    } catch (error) {
      if (gate.current.isCurrent(ticket)) fail(error);
    } finally {
      active.current = false;
      if (gate.current.isCurrent(ticket))
        dispatch({ type: "busy", busy: false });
    }
  };
  useEffect(() => {
    if (
      !state.paused &&
      !state.busy &&
      state.position &&
      !state.position.outcome &&
      state.session?.controllers[state.position.turn]?.player !== "human"
    ) {
      const timer = setTimeout(() => void advance(), 150);
      return () => clearTimeout(timer);
    }
  }, [state.paused, state.busy, state.position, state.session]);
  const configure = async (side: "red" | "black", controller: Controller) => {
    pause();
    dispatch({ type: "busy", busy: true });
    try {
      await lock(async () => {
        const validated = await request<Controller>(
          "play/controller/inspect",
          controller,
        );
        if (current.current.session)
          persist(
            changeControllers(current.current.session, {
              ...current.current.session.controllers,
              [side]: validated,
            } as Controllers),
          );
      });
    } catch (error) {
      fail(error);
    } finally {
      dispatch({ type: "busy", busy: false });
    }
  };
  const replace = async (data?: unknown) => {
    pause();
    dispatch({ type: "busy", busy: true });
    const ticket = gate.current.start();
    try {
      await lock(async () => {
        let session: GameSession, position: Position;
        if (data && typeof data === "object" && "format" in data) {
          const result = await request<Schema<"SessionResult">>(
            "play/session/inspect",
            data,
            ticket.signal,
          );
          session = result.session as GameSession;
          position = result.position;
        } else {
          position = data
            ? await request("inspect", { snapshot: data }, ticket.signal)
            : await request("new", undefined, ticket.signal);
          session = newSession(position);
        }
        if (!gate.current.isCurrent(ticket)) return;
        persist(session, position);
        dispatch({ type: "loaded", session, position });
      });
    } catch (error) {
      if (gate.current.isCurrent(ticket)) fail(error);
    } finally {
      if (gate.current.isCurrent(ticket))
        dispatch({ type: "busy", busy: false });
    }
  };
  return (
    <SessionContext
      value={{
        ...state,
        thinking: active.current,
        pause,
        resume: () => dispatch({ type: "resume" }),
        step: () => advance(),
        move: (move) => advance(move),
        configure,
        replace,
        restore,
        recover,
      }}
    >
      {children}
    </SessionContext>
  );
}
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("Session provider missing");
  return value;
}
