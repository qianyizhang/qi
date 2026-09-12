import { useEffect, useRef, useState } from "react";
import { Bookmark } from "lucide-react";
import { Button } from "./components/ui/button";
import {
  parseReview,
  reviewPrefix,
  type Review,
  type ReviewStatus,
} from "./data-review";
import type { Game } from "./data-format";

type Draft = { status: ReviewStatus; note: string; base: string | null };
// Tab-local drafts outlive inspector and route changes, but never change saved reviews.
const drafts = new Map<string, Draft>();

export function ReviewEditor({
  collection,
  game,
  ply,
  saved,
  blocked,
  onSave,
}: {
  collection: string;
  game: Game;
  ply: number;
  saved?: Review;
  blocked: boolean;
  onSave: () => void;
}) {
  const key = reviewPrefix(collection) + game.attempt;
  const draftKey = `${key}:${game.trajectory}`;
  const [draft, setDraft] = useState<Draft>(() => {
    const existing = drafts.get(draftKey);
    if (existing) return existing;
    let base = null;
    let review = saved;
    try {
      base = localStorage.getItem(key);
      review = parseReview(base, game.attempt);
      if (review?.trajectory !== game.trajectory) review = undefined;
    } catch {
      /* Saving remains blocked. */
    }
    return {
      status: review?.status ?? "inspect",
      note: review?.note ?? "",
      base,
    };
  });
  const [conflict, setConflict] = useState<{ raw: string | null } | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const active = useRef(false);
  const update = (next: Draft) => {
    drafts.set(draftKey, next);
    setDraft(next);
  };
  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw !== draft.base) setConflict({ raw });
    } catch {
      setMessage("Browser storage is unavailable. Your draft remains here.");
    }
  }, [key, saved, draft.base]);
  const loadSaved = () => {
    try {
      const raw = localStorage.getItem(key);
      const review = parseReview(raw, game.attempt);
      if (review && review.trajectory !== game.trajectory)
        throw new Error("The saved review belongs to different game evidence.");
      update({
        status: review?.status ?? "inspect",
        note: review?.note ?? "",
        base: raw,
      });
      setConflict(null);
      setMessage(
        review
          ? "Loaded the latest saved review."
          : "The saved review was removed. Loaded an empty draft.",
      );
      onSave();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not read saved review.",
      );
    }
  };
  const save = async (remove = false, overwrite = false) => {
    if (blocked || active.current || (conflict && !overwrite)) return;
    active.current = true;
    setPending(true);
    setMessage("");
    // An overwrite accepts only the revision the user saw. A further change
    // while waiting for the shared lock requires another explicit choice.
    const expected = overwrite && conflict ? conflict.raw : draft.base;
    try {
      if (!navigator.locks)
        throw new Error(
          "This browser needs Web Locks to safely save shared reviews.",
        );
      await navigator.locks.request(key, () => {
        const raw = localStorage.getItem(key);
        const current = parseReview(raw, game.attempt);
        if (current && current.trajectory !== game.trajectory)
          throw new Error(
            "The saved review belongs to different game evidence.",
          );
        if (raw !== expected) {
          setConflict({ raw });
          return;
        }
        const review: Review = {
          attempt: game.attempt,
          game_id: game.id,
          trajectory: game.trajectory,
          status: draft.status,
          note: draft.note,
          ply,
          updated: new Date().toISOString(),
        };
        const next = remove ? null : JSON.stringify(review);
        if (next === null) localStorage.removeItem(key);
        else localStorage.setItem(key, next);
        update({ ...draft, base: next });
        setConflict(null);
        setMessage(
          remove
            ? "Review removed. Your draft remains here."
            : "Review saved in this browser.",
        );
        onSave();
      });
    } catch (error) {
      setMessage(
        `${error instanceof Error ? error.message : "Could not save review."} Your draft remains here.`,
      );
    } finally {
      active.current = false;
      setPending(false);
    }
  };
  return (
    <div className="review-editor">
      <h3>
        <Bookmark size={15} /> Review this game
      </h3>
      <div className="review-options">
        {(["keep", "inspect", "exclude"] as const).map((status) => (
          <button
            key={status}
            className={`review-${status}`}
            aria-pressed={draft.status === status}
            disabled={pending}
            onClick={() => update({ ...draft, status })}
          >
            {status === "keep"
              ? "Keep example"
              : status === "inspect"
                ? "Inspect later"
                : "Exclude candidate"}
          </button>
        ))}
      </div>
      <label>
        Review note
        <textarea
          rows={3}
          maxLength={4000}
          value={draft.note}
          disabled={pending}
          onChange={(event) => update({ ...draft, note: event.target.value })}
          placeholder="What makes this game useful, unusual, or unsuitable?"
        />
      </label>
      {conflict && (
        <div className="card">
          <p role="alert">
            Another tab changed this saved review. Your draft is preserved. Load
            the saved review or explicitly overwrite it with this draft.
          </p>
          <div className="toolbar">
            <Button onClick={loadSaved} disabled={blocked || pending}>
              Load saved review
            </Button>
            <Button
              onClick={() => void save(false, true)}
              disabled={blocked || pending || game.status === "running"}
            >
              Overwrite with my draft
            </Button>
          </div>
        </div>
      )}
      <div className="toolbar">
        <Button
          onClick={() => void save()}
          disabled={
            blocked || pending || !!conflict || game.status === "running"
          }
        >
          Save review at ply {ply}
        </Button>
        {saved && (
          <Button
            variant="ghost"
            disabled={blocked || pending || !!conflict}
            onClick={() => void save(true)}
          >
            Clear review
          </Button>
        )}
      </div>
      <p className="muted">
        Browser shortlist only. Exclude is a review suggestion; training
        selection and source evidence are unchanged.
      </p>
      {game.status === "running" && (
        <p className="muted">Review after this attempt is finalized.</p>
      )}
      {pending && <p role="status">Saving review…</p>}
      {message && <p role="status">{message}</p>}
    </div>
  );
}
