import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import { read, type Schema } from "./api";
import { Board } from "./board";
import { Button } from "./components/ui/button";
import { Term } from "./reference";
import { number } from "./data-format";
import { Takeaway } from "./generation-concepts";
import type { Lesson } from "./generation-lesson";

const phaseNames = ["opening", "middlegame", "endgame"] as const;
export function ReplayLesson({
  lesson,
  phases = false,
}: {
  lesson: Lesson;
  phases?: boolean;
}) {
  const [ply, setPly] = useState(phases ? 31 : 0);
  const frame = lesson.frames[ply],
    max = lesson.frames.length - 1;
  return (
    <>
      <div className="lesson-replay">
        <div className="lesson-board">
          <Board
            flipped={false}
            view={frame.position}
            selected={null}
            disabled
            keyboardDisabled
            onChoose={() => {}}
            arrows={
              ply < max
                ? [
                    {
                      move: lesson.example.snapshot.moves[ply],
                      color: "#315c4c",
                    },
                  ]
                : []
            }
          />
          <div className="lesson-replay-controls">
            <Button
              size="icon"
              aria-label="Previous ply"
              disabled={ply === 0}
              onClick={() => setPly(ply - 1)}
            >
              <ChevronLeft size={16} />
            </Button>
            <input
              type="range"
              aria-label="Example replay ply"
              min={0}
              max={max}
              value={ply}
              onChange={(e) => setPly(Number(e.target.value))}
            />
            <Button
              size="icon"
              aria-label="Next ply"
              disabled={ply === max}
              onClick={() => setPly(ply + 1)}
            >
              <ChevronRight size={16} />
            </Button>
          </div>
          <p className="lesson-board-caption" aria-live="polite">
            <b>
              Ply {ply} / {max}
            </b>
            <span>
              {frame.position.outcome
                ? "Black wins · checkmate"
                : `${frame.position.turn} to move`}{" "}
              · {frame.phase}
            </span>
          </p>
        </div>
        <div>
          {phases ? (
            <>
              <p className="eyebrow">COUNT THE MOBILE PIECES</p>
              <div className="lesson-material">
                <strong>{frame.mobile}</strong>
                <span>
                  chariots + horses + cannons
                  <br />
                  across both sides
                </span>
              </div>
              <p>
                <b>{frame.developed}</b> are on squares where that same piece
                symbol was not present in the starting layout. This is the
                classifier’s “development” count.
              </p>
              <div className="lesson-phase-rules">
                {phaseNames.map((phase) => (
                  <div
                    key={phase}
                    className={frame.phase === phase ? "active" : ""}
                  >
                    <span className={`phase-dot ${phase}`} />
                    <div>
                      <strong>{phase}</strong>
                      <small>
                        {phase === "opening"
                          ? "10+ mobile pieces and development count ≤ 2"
                          : phase === "endgame"
                            ? "4 or fewer mobile pieces"
                            : "All other valid boards"}
                      </small>
                    </div>
                    {frame.phase === phase && (
                      <span className="badge">Now</span>
                    )}
                  </div>
                ))}
              </div>
              <p className="muted">
                This experimental heuristic is a sampling convention. It is not
                a universal definition of Xiangqi phases. A board without one
                general per side is “unknown.”
              </p>
            </>
          ) : (
            <>
              <p className="eyebrow">
                RECORDED INTERVENTION GAME #{lesson.example.game_id}
              </p>
              <h3>
                {ply === 0
                  ? "The starting position"
                  : ply === max
                    ? "The referee ends the game"
                    : `A position after ${ply} half-moves`}
              </h3>
              <p>
                A <Term name="Ply" /> is one move by one side. Red’s move and
                Black’s reply together make two plies. Ply 0 is the initial
                board.
              </p>
              <div className="lesson-move-card">
                <small>
                  {ply === max
                    ? "Final actor move"
                    : "Next recorded actor move"}
                </small>
                <strong>
                  {lesson.example.snapshot.moves[ply === max ? ply - 1 : ply]}
                </strong>
                <span>
                  {ply === lesson.example.intervention_ply
                    ? "Marked intervention: a non-best legal move."
                    : ply === max
                      ? "Black delivered checkmate at the 32nd half-move."
                      : "Teacher-best actor decision."}
                </span>
              </div>
              <p>
                The <Term name="Trajectory" /> is the complete ordered replay. A{" "}
                <Term name="Position" /> is a state along that replay: the
                board, side to move, and rule-relevant context.
              </p>
              <p className="muted">
                The arrow shows the next recorded move. Drag the slider or use
                the buttons; this replays saved moves.
              </p>
            </>
          )}
          <div className="lesson-jumps" aria-label="Key moments">
            {[
              { p: 0, text: "Start" },
              { p: 3, text: "Ply 3" },
              { p: 17, text: "Ply 17" },
              { p: 30, text: "Intervention" },
              { p: max, text: "Finish" },
            ].map(({ p, text }) => (
              <button
                key={p}
                aria-pressed={ply === p}
                onClick={() => setPly(p)}
              >
                {text}
              </button>
            ))}
          </div>
        </div>
      </div>
      <Takeaway>
        {phases ? (
          <>
            The last position of this game is still classified as{" "}
            <b>middlegame</b>. “The game ended” does not mean “the board reached
            endgame.” That is why this game has no endgame samples.
          </>
        ) : (
          <>
            A game with {max} plies has {max + 1} replay states including the
            initial board. Sampling later keeps only a few eligible, nonterminal
            states; the full game stays available.
          </>
        )}
      </Takeaway>
    </>
  );
}

export function SamplingLesson({ lesson }: { lesson: Lesson }) {
  const [practice, setPractice] = useState(false),
    [spacing, setSpacing] = useState(4),
    [seed, setSeed] = useState(7),
    [ply, setPly] = useState(3);
  const query = useQuery({
    queryKey: ["lesson-sampling", spacing, seed],
    queryFn: ({ signal }) =>
      read<Schema<"SamplingResult">>(
        `learn/generation/sampling?spacing=${spacing}&seed=${seed}`,
        signal,
      ),
    enabled: practice,
    staleTime: Infinity,
    retry: false,
  });
  const result = practice ? query.data : lesson.example.sampling;
  const selected = result?.selected ?? [];
  const frame = lesson.frames[ply];
  const target = Object.values(lesson.example.sampling.requested).reduce(
    (a, b) => a + b,
    0,
  );
  return (
    <>
      <div className="lesson-segment" aria-label="Sampling mode">
        <button aria-pressed={!practice} onClick={() => setPractice(false)}>
          Recorded sample
        </button>
        <button aria-pressed={practice} onClick={() => setPractice(true)}>
          Try the sampler
        </button>
      </div>
      {practice ? (
        <div className="lesson-sampling-controls">
          <label>
            Minimum spacing: {spacing} plies
            <input
              aria-label="Minimum sample spacing"
              type="range"
              min={1}
              max={8}
              value={spacing}
              onChange={(e) => setSpacing(Number(e.target.value))}
            />
          </label>
          <Button onClick={() => setSeed((seed + 1) % 32)}>
            <RotateCcw size={15} /> Try another shuffle
          </Button>
          <small>
            Practice seed {seed}. Same game and targets; a fresh sample,
            separate from the recorded selection.
          </small>
        </div>
      ) : (
        <p className="muted">
          Recorded settings: 1 opening + 8 middlegame + 8 endgame positions, at
          least {lesson.example.sampling_policy.min_spacing} plies apart.
          Sampling window: plies 1–299.
        </p>
      )}
      {query.error && practice && (
        <p role="alert">
          Practice sample failed: {query.error.message}{" "}
          <Button size="sm" onClick={() => void query.refetch()}>
            Retry sampling
          </Button>
        </p>
      )}
      <div className="lesson-demo" aria-busy={practice && query.isFetching}>
        {!result ? (
          <p role="status">Selecting practice positions…</p>
        ) : (
          <>
            <div className="lesson-sample-total" aria-live="polite">
              <strong>
                {selected.length}
                <small>selected</small>
              </strong>
              <span>+</span>
              <strong>
                {target - selected.length}
                <small>unfilled</small>
              </strong>
              <span>=</span>
              <strong>
                {target}
                <small>requested</small>
              </strong>
            </div>
            <div className="lesson-quota-list">
              {phaseNames.map((phase) => (
                <div key={phase}>
                  <b>
                    <span className={`phase-dot ${phase}`} />
                    {phase}
                  </b>
                  <div
                    className="lesson-quota-slots"
                    aria-label={`${phase}: ${result.actual[phase]} of ${result.requested[phase]} selected`}
                  >
                    {Array.from(
                      { length: result.requested[phase] ?? 0 },
                      (_, i) => (
                        <span
                          key={i}
                          className={
                            i < (result.actual[phase] ?? 0) ? "filled" : ""
                          }
                        />
                      ),
                    )}
                  </div>
                  <span>
                    {result.actual[phase]} / {result.requested[phase]}
                  </span>
                </div>
              ))}
            </div>
            <p className="muted">
              Filled squares are retained positions. Outlined squares are
              unfilled targets for that phase.
            </p>
            <h3>Where the selected positions occur</h3>
            <div className="lesson-timeline" aria-label="Sampling timeline">
              {lesson.frames.map((f, i) => (
                <button
                  key={i}
                  className={`${f.phase} ${selected.includes(i) ? "sampled" : ""} ${i === ply ? "chosen" : ""}`}
                  aria-pressed={i === ply}
                  aria-label={`Ply ${i}, ${f.phase}${selected.includes(i) ? ", selected" : ", not selected"}`}
                  onClick={() => setPly(i)}
                >
                  <span>{i}</span>
                  <small>
                    {selected.includes(i)
                      ? "●"
                      : i === 0 || f.position.outcome
                        ? "×"
                        : "·"}
                  </small>
                </button>
              ))}
            </div>
            <div className="lesson-timeline-legend">
              <span>● Selected</span>
              <span>· Not selected</span>
              <span>× Initial / terminal state excluded</span>
            </div>
            <p className="lesson-position-explanation" aria-live="polite">
              <b>
                Ply {ply} · {frame.phase}.
              </b>{" "}
              {selected.includes(ply)
                ? "This occurrence was retained for teacher supervision."
                : ply === 0
                  ? "The configured window starts at ply 1."
                  : frame.position.outcome
                    ? "Terminal states are not sampling candidates."
                    : "This occurrence was not retained under this shuffle, quota and spacing policy."}
            </p>
            <p>
              Before spacing, this game has{" "}
              <b>{result.available.opening} opening</b>,{" "}
              <b>{result.available.middlegame} middlegame</b>, and{" "}
              <b>{result.available.endgame} endgame</b> eligible distinct
              inputs. The seeded greedy sampler shuffles candidates, then keeps
              one only if its phase still needs a sample and it is far enough
              from every retained ply.
            </p>
          </>
        )}
      </div>
      <p className="lesson-margin-note">
        Reserved learner inputs and repeated inputs within the same trajectory
        are removed before spacing. Across-game duplicates can still remain in
        the collection. Unfilled quotas are never moved to another phase; greedy
        underfill does not prove every possible selection would underfill.
      </p>
      <Takeaway>
        “Selected / gap” means{" "}
        <b>retained position occurrences / unfilled sampling targets</b>. For
        the recorded game, that is 6 selected and 11 unfilled. The chips 3, 10,
        17, 22, 26, 31 are their ply numbers.
      </Takeaway>
    </>
  );
}

export function SupervisionLesson({ lesson }: { lesson: Lesson }) {
  const [exactOnly, setExactOnly] = useState(true),
    [ply, setPly] = useState(31);
  const analyses = lesson.example.analyses;
  const exact = analyses.filter(
    (a) => a.score.kind === "cp" && a.score.bound === "exact",
  );
  const bounded = analyses.filter(
    (a) => a.score.kind === "cp" && a.score.bound !== "exact",
  ).length;
  const mate = analyses.filter((a) => a.score.kind === "mate").length;
  const visible = exactOnly ? exact : analyses;
  const evidence = analyses.filter((a) => a.ply === ply);
  const redScore = (a: (typeof analyses)[number]) =>
    a.score.value * (lesson.frames[a.ply].position.turn === "red" ? 1 : -1);
  const format = (a: (typeof analyses)[number]) =>
    `${a.score.bound === "lowerbound" ? "≥ " : a.score.bound === "upperbound" ? "≤ " : ""}${a.score.value > 0 ? "+" : ""}${a.score.value} ${a.score.kind}`;
  return (
    <>
      <div className="lesson-count-flow">
        {[
          {
            value: lesson.example.snapshot.moves.length,
            text: "plies in the game",
          },
          {
            value: lesson.example.sampling.selected.length,
            text: "selected occurrences",
          },
          { value: analyses.length, text: "supervision analyses" },
          { value: exact.length, text: "exact cp plot points" },
        ].map((x, i) => (
          <div key={x.text}>
            <strong>{x.value}</strong>
            <small>{x.text}</small>
            {i < 3 && <ArrowRight aria-hidden size={18} />}
          </div>
        ))}
      </div>
      <p>
        A <Term name="Supervision specification" /> identifies exactly which
        engine, settings and budget produced the label. Here each selected
        occurrence has one <b>10,000-node</b> and one <b>100,000-node</b>{" "}
        single-PV analysis. “Nodes” is the requested engine search-work budget;
        “PV 1” asks for one principal line.
      </p>
      <div className="lesson-demo">
        <h3>Why the original chart has only two dots</h3>
        <svg
          className="lesson-score-chart"
          viewBox="0 0 620 170"
          role="img"
          aria-label="Two exact centipawn scores from Red's perspective: minus 21 at ply 10, minus 51 at ply 17."
        >
          <line x1="50" y1="35" x2="600" y2="35" stroke="#9eaea0" />
          <line x1="50" y1="140" x2="600" y2="140" stroke="#d4dbcf" />
          <text x="10" y="40">
            0
          </text>
          <text x="4" y="144">
            −100
          </text>
          <text x="50" y="165">
            Ply 0
          </text>
          <text x="552" y="165">
            Ply 32
          </text>
          {exact.map((a) => (
            <g key={a.analysis_id}>
              <circle
                cx={50 + (a.ply / 32) * 550}
                cy={35 - redScore(a) * 1.05}
                r="6"
                fill={a.nodes === 10000 ? "#315c4c" : "#b76d41"}
              />
              <text
                x={50 + (a.ply / 32) * 550 + 10}
                y={35 - redScore(a) * 1.05 + 4}
              >
                {redScore(a)} cp
              </text>
            </g>
          ))}
        </svg>
        <div className="lesson-score-key">
          <span>
            <i style={{ background: "#315c4c" }} />
            10,000 nodes
          </span>
          <span>
            <i style={{ background: "#b76d41" }} />
            100,000 nodes
          </span>
        </div>
        <p>
          The chart keeps <b>{exact.length} exact cp</b> results. It omits{" "}
          <b>{bounded} bounded cp</b> results and <b>{mate} mate</b> results.
          These are sampled analyses, not a continuous evaluation after every
          move.
        </p>
        <div className="lesson-segment" aria-label="Teacher evidence filter">
          <button aria-pressed={exactOnly} onClick={() => setExactOnly(true)}>
            Exact cp only ({exact.length})
          </button>
          <button aria-pressed={!exactOnly} onClick={() => setExactOnly(false)}>
            All analyses ({analyses.length})
          </button>
        </div>
        <div
          className="lesson-evidence-grid"
          aria-label="Retained teacher analyses"
        >
          {visible.map((a) => (
            <button
              key={a.analysis_id}
              aria-pressed={ply === a.ply}
              onClick={() => setPly(a.ply)}
            >
              <small>
                Ply {a.ply} · {a.nodes / 1000}k nodes
              </small>
              <strong>{format(a)}</strong>
              <span>
                {a.score.kind === "mate"
                  ? "Mate score · off cp plot"
                  : a.score.bound === "exact"
                    ? "Exact cp · plotted"
                    : "Bound · off cp plot"}
              </span>
            </button>
          ))}
        </div>
        <p className="muted">
          Cards show the score from the side to move. The chart converts to
          Red’s perspective: at ply 17, Black’s +51 cp becomes Red’s −51 cp.
          “Exact” is the engine’s score-bound category, not proof of objective
          truth. ≥ is a lower bound; ≤ is an upper bound.
        </p>
      </div>
      <div className="lesson-selected-evidence">
        <label>
          Inspect a selected occurrence
          <select value={ply} onChange={(e) => setPly(Number(e.target.value))}>
            {lesson.example.sampling.selected.map((p) => (
              <option key={p} value={p}>
                Ply {p} · {lesson.frames[p].position.turn} to move
              </option>
            ))}
          </select>
        </label>
        <h3>
          At ply {ply}, the actor played {lesson.example.snapshot.moves[ply]}
        </h3>
        <div className="lesson-label-pair">
          {evidence.map((a) => (
            <div key={a.analysis_id}>
              <small>{number(a.nodes)} nodes · single PV</small>
              <p>
                Teacher target <b>{a.move}</b>
              </p>
              <strong>{format(a)}</strong>
            </div>
          ))}
        </div>
        {evidence.some((a) => a.score.kind === "mate") && (
          <p>
            +1 mate reports a forced mate in one move for the side to move. It
            has a different unit from centipawns, so it is not placed on the cp
            axis.
          </p>
        )}
      </div>
      <Takeaway>
        The actor’s move is what happened; the teacher target is what the engine
        recommends from that position. Two budgets provide two pieces of
        evidence about one input. More analyses do not automatically mean more
        distinct training examples.
      </Takeaway>
    </>
  );
}
