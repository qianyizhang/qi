import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Shuffle, GitBranch, Sparkles, Check } from "lucide-react";
import { Term } from "./reference";
import { Button } from "./components/ui/button";
import { number } from "./data-format";
import type { Example } from "./generation-lesson";

export function Takeaway({ children }: { children: ReactNode }) {
  return (
    <div className="lesson-takeaway">
      <span>THE IDEA TO KEEP</span>
      <p>{children}</p>
    </div>
  );
}
export function ActorLesson({ example }: { example: Example }) {
  const [mode, setMode] = useState<"plausible" | "random" | "intervention">(
    "plausible",
  );
  const choices = [
    {
      id: "plausible",
      title: "Plausible",
      icon: Sparkles,
      detail: "Vary among teacher-supported candidates",
    },
    {
      id: "random",
      title: "Random",
      icon: Shuffle,
      detail: "Pick uniformly from all legal moves",
    },
    {
      id: "intervention",
      title: "Intervention",
      icon: GitBranch,
      detail: "Insert one non-best move into teacher play",
    },
  ] as const;
  return (
    <>
      <div className="lesson-choice-grid" aria-label="Actor policies">
        {choices.map(({ id, title, detail, icon: Icon }) => (
          <button
            key={id}
            aria-pressed={mode === id}
            onClick={() => setMode(id)}
          >
            <Icon size={21} />
            <strong>{title}</strong>
            <small>{detail}</small>
          </button>
        ))}
      </div>
      <div className="lesson-demo" aria-live="polite">
        {mode === "plausible" && (
          <>
            <p className="eyebrow">
              ILLUSTRATIVE CANDIDATES · NOT SCORES FROM THIS GAME
            </p>
            <h3>Give variety a quality boundary</h3>
            <div className="lesson-candidates">
              {[
                { name: "Move A", score: 50, eligible: true },
                { name: "Move B", score: 25, eligible: true },
                { name: "Move C", score: -40, eligible: false },
              ].map((c) => (
                <div key={c.name} className={c.eligible ? "eligible" : ""}>
                  <strong>{c.name}</strong>
                  <span>
                    {c.score > 0 ? "+" : ""}
                    {c.score} cp
                  </span>
                  <small>
                    {c.eligible
                      ? "Eligible · 1 in 2 chance"
                      : "90 cp behind · outside gap"}
                  </small>
                </div>
              ))}
            </div>
            <p>
              This batch asks for up to{" "}
              <b>{example.actor.candidate_count} candidates</b> and allows a{" "}
              <b>{example.actor.max_cp_gap} cp gap</b> from the best. In this
              illustration, A and B qualify; the actor chooses either with equal
              probability.
            </p>
            <p className="muted">
              cp means engine centipawns: a score scale, not a win probability.
              Candidate scores must be compatible, exact, and from a common
              search depth. Incomplete or mate evidence triggers a recorded
              teacher-best fallback.
            </p>
          </>
        )}
        {mode === "random" && (
          <>
            <p className="eyebrow">ILLUSTRATION · FOUR LEGAL CHOICES</p>
            <h3>Every legal move has the same chance</h3>
            <div className="lesson-random">
              {["A", "B", "C", "D"].map((m) => (
                <div key={m}>
                  <strong>{m}</strong>
                  <span>25%</span>
                </div>
              ))}
            </div>
            <p>
              The actor does not ask the engine to rank moves. If a position has
              40 legal moves, each has a 1-in-40 chance instead.
            </p>
            <p className="muted">
              “Random” describes how the game was played. Its selected positions
              still receive teacher analyses later.
            </p>
          </>
        )}
        {mode === "intervention" && (
          <>
            <p className="eyebrow">RECORDED GAME #{example.game_id}</p>
            <h3>Change one move, then let play continue</h3>
            <div className="lesson-flow">
              <div>
                Teacher-best<small>plies 0–29</small>
              </div>
              <ArrowRight aria-hidden />
              <div className="intervention">
                Non-best legal move
                <small>
                  at ply {example.intervention_ply}:{" "}
                  {example.snapshot.moves[example.intervention_ply]}
                </small>
              </div>
              <ArrowRight aria-hidden />
              <div>
                Teacher-best<small>at ply 31: b9b1</small>
              </div>
            </div>
            <p>
              A seeded choice picks an intervention ply between{" "}
              <b>
                {example.actor.intervention_min_ply} and{" "}
                {example.actor.intervention_max_ply}
              </b>
              . At that point the actor chooses uniformly among legal moves
              other than the teacher’s best, then resumes teacher-best play.
            </p>
            <p className="muted">
              Here it happened at ply 30. In another game, early termination or
              no alternative legal move could leave it unapplied. “Intervention”
              alone does not tell us how serious the mistake was.
            </p>
          </>
        )}
      </div>
      <p className="lesson-margin-note">
        Before play, the recipe also fixes starting positions, seeds, move
        limits, teacher settings and source-family splits. <b>Train</b> supplies
        learning examples; <b>validation</b> checks performance on held-out
        inputs. These labels are separate from actor policy.
      </p>
      <Takeaway>
        The <Term name="Player">actor</Term> makes the game’s moves. The{" "}
        <Term name="Teacher supervision">teacher</Term> also provides advice
        used as labels. Those are two different jobs, even when the same engine
        does both.
      </Takeaway>
    </>
  );
}

export function QualityLesson({ example }: { example: Example }) {
  const [identity, setIdentity] = useState("input");
  const [filtered, setFiltered] = useState(false);
  const batch = example.batch;
  return (
    <>
      <div className="lesson-demo">
        <p className="eyebrow">RECORDED BATCH · {example.captured}</p>
        <h3>First, read the denominator</h3>
        <div
          className="lesson-segment"
          aria-label="Illustrate dashboard filters"
        >
          <button aria-pressed={!filtered} onClick={() => setFiltered(false)}>
            Whole batch
          </button>
          <button aria-pressed={filtered} onClick={() => setFiltered(true)}>
            Endgame sampling gaps
          </button>
        </div>
        <div className="lesson-denominator" aria-live="polite">
          <strong>
            {number(filtered ? batch.endgame_shortfall_games : batch.accepted)}
          </strong>
          <span>
            accepted games
            {filtered
              ? " matching these filters"
              : ` out of ${number(batch.attempts)} attempts`}
          </span>
        </div>
        <p>
          {filtered
            ? `The sampling-gap filter shows ${number(batch.endgame_shortfall_games)} accepted games with unfilled endgame targets. The remaining accepted games are outside this view; they were not rejected.`
            : `The batch retained ${number(batch.accepted)} accepted games and ${number(batch.rejected)} rejected attempts. The accepted status describes generation completion, not final training eligibility.`}
        </p>
      </div>
      <h3>Then ask: “The same” in what sense?</h3>
      <div className="lesson-choice-grid" aria-label="Identity levels">
        {[
          {
            id: "trajectory",
            title: "Full trajectory",
            detail: "The entire replay",
          },
          {
            id: "occurrence",
            title: "Position occurrence",
            detail: "This game, at this ply",
          },
          {
            id: "input",
            title: "Learner input",
            detail: "What the model sees",
          },
        ].map((i) => (
          <button
            key={i.id}
            aria-pressed={identity === i.id}
            onClick={() => setIdentity(i.id)}
          >
            <strong>{i.title}</strong>
            <small>{i.detail}</small>
          </button>
        ))}
      </div>
      <div className="lesson-demo" aria-live="polite">
        {identity === "trajectory" && (
          <>
            <div className="lesson-identity-pair">
              <span>
                Game #{example.game_id}
                <small>train</small>
              </span>
              <b>= same moves =</b>
              <span>
                Game #{example.duplicate_games[0]}
                <small>train</small>
              </span>
            </div>
            <p>
              “Same accepted full trajectory” links other game records with
              exactly the same complete replay. Repeated attempts within the
              same split are retained as evidence.
            </p>
            <p>
              A completed trajectory already accepted in the opposite split is
              rejected. That protects against copying a whole game across train
              and validation.
            </p>
          </>
        )}
        {identity === "occurrence" && (
          <>
            <div className="lesson-identity-pair">
              <span>
                Game #6286<small>history through ply 17</small>
              </span>
              <ArrowRight aria-hidden />
              <span>
                One occurrence<small>board + provenance</small>
              </span>
            </div>
            <p>
              A <Term name="Position occurrence" /> remembers where a position
              appeared: which game, which ply and which replay history. Two
              occurrences may show the same board while keeping different
              histories or sources.
            </p>
            <p>
              The selected-position count counts these occurrences, before
              dataset-wide deduplication.
            </p>
          </>
        )}
        {identity === "input" && (
          <>
            <div className="lesson-identity-pair">
              <span>
                Train occurrence<small>board + side to move</small>
              </span>
              <b>= same input =</b>
              <span>
                Validation occurrence<small>board + side to move</small>
              </span>
            </div>
            <p>
              The current learner encodes the board and side to move. It does
              not encode the full replay history. Different games can therefore
              give it the same input.
            </p>
            <p>
              The batch audit found{" "}
              <b>
                {number(batch.shared_inputs)} distinct inputs in both splits
              </b>
              . Hashes were present: hashing identifies a match; a selection
              policy must decide what to exclude. Full-trajectory rejection
              alone cannot catch every shared intermediate input.
            </p>
          </>
        )}
      </div>
      <Takeaway>
        Check three things separately: generation acceptance, phase coverage,
        and independence of learner inputs. A sampling shortfall does not reject
        a game; a stored hash does not automatically remove duplicates.
      </Takeaway>
    </>
  );
}

export function DatasetLesson({
  example,
  onStep,
}: {
  example: Example;
  onStep: (step: number) => void;
}) {
  return (
    <>
      <div className="lesson-freeze">
        {[
          {
            n: "01",
            title: "Retain the evidence",
            detail:
              "Keep games, selected occurrences and analysis attempts in the collection. Their history and identities stay available for inspection.",
          },
          {
            n: "02",
            title: "Apply a selection recipe",
            detail:
              "Choose sources, quotas and an exact supervision specification. Enforce reserved-input exclusions, deduplication and train/validation isolation; require eligible successful analyses.",
          },
          {
            n: "03",
            title: "Freeze and verify",
            detail:
              "Export an immutable snapshot of the chosen examples, labels and replay evidence. Verify the selection against its recipe so the dataset can be reproduced.",
          },
          {
            n: "04",
            title: "Prepare inputs and train",
            detail:
              "A trainer encodes each eligible position and uses the chosen teacher move as a target. Updating model weights is a separate operation.",
          },
        ].map((item) => (
          <div key={item.n}>
            <span>{item.n}</span>
            <div>
              <h3>{item.title}</h3>
              <p>{item.detail}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="lesson-demo">
        <h3>What is one training example?</h3>
        <div className="lesson-flow">
          <div>
            <Term name="Position" />
            <small>board + side to move</small>
          </div>
          <span>+</span>
          <div>
            Chosen teacher label<small>one explicit specification</small>
          </div>
          <ArrowRight aria-hidden />
          <div>
            Input / target pair<small>with provenance retained</small>
          </div>
        </div>
        <p>
          Game #{example.game_id} has 6 selected occurrences and 12 supervision
          analyses. That does <b>not</b> automatically make 12 independent
          training inputs. The recipe determines which evidence is eligible and
          which label to use.
        </p>
      </div>
      <Takeaway>
        <Term name="Dataset preparation" /> covers this whole journey:
        generating trajectories, providing supervision, and freezing a selected
        dataset. The browser review shortlist expresses your curation intent; a
        frozen selection makes that intent part of a reproducible dataset.
      </Takeaway>
      <h3>Connect this back to the Data page</h3>
      <div className="lesson-recap">
        {[
          [
            6,
            "Why do I see only 4,398 accepted games?",
            "You are looking at a filtered group.",
          ],
          [
            1,
            "Plausible, random, intervention?",
            "Different actor policies for choosing moves.",
          ],
          [
            3,
            "Opening, middlegame, endgame?",
            "Board-based categories under an explicit heuristic.",
          ],
          [
            6,
            "949 shared inputs, and the linked game IDs?",
            "Input overlap and repeated full trajectories are different.",
          ],
          [
            4,
            "Selected positions, and selected / gap?",
            "Retained occurrences and unfilled per-phase targets.",
          ],
          [
            5,
            "Why does the score chart have so few points?",
            "It only plots exact centipawn evidence.",
          ],
        ].map(([step, title, detail]) => (
          <button key={title} onClick={() => onStep(Number(step))}>
            <Check size={17} />
            <span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </span>
            <ArrowRight size={16} />
          </button>
        ))}
      </div>
      <div className="toolbar">
        <Button variant="default" asChild>
          <Link to="/data">
            Explore the batch
            <ArrowRight size={16} />
          </Link>
        </Button>
        <Button asChild>
          <Link to="/reference">Browse all definitions</Link>
        </Button>
      </div>
    </>
  );
}
