import type { Position } from "./api";

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
export const coord = (i: number) =>
  String.fromCharCode(97 + (i % 9)) + Math.floor(i / 9);
export const color = (piece: string) =>
  piece === piece.toUpperCase() ? "red" : "black";

type BoardProps = {
  view: Position;
  flipped: boolean;
  selected: string | null;
  keyboardDisabled: boolean;
  disabled: boolean;
  onChoose: (index: number) => void;
};

export function Board({
  view,
  flipped,
  selected,
  keyboardDisabled,
  disabled,
  onChoose,
}: BoardProps) {
  return (
    <svg
      viewBox="0 0 540 600"
      role="group"
      aria-label="Chinese chess board"
      className="board"
    >
      <rect x="0" y="0" width="540" height="600" rx="8" fill="#e9d6ae" />
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
          y = 48 + (flipped ? Math.floor(i / 9) : 9 - Math.floor(i / 9)) * 56;
        const piece = view.board[i],
          sq = coord(i),
          active = selected === sq;
        const destination =
          selected && view.legal_moves.includes(selected + sq);
        const last = view.snapshot.moves.at(-1);
        const recent = last?.slice(0, 2) === sq || last?.slice(2) === sq;
        const label = `${sq}${piece === "." ? " empty" : ` ${color(piece)} ${names[piece.toUpperCase()]}`}${destination ? ", legal destination" : ""}`;
        return (
          <g
            key={i}
            transform={`translate(${x},${y})`}
            role="button"
            tabIndex={keyboardDisabled ? -1 : 0}
            aria-disabled={disabled}
            aria-label={label}
            aria-pressed={active}
            onClick={() => void onChoose(i)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                void onChoose(i);
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
                  stroke={color(piece) === "red" ? "#b54d3e" : "#484840"}
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
  );
}
