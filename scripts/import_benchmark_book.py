"""Normalize CCPD Chinese-notation prefixes from a pinned downloaded manifest.

Raw downloads stay local; sources.json preserves the portable normalized inputs
and source hashes. No engine chooses, repairs or filters moves by strength.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from qi.artifacts import digest, write_json
from qi.benchmark.books import SourceGame, build_books
from qi.game import START_FEN, Game, legal_moves, parse_move

NUMBERS = {c: str(i) for i, c in enumerate("〇一二三四五六七八九")}
PIECES = {
    "車": "R",
    "俥": "R",
    "马": "N",
    "馬": "N",
    "傌": "N",
    "相": "B",
    "象": "B",
    "仕": "A",
    "士": "A",
    "帅": "K",
    "帥": "K",
    "将": "K",
    "將": "K",
    "炮": "C",
    "砲": "C",
    "包": "C",
    "兵": "P",
    "卒": "P",
    "车": "R",
}


def normalize(token):
    token = unicodedata.normalize("NFKC", token)
    return "".join(NUMBERS.get(c, c) for c in token).replace("进", "進").replace("后", "後")


def chinese_move(game: Game, token: str) -> str:
    token = normalize(token)
    if len(token) != 4:
        raise ValueError(f"Unsupported move notation: {token!r}")
    front = token[0] in "前後中"
    piece = PIECES.get(token[1] if front else token[0])
    matches = []
    for move in legal_moves(game.board, game.turn):
        source, target = parse_move(move)
        if game.board[source].upper() != piece:
            continue

        def file(square):
            return 9 - square % 9 if game.turn == "red" else square % 9 + 1

        if front:
            peers = [i for i, p in enumerate(game.board) if p == game.board[source] and i % 9 == source % 9]
            peers.sort(reverse=game.turn == "red")
            if len(peers) < 2 or source != peers[{"前": 0, "後": -1, "中": len(peers) // 2}[token[0]]]:
                continue
        elif str(file(source)) != token[1]:
            continue
        delta = (target // 9 - source // 9) * (1 if game.turn == "red" else -1)
        direction = "平" if delta == 0 else "進" if delta > 0 else "退"
        destination = file(target) if direction == "平" or piece in "NBA" else abs(delta)
        if direction == token[2] and str(destination) == token[3]:
            matches.append(move)
    if len(matches) != 1:
        raise ValueError(f"Expected one legal move for {token!r}, found {len(matches)}.")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    games, receipts, rejected = [], [], []
    for item in manifest["files"]:
        try:
            data = Path(item["local"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Source digest mismatch")
            text = data.decode("cp950")
            headers = dict(re.findall(r'^\[(\w+) "(.*)"\]$', text, re.M))
            if " ".join(headers.get("FEN", "").split()[:2]) != START_FEN:
                raise ValueError("Source does not begin at the standard initial position")
            body = re.sub(r"^\[.*\]$", "", text, flags=re.M)
            body = re.sub(r"\{[^}]*\}", "", body)
            tokens = [t for t in body.split() if not re.fullmatch(r"\d+\.+|1-0|0-1|1/2-1/2|\*", t)]
            identity = digest([normalize(t) for t in tokens])
            game = Game()
            for token in tokens[:12]:
                game = game.apply(chinese_move(game, token))
            if len(game.moves) != 12:
                raise ValueError("Fewer than twelve prefix plies")
            description = (
                f"{headers.get('Red', '?')} vs {headers.get('Black', '?')} · "
                f"{headers.get('Date', '?')} · {headers.get('Event', '')}"
            )
            games.append(
                SourceGame(id=identity, source_url=item["source_url"], description=description, moves=list(game.moves))
            )
            receipts.append(
                {
                    "source_game": identity,
                    "source_url": item["source_url"],
                    "sha256": item["sha256"],
                    "encoding": "cp950",
                    "original_prefix": tokens[:12],
                }
            )
        except (ValueError, UnicodeError, KeyError) as exc:
            rejected.append({"path": item["path"], "reason": str(exc)})
    provenance = (
        "Yu-Han Tseng and Bo-Nian Chen (2026), Chinese Chess Practical Dataset (CCPD), "
        "https://github.com/Yvonne761/Chinese-Chess-Practical-Dataset, CC BY 4.0. "
        f"Pinned revision {manifest['commit']}. " + manifest["selection"]
    )
    dev, test, audit = build_books(games, id="ccpd-openings-v1", provenance=provenance)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, value in (
        ("development.json", dev.model_dump(mode="json")),
        ("locked-test.json", test.model_dump(mode="json")),
        (
            "sources.json",
            {"provenance": provenance, "games": [g.model_dump(mode="json") for g in games], "receipts": receipts},
        ),
        ("audit.json", {**audit, "import_rejections": rejected, "import_rejection_count": len(rejected)}),
    ):
        write_json(args.output / name, value, indent=2)
    print(json.dumps({**audit, "import_rejection_count": len(rejected)}))


if __name__ == "__main__":
    main()
