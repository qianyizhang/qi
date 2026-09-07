"""Bounded local UCI analysis; qi retains legality and outcome authority."""

import os
import selectors
import subprocess
from dataclasses import dataclass
from hashlib import file_digest
from pathlib import Path
from time import monotonic, perf_counter
from typing import Literal

from pydantic import BaseModel

from qi.game import Game, GameError, legal_moves
from qi.protocol import Snapshot


@dataclass(frozen=True)
class TeacherConfig:
    engine: Path
    network: Path
    nodes: int = 10_000
    depth: int = 6
    timeout_seconds: float = 10

    def __post_init__(self) -> None:
        if self.nodes < 1 or not 1 <= self.depth <= 64 or not 0 < self.timeout_seconds <= 120:
            raise GameError("invalid_budget", "Teacher needs positive nodes, depth 1-64, and timeout in (0, 120].")
        for path in (self.engine, self.network):
            if not path.is_file() or any(c in str(path.resolve()) for c in "\r\n"):
                raise GameError("invalid_teacher", "Engine and network must be existing files with single-line paths.")


class TeacherScore(BaseModel):
    kind: Literal["cp", "mate"]
    value: int
    bound: Literal["exact", "lowerbound", "upperbound"]
    perspective: Literal["side_to_move"] = "side_to_move"
    semantics: Literal["engine_native"] = "engine_native"


class TeacherAnalysis(BaseModel):
    schema_version: Literal[1] = 1
    adapter_version: Literal["uci-teacher-v1"] = "uci-teacher-v1"
    snapshot: Snapshot
    state_hash: str
    move: str
    engine_name: str
    engine_sha256: str
    network_sha256: str
    settings: dict[str, str]
    requested_nodes: int
    requested_depth: int
    timeout_seconds: float
    reported_nodes: int | None
    reported_depth: int | None
    score: TeacherScore | None
    elapsed_ms: float
    search_info: list[str]
    invalid_actions: int = 0
    retries: int = 0


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


class UciProcess:
    """One fresh engine per analysis, with a shared protocol deadline and output cap."""

    def __init__(self, config: TeacherConfig):
        self.deadline = monotonic() + config.timeout_seconds
        self.process = subprocess.Popen(
            [str(config.engine.resolve())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=config.engine.resolve().parent,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.pending = b""
        self.total = 0

    def send(self, command: str) -> None:
        try:
            self.process.stdin.write((command + "\n").encode())
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise GameError("teacher_exit", "Teacher exited before completing the protocol.") from exc

    def line(self) -> str:
        while True:
            remaining = self.deadline - monotonic()
            if remaining <= 0:
                raise GameError("teacher_timeout", "Teacher exceeded its protocol deadline.")
            if b"\n" in self.pending:
                line, self.pending = self.pending.split(b"\n", 1)
                return line.decode("utf-8", errors="replace").strip()
            if not self.selector.select(remaining):
                raise GameError("teacher_timeout", "Teacher exceeded its protocol deadline.")
            chunk = os.read(self.process.stdout.fileno(), 8192)
            if not chunk:
                raise GameError("teacher_exit", "Teacher exited without a complete response.")
            self.total += len(chunk)
            if self.total > 1_048_576:
                raise GameError("teacher_output_limit", "Teacher exceeded the 1 MiB protocol output limit.")
            self.pending += chunk

    def until(self, marker: str) -> list[str]:
        lines = []
        while (line := self.line()) != marker:
            lines.append(line)
        return lines

    def close(self) -> None:
        self.selector.close()
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


def read_info(lines: list[str]) -> tuple[int | None, int | None, TeacherScore | None]:
    nodes = depth = None
    score = None
    for line in lines:
        tokens = line.split()
        if len(tokens) < 2 or tokens[0] != "info" or tokens[1] == "string":
            continue
        try:
            if "nodes" in tokens:
                nodes = int(tokens[tokens.index("nodes") + 1])
            if "depth" in tokens:
                depth = int(tokens[tokens.index("depth") + 1])
            if "score" in tokens:
                start = tokens.index("score")
                kind, value = tokens[start + 1 : start + 3]
                bound = next((b for b in ("lowerbound", "upperbound") if b in tokens), "exact")
                score = TeacherScore(kind=kind, value=int(value), bound=bound)
            if (nodes is not None and nodes < 0) or (depth is not None and depth < 0):
                raise ValueError("negative search statistic")
        except (ValueError, IndexError) as exc:
            raise GameError("teacher_protocol", "Malformed teacher search information.") from exc
    return nodes, depth, score


def analyze(game: Game, config: TeacherConfig) -> TeacherAnalysis:
    if game.outcome:
        raise GameError("game_over", "Cannot query a teacher after the game ends.")
    snapshot = Snapshot(moves=list(game.moves))
    if snapshot.game() != game:
        raise GameError("invalid_state", "Teacher input must replay from the standard initial position.")
    engine_hash, network_hash = digest(config.engine), digest(config.network)
    settings = {
        "Threads": "1",
        "Hash": "16",
        "MultiPV": "1",
        "Ponder": "false",
        "EvalFile": str(config.network.resolve()),
    }
    started = perf_counter()
    engine = UciProcess(config)
    try:
        engine.send("uci")
        handshake = engine.until("uciok")
        name = next((line.removeprefix("id name ") for line in handshake if line.startswith("id name ")), "")
        options = {
            line.split(" type ")[0].removeprefix("option name ")
            for line in handshake
            if line.startswith("option name ")
        }
        if not name or not settings.keys() <= options:
            raise GameError(
                "teacher_protocol", "Teacher must identify itself and support Threads, Hash, MultiPV, Ponder, EvalFile."
            )
        for key, value in settings.items():
            engine.send(f"setoption name {key} value {value}")
        engine.send("ucinewgame")
        engine.send("isready")
        engine.until("readyok")
        engine.send("position startpos" + (" moves " + " ".join(game.moves) if game.moves else ""))
        engine.send(f"go nodes {config.nodes} depth {config.depth}")
        info = []
        while True:
            line = engine.line()
            if line.startswith("bestmove "):
                fields = line.split()
                if len(fields) not in (2, 4) or (len(fields) == 4 and fields[2] != "ponder"):
                    raise GameError("teacher_protocol", "Malformed bestmove response.")
                move = fields[1]
                break
            if line.startswith("info "):
                info.append(line)
        if move not in legal_moves(game.board, game.turn):
            raise GameError("teacher_illegal_move", f"Teacher proposed a move rejected by qi: {move}")
        nodes, depth, score = read_info(info)
        return TeacherAnalysis(
            snapshot=snapshot,
            state_hash=game.state_hash,
            move=move,
            engine_name=name,
            engine_sha256=engine_hash,
            network_sha256=network_hash,
            settings=settings,
            requested_nodes=config.nodes,
            requested_depth=config.depth,
            timeout_seconds=config.timeout_seconds,
            reported_nodes=nodes,
            reported_depth=depth,
            score=score,
            elapsed_ms=(perf_counter() - started) * 1000,
            search_info=info,
        )
    finally:
        engine.close()
