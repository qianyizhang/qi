import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  BookOpen,
  RotateCcw,
} from "lucide-react";
import { read, type Schema } from "./api";
import { glossaryQuery } from "./queries";
import { GlossaryContext } from "./reference";
import { Button } from "./components/ui/button";
import {
  ActorLesson,
  QualityLesson,
  DatasetLesson,
} from "./generation-concepts";
import {
  ReplayLesson,
  SamplingLesson,
  SupervisionLesson,
} from "./generation-example";
import "./generation-lesson.css";

export type Example = Schema<"GenerationLesson">["example"] & {
  snapshot: Required<Schema<"Snapshot">>;
};
export type Lesson = Omit<Schema<"GenerationLesson">, "example"> & {
  example: Example;
};
export const steps = [
  {
    short: "Choose a policy",
    title: "Decide how the moves will be chosen",
    subtitle:
      "A policy controls the actor: the player making each move in a generated game.",
  },
  {
    short: "Play a game",
    title: "One move at a time becomes a trajectory",
    subtitle:
      "The actor proposes a legal move. The referee applies it and checks whether the game has ended.",
  },
  {
    short: "Recognize phases",
    title: "Read the board, not the move number",
    subtitle:
      "Opening, middlegame and endgame are computed from the pieces on the board.",
  },
  {
    short: "Sample positions",
    title: "Keep a few useful stopping points",
    subtitle:
      "Sampling chooses positions from the completed trajectory, using phase targets and spacing.",
  },
  {
    short: "Ask the teacher",
    title: "One position can have several analyses",
    subtitle:
      "At each selected position, ask the teacher what it would play with each configured search budget.",
  },
  {
    short: "Check quality",
    title: "Accepted games still need an input audit",
    subtitle:
      "A complete game, a unique trajectory and an independent learner input answer different questions.",
  },
  {
    short: "Freeze a dataset",
    title: "Turn retained evidence into training examples",
    subtitle:
      "An explicit selection recipe chooses eligible inputs and labels; a frozen snapshot records that decision.",
  },
] as const;

export function parseLessonSearch(search: Record<string, unknown>): {
  step?: number;
} {
  const value = Number(search.step);
  return {
    step:
      Number.isInteger(value) && value >= 1 && value <= steps.length
        ? value
        : 1,
  };
}

export function GenerationLessonPage({
  step,
  onStep,
}: {
  step: number;
  onStep: (step: number) => void;
}) {
  const lesson = useQuery({
    queryKey: ["generation-lesson"],
    queryFn: ({ signal }) => read<Lesson>("learn/generation", signal),
    staleTime: Infinity,
    retry: false,
  });
  const glossary = useQuery(glossaryQuery);
  const heading = useRef<HTMLHeadingElement>(null);
  const previousStep = useRef(step);
  useEffect(() => {
    if (previousStep.current !== step) {
      heading.current?.focus({ preventScroll: true });
      heading.current?.scrollIntoView({ block: "start", behavior: "instant" });
      previousStep.current = step;
    }
  }, [step]);
  const current = steps[step - 1];
  const data = lesson.data;
  return (
    <GlossaryContext.Provider value={glossary.data ?? null}>
      <section className="generation-lesson">
        <header className="lesson-heading">
          <div>
            <p className="eyebrow">A GUIDED WALK THROUGH THE DATA</p>
            <h1>From game to training example</h1>
            <p>
              Follow one real game. Move the board, try the sampler, and learn
              what the numbers mean.
            </p>
          </div>
          <Link to="/data" className="lesson-back">
            <ArrowLeft size={16} /> Data workspace
          </Link>
        </header>
        <div
          className="lesson-journey"
          aria-label="The stages of sample generation"
        >
          <span>Play a game</span>
          <ArrowRight aria-hidden size={18} />
          <span>Sample positions</span>
          <ArrowRight aria-hidden size={18} />
          <span>Retain teacher evidence</span>
          <ArrowRight aria-hidden size={18} />
          <span>Select a dataset</span>
        </div>
        <div className="lesson-layout">
          <aside className="lesson-sidebar">
            <nav aria-label="Generation lesson steps">
              <ol>
                {steps.map((item, i) => (
                  <li key={item.short}>
                    <button
                      aria-current={step === i + 1 ? "step" : undefined}
                      onClick={() => onStep(i + 1)}
                    >
                      <span className="lesson-step-number">
                        {i < step - 1 ? (
                          <Check size={15} aria-hidden />
                        ) : (
                          String(i + 1).padStart(2, "0")
                        )}
                      </span>
                      {item.short}
                    </button>
                  </li>
                ))}
              </ol>
            </nav>
            <p className="lesson-definition-hint">
              <BookOpen size={15} /> Underlined terms open a short definition in
              English and Chinese.
            </p>
            {data && (
              <details className="lesson-source">
                <summary>About this example</summary>
                <p>
                  Saved from {data.example.collection}, game #
                  {data.example.game_id}, on {data.example.captured}. This is a
                  fixed teaching example; batch numbers do not refresh here.
                </p>
                <p>
                  The board and phases are replayed by Python. Teacher answers
                  are retained evidence. The sampling exercise uses the same
                  sampler as generation.
                </p>
                <small>Trajectory identity</small>
                <code>{data.example.trajectory}</code>
              </details>
            )}
          </aside>
          <article
            className="lesson-panel"
            aria-labelledby="lesson-step-heading"
          >
            <header className="lesson-step-heading">
              <p className="eyebrow">
                STEP {String(step).padStart(2, "0")} / 07
              </p>
              <h2 ref={heading} tabIndex={-1} id="lesson-step-heading">
                {current.title}
              </h2>
              <p>{current.subtitle}</p>
            </header>
            {lesson.isLoading && (
              <p role="status">Replaying the saved teaching example…</p>
            )}
            {lesson.error && (
              <div role="alert">
                <p>Could not load the example: {lesson.error.message}</p>
                <Button onClick={() => void lesson.refetch()}>
                  Retry example
                </Button>
              </div>
            )}
            {data && (
              <div className="lesson-content" key={step}>
                {step === 1 && <ActorLesson example={data.example} />}
                {step === 2 && <ReplayLesson lesson={data} />}
                {step === 3 && <ReplayLesson lesson={data} phases />}
                {step === 4 && <SamplingLesson lesson={data} />}
                {step === 5 && <SupervisionLesson lesson={data} />}
                {step === 6 && <QualityLesson example={data.example} />}
                {step === 7 && (
                  <DatasetLesson example={data.example} onStep={onStep} />
                )}
              </div>
            )}
            <footer className="lesson-pager">
              <Button disabled={step === 1} onClick={() => onStep(step - 1)}>
                <ArrowLeft size={16} /> Previous
              </Button>
              <span>
                {step} of {steps.length}
              </span>
              {step < steps.length ? (
                <Button variant="default" onClick={() => onStep(step + 1)}>
                  Next: {steps[step].short}
                  <ArrowRight size={16} />
                </Button>
              ) : (
                <Button onClick={() => onStep(1)}>
                  <RotateCcw size={16} /> Start again
                </Button>
              )}
            </footer>
          </article>
        </div>
      </section>
    </GlossaryContext.Provider>
  );
}
