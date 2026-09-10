import type {
  Controller,
  Controllers,
  GameSession,
  Position,
  Schema,
} from "./api";
export const human = (): Controller => ({
  player: "human",
  settings: {},
  binding_sha256: null,
  checkpoint_sha256: null,
});
export function newSession(position: Position): GameSession {
  const controllers = { red: human(), black: human() };
  return {
    format: "qi-game-session",
    schema_version: 1,
    snapshot: position.snapshot,
    controllers,
    unknown_prefix: position.ply,
    changes: [{ ply: position.ply, controllers }],
    history: [],
  };
}
export function changeControllers(
  session: GameSession,
  controllers: Controllers,
): GameSession {
  if (session.changes.length >= 2000)
    throw new Error(
      "This session reached its configuration-change limit. Export it before starting a new game.",
    );
  return {
    ...session,
    controllers,
    changes: [
      ...session.changes,
      { ply: session.snapshot.moves!.length, controllers },
    ],
  };
}
export function appendMove(
  session: GameSession,
  position: Position,
  move: Schema<"SessionMove">,
): GameSession {
  return {
    ...session,
    snapshot: position.snapshot,
    history: [...session.history, move],
  };
}
export type SessionState = {
  session: GameSession | null;
  position: Position | null;
  paused: boolean;
  busy: boolean;
  error: string;
  conflict: boolean;
};
export const initialState: SessionState = {
  session: null,
  position: null,
  paused: true,
  busy: false,
  error: "",
  conflict: false,
};
export type SessionAction =
  | { type: "loaded"; session: GameSession; position: Position }
  | { type: "saved"; session: GameSession; position?: Position }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "busy"; busy: boolean }
  | { type: "error"; error: string; conflict?: boolean };
export function sessionReducer(
  state: SessionState,
  action: SessionAction,
): SessionState {
  switch (action.type) {
    case "loaded":
      return {
        ...initialState,
        session: action.session,
        position: action.position,
      };
    case "saved":
      return {
        ...state,
        session: action.session,
        position: action.position ?? state.position,
        error: "",
      };
    case "pause":
      return { ...state, paused: true, busy: false };
    case "resume":
      return state.conflict ? state : { ...state, paused: false, error: "" };
    case "busy":
      return { ...state, busy: action.busy };
    case "error":
      return {
        ...state,
        paused: true,
        busy: false,
        error: action.error,
        conflict: action.conflict ?? state.conflict,
      };
  }
}
