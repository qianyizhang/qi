import { useId, useRef, useState } from "react";
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
  arrows?: { move: string; color: string }[];
  view: Pick<Position, "board" | "legal_moves"> & {
    snapshot: { moves?: string[] };
  };
  flipped: boolean;
  selected: string | null;
  keyboardDisabled?: boolean;
  disabled?: boolean;
  onChoose?: (index: number) => void;
};

export function Board({
  view,
  arrows = [],
  flipped,
  selected,
  keyboardDisabled,
  disabled,
  onChoose,
}: BoardProps) {
  const [cursor, setCursor] = useState(0);
  const squares = useRef<(SVGGElement | null)[]>([]);
  const helpId = useId();
  const interactive = !!onChoose;
  const enabled = interactive && !disabled && !keyboardDisabled;
  return (
    <svg
      viewBox="0 0 540 600"
      role="group"
      aria-label="Chinese chess board"
      aria-describedby={interactive ? helpId : undefined}
      className="board"
    >
      {interactive && (
        <desc id={helpId}>
          Use arrow keys to explore squares. Enter or Space selects a piece or
          legal destination. Tab leaves the board.
        </desc>
      )}
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
        const last = view.snapshot.moves?.at(-1);
        const recent = last?.slice(0, 2) === sq || last?.slice(2) === sq;
        const label = `${sq}${piece === "." ? " empty" : ` ${color(piece)} ${names[piece.toUpperCase()]}`}${destination ? ", legal destination" : ""}`;
        return (
          <g
            key={i}
            ref={(element) => {
              squares.current[i] = element;
            }}
            transform={`translate(${x},${y})`}
            role={interactive ? "button" : undefined}
            tabIndex={
              interactive ? (enabled && cursor === i ? 0 : -1) : undefined
            }
            aria-disabled={interactive ? disabled : undefined}
            aria-label={label}
            aria-pressed={interactive ? active : undefined}
            onFocus={() => setCursor(i)}
            onClick={() => {
              if (!enabled) return;
              setCursor(i);
              onChoose(i);
            }}
            onKeyDown={(e) => {
              if (!enabled) return;
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onChoose(i);
                return;
              }
              const direction: Record<string, [number, number]> = {
                ArrowLeft: [-1, 0],
                ArrowRight: [1, 0],
                ArrowUp: [0, 1],
                ArrowDown: [0, -1],
              };
              const step = direction[e.key];
              if (!step) return;
              e.preventDefault();
              const sign = flipped ? -1 : 1;
              const file = Math.max(0, Math.min(8, (i % 9) + step[0] * sign));
              const rank = Math.max(
                0,
                Math.min(9, Math.floor(i / 9) + step[1] * sign),
              );
              const next = rank * 9 + file;
              setCursor(next);
              squares.current[next]?.focus();
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
      {arrows.map(({ move, color }, index) => {
        const point = (square: string) => {
          const file = square.charCodeAt(0) - 97,
            rank = Number(square[1]);
          return [
            50 + (flipped ? 8 - file : file) * 56,
            48 + (flipped ? rank : 9 - rank) * 56,
          ];
        };
        const [x1, y1] = point(move.slice(0, 2)),
          [x2, y2] = point(move.slice(2));
        const dx = x2 - x1,
          dy = y2 - y1,
          length = Math.hypot(dx, dy);
        if (!length) return null;
        const ux = dx / length,
          uy = dy / length,
          endX = x2 - ux * 12,
          endY = y2 - uy * 12;
        return (
          <g key={index} pointerEvents="none" opacity="0.8" aria-hidden="true">
            <line
              x1={x1 + ux * 15}
              y1={y1 + uy * 15}
              x2={endX - ux * 12}
              y2={endY - uy * 12}
              stroke={color}
              strokeWidth="7"
              strokeLinecap="round"
            />
            <polygon
              points={`${endX},${endY} ${endX - ux * 19 - uy * 9},${endY - uy * 19 + ux * 9} ${endX - ux * 19 + uy * 9},${endY - uy * 19 - ux * 9}`}
              fill={color}
            />
          </g>
        );
      })}
    </svg>
  );
}
