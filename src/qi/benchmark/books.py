"""Replay-validated opening book construction with explicit family partitions."""

from collections import Counter

from pydantic import Field

from qi.artifacts import digest
from qi.benchmark.models import Book, BookStart, Record
from qi.protocol import Snapshot


class SourceGame(Record):
    id: str
    source_url: str
    description: str
    moves: list[str] = Field(min_length=1)


def build_books(games: list[SourceGame], *, id: str, provenance: str, plies: int = 12) -> tuple[Book, Book, dict]:
    if plies < 8:
        raise ValueError("Human opening prefixes require at least eight plies; family grouping uses six.")
    starts = {"development": [], "locked-test": []}
    seen_boards, seen_games = set(), set()
    rejected = Counter()
    for source in sorted(games, key=lambda g: g.id):
        if source.id in seen_games:
            rejected["duplicate-source-game"] += 1
            continue
        seen_games.add(source.id)
        if len(source.moves) < plies:
            rejected["short-source"] += 1
            continue
        snapshot = Snapshot(moves=source.moves[:plies])
        try:
            game = snapshot.game()
            prefix = Snapshot(moves=source.moves[:6]).game()
        except ValueError:
            rejected["illegal-prefix"] += 1
            continue
        board = (game.board, game.turn)
        if game.outcome or board in seen_boards:
            rejected["terminal-or-duplicate-start"] += 1
            continue
        seen_boards.add(board)
        family = digest({"policy": "six-ply-board-family-v1", "board": prefix.board, "turn": prefix.turn})
        use = (
            "locked-test"
            if int(digest({"partition": "qi-book-split-v1", "family": family})[:8], 16) % 5 == 0
            else "development"
        )
        starts[use].append(
            BookStart(
                id=f"opening-{game.state_hash[:16]}",
                family=family,
                source_game=source.id,
                source_url=source.source_url,
                description=source.description,
                snapshot=snapshot,
            )
        )
    if not all(starts.values()):
        raise ValueError("Book construction must produce nonempty development and locked-test pools.")
    selection = (
        f"Sorted source identity; one {plies}-ply prefix per source; deduplicate board/turn; "
        "group by board/turn after six plies; SHA256(qi-book-split-v1, family) modulo 5 == 0 is locked-test. "
        "Recorded prefixes only are replay-validated; source continuations are not referee-certified."
    )
    books = [
        Book(id=f"{id}-{use}", use=use, provenance=provenance, selection=selection, starts=entries)
        for use, entries in starts.items()
    ]
    audit = {
        "source_games": len(games),
        "rejected": dict(rejected),
        "accepted": {k: len(v) for k, v in starts.items()},
        "families": {k: len({s.family for s in v}) for k, v in starts.items()},
    }
    return books[0], books[1], audit
