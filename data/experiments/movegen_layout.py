"""AB-EVAL-008: bounded NumPy and occupancy-mask prototypes (not player recipes)."""

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter


def load_referee(path):
    spec = importlib.util.spec_from_file_location("layout_baseline", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidates(ref, board, side):
    """Baseline pseudo-legal candidates, shared by the two prototypes."""
    moves = []
    for source, piece in enumerate(board):
        if piece == "." or ref.owner(piece) != side:
            continue
        if piece.upper() in "RC":
            targets = []
            for ray in ref._RAYS[source]:
                screened = False
                for target in ray:
                    if board[target] == ".":
                        if not screened:
                            targets.append(target)
                    elif piece.upper() == "R" or screened:
                        targets.append(target)
                        break
                    else:
                        screened = True
        elif piece in ref._STEPS:
            targets = [target for target, blocker in ref._STEPS[piece][source] if blocker < 0 or board[blocker] == "."]
        else:
            continue
        for target in sorted(targets):
            occupant = board[target]
            if occupant != "." and (occupant.upper() == "K" or ref.owner(occupant) == side):
                continue
            moves.append((source, target))
    return moves


class NumpyMoves:
    """One batch per position, including candidate boards and conversion cost."""

    def __init__(self, ref):
        import numpy as np

        self.np, self.ref = np, ref
        width = max(len(row) for squares in ref._ATTACKERS.values() for row in squares)
        self.pieces = np.zeros((2, 90, width), dtype=np.uint8)
        self.sources = np.full((2, 90, width), 90, dtype=np.intp)
        self.blockers = np.full((2, 90, width), 90, dtype=np.intp)
        for color, side in enumerate(("red", "black")):
            for target, attackers in enumerate(ref._ATTACKERS[side]):
                for i, (piece, source, blocker) in enumerate(attackers):
                    self.pieces[color, target, i] = ord(piece)
                    self.sources[color, target, i] = source
                    self.blockers[color, target, i] = blocker if blocker >= 0 else 90
        self.rays = np.full((90, 4, 9), 90, dtype=np.intp)
        for target, rays in enumerate(ref._RAYS):
            for direction, ray in enumerate(rays):
                self.rays[target, direction, : len(ray)] = ray
        self.vertical = np.array([False, False, True, True])[None, :, None]

    def __call__(self, board, side):
        np, ref = self.np, self.ref
        king = board.find("K" if side == "red" else "k")
        if king < 0:
            return ()
        pairs = candidates(ref, board, side)
        if not pairs:
            return ()
        pairs_array = np.asarray(pairs, dtype=np.intp)
        source, target = pairs_array.T
        rows = np.arange(len(pairs))
        original = np.frombuffer((board + ".").encode("ascii"), dtype=np.uint8)
        boards = np.tile(original, (len(pairs), 1))
        boards[rows, source] = ord(".")
        boards[rows, target] = original[source]
        kings = np.where(source == king, target, king)
        color = int(side == "black")
        attacked = (
            (boards[rows[:, None], self.sources[color, kings]] == self.pieces[color, kings])
            & (boards[rows[:, None], self.blockers[color, kings]] == ord("."))
        ).any(axis=1)
        occupants = boards[rows[:, None, None], self.rays[kings]]
        screens = np.cumsum(occupants != ord("."), axis=2)
        rook, cannon, enemy_king = map(ord, "rck" if side == "red" else "RCK")
        attacked |= (
            ((screens == 1) & ((occupants == rook) | ((occupants == enemy_king) & self.vertical)))
            | ((screens == 2) & (occupants == cannon))
        ).any(axis=(1, 2))
        return tuple(ref._SQUARES[s] + ref._SQUARES[t] for (s, t), bad in zip(pairs, attacked, strict=True) if not bad)


class MaskMoves:
    """Filter potential attackers once, update occupancy with two integer ops."""

    def __init__(self, ref):
        self.ref = ref
        self.bits = tuple(1 << i for i in range(90))
        self.attacks = {}
        for side in ("red", "black"):
            tables = []
            for target in range(90):
                attacks = [
                    (piece, source, self.bits[source], self.bits[blocker] if blocker >= 0 else 0, 0)
                    for piece, source, blocker in ref._ATTACKERS[side][target]
                ]
                rook, cannon, king = "rck" if side == "red" else "RCK"
                for direction, ray in enumerate(ref._RAYS[target]):
                    between = 0
                    for source in ray:
                        bit = self.bits[source]
                        attacks.extend(((rook, source, bit, between, 0), (cannon, source, bit, between, 1)))
                        if direction >= 2:
                            attacks.append((king, source, bit, between, 0))
                        between |= bit
                tables.append(tuple(attacks))
            self.attacks[side] = tuple(tables)

    def __call__(self, board, side):
        ref, bits = self.ref, self.bits
        king = board.find("K" if side == "red" else "k")
        if king < 0:
            return ()
        occupied = sum(bits[i] for i, piece in enumerate(board) if piece != ".")
        contexts = {}
        moves = []
        for source, target in candidates(ref, board, side):
            king_target = target if source == king else king
            if king_target not in contexts:
                contexts[king_target] = tuple(
                    (bit, blockers, screens)
                    for piece, square, bit, blockers, screens in self.attacks[side][king_target]
                    if board[square] == piece
                )
            capture = bits[target]
            updated = (occupied ^ bits[source]) | capture
            for bit, blockers, screens in contexts[king_target]:
                if bit != capture and (updated & blockers).bit_count() == screens:
                    break
            else:
                moves.append(ref._SQUARES[source] + ref._SQUARES[target])
        return tuple(moves)


def screen(run):
    if (run / "screen.json").exists():
        raise ValueError("Use a fresh screen output directory; existing measurements must be preserved.")
    ref = load_referee(run / "before/src/qi/game.py")
    started = perf_counter()
    import numpy as np

    numpy_import_ms = (perf_counter() - started) * 1000
    methods = {"baseline": ref.legal_moves.__wrapped__}
    setups = {}
    for name, cls in (("numpy", NumpyMoves), ("mask", MaskMoves)):
        started = perf_counter()
        methods[name] = cls(ref)
        setups[name] = (perf_counter() - started) * 1000
    positions = json.loads((run / "positions.json").read_text())
    boards = [*positions["boards"], *positions["arbitrary_boards"]]
    for index, board in enumerate(boards):
        for side in ("red", "black"):
            expected = methods["baseline"](board, side)
            for name in ("numpy", "mask"):
                assert methods[name](board, side) == expected, (name, index, side)
    timing_boards = json.loads((run / "timing-boards.json").read_text())
    rounds = []
    for repeat in range(3):
        record = {}
        order = ("baseline", "numpy", "mask") if repeat % 2 == 0 else ("mask", "numpy", "baseline")
        for name in order:
            rows = []
            for board in timing_boards:
                for side in ("red", "black"):
                    started = perf_counter()
                    moves = methods[name](board, side)
                    rows.append({"ms": (perf_counter() - started) * 1000, "moves": len(moves)})
            record[name] = {"rows": rows, "mean_ms": statistics.mean(row["ms"] for row in rows)}
        rounds.append(record)
        print({name: data["mean_ms"] for name, data in record.items()}, flush=True)
    result = {
        "numpy_version": np.__version__,
        "numpy_import_ms": numpy_import_ms,
        "prototype_setup_ms": setups,
        "equivalent_queries_per_prototype": len(boards) * 2,
        "rounds": rounds,
    }
    (run / "screen.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    screen(parser.parse_args().run)
