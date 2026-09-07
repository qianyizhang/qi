"""Optional movement-only differential check; install pyffish separately."""

import random
import re

from qi.game import Game, legal_moves


def main() -> None:
    import pyffish

    # SAMPLE: Fairy-Stockfish b3b10 corresponds to qi b2b9 (one-based ranks).
    pattern = re.compile(r"([a-i])(10|[1-9])([a-i])(10|[1-9])")

    def to_qi(move: str) -> str:
        match = pattern.fullmatch(move)
        if match is None:
            raise ValueError(f"Unexpected reference move: {move}")
        a, b, c, d = match.groups()
        return f"{a}{int(b) - 1}{c}{int(d) - 1}"

    def to_reference(move: str) -> str:
        return f"{move[0]}{int(move[1]) + 1}{move[2]}{int(move[3]) + 1}"

    rng = random.Random(7)
    count = 0
    for _ in range(10):
        game = Game()
        for _ in range(100):
            ours = set(legal_moves(game.board, game.turn))
            reference = pyffish.legal_moves(
                "xiangqi", pyffish.start_fen("xiangqi"), [to_reference(m) for m in game.moves]
            )
            theirs = {to_qi(m) for m in reference}
            if ours != theirs:
                raise AssertionError((game.moves, ours - theirs, theirs - ours))
            count += 1
            if game.outcome:
                break
            game = game.apply(rng.choice(sorted(ours)))
    print(f"Legal moves matched across {count} positions (seed 7). Adjudication is not compared.")


if __name__ == "__main__":
    main()
