"""Bounded local UCI analysis; qi retains legality and outcome authority."""

import os
import selectors
import subprocess
from dataclasses import dataclass
from hashlib import file_digest
from pathlib import Path
from time import monotonic, perf_counter
from typing import Literal

from pydantic import BaseModel, model_validator
from qi_game.contracts import Snapshot
from qi_game.core import GameError
from qi_game.execution import ReplaySession
from qi_game.reference import Game, inspect, legal_moves, restore
from qi_game.trajectory import GameView


@dataclass(frozen=True)
class TeacherConfig:
    engine: Path
    network: Path
    nodes: int = 10_000
    depth: int | None = 6
    timeout_seconds: float = 10
    multipv: int = 1
    show_wdl: bool = False
    threads: int = 1

    def __post_init__(self) -> None:
        if (
            self.nodes < 1
            or (self.depth is not None and not 1 <= self.depth <= 64)
            or not 0 < self.timeout_seconds <= 120
            or not 1 <= self.multipv <= 256
            or not isinstance(self.threads, int)
            or isinstance(self.threads, bool)
            or not 1 <= self.threads <= 16
        ):
            raise GameError(
                "invalid_budget",
                "Use positive nodes, optional depth 1-64, MultiPV 1-256, threads 1-16 and timeout (0,120].",
            )
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
    schema_version: Literal[1, 2] = 1
    adapter_version: Literal["uci-teacher-v1", "uci-teacher-v2"] = "uci-teacher-v1"
    snapshot: Snapshot
    state_hash: str
    move: str
    engine_name: str
    engine_sha256: str
    network_sha256: str
    settings: dict[str, str]
    requested_nodes: int
    requested_depth: int | None
    timeout_seconds: float
    reported_nodes: int | None
    reported_depth: int | None
    score: TeacherScore | None
    elapsed_ms: float
    search_info: list[str]
    invalid_actions: int = 0
    retries: int = 0

    @model_validator(mode="after")
    def versioned_search(self):
        if self.adapter_version != f"uci-teacher-v{self.schema_version}":
            raise ValueError("Teacher schema and adapter versions must agree.")
        if self.schema_version == 1 and (
            self.requested_depth is None
            or self.settings.get("MultiPV", "1") != "1"
            or self.settings.get("UCI_ShowWDL") == "true"
        ):
            raise ValueError("Node-only, MultiPV and WDL records require teacher schema v2.")
        return self


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


class UciProcess:
    """Engine pipe with a per-query protocol deadline and output cap."""

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


@dataclass(frozen=True)
class TeacherIdentity:
    engine: Path
    network: Path
    engine_sha256: str
    network_sha256: str

    @classmethod
    def read(cls, config: TeacherConfig) -> "TeacherIdentity":
        return cls(config.engine.resolve(), config.network.resolve(), digest(config.engine), digest(config.network))

    def require(self, config: TeacherConfig) -> None:
        if (config.engine.resolve(), config.network.resolve()) != (self.engine, self.network):
            raise GameError("teacher_mismatch", "Pinned identity belongs to different teacher files.")


class TeacherSession:
    """Sequential, lazy engine session; any failed query permanently closes it."""

    def __init__(
        self,
        config: TeacherConfig,
        *,
        identity: TeacherIdentity | None = None,
        execution: ReplaySession | None = None,
    ):
        self.config = config
        self.execution = execution
        # CONTRACT: supplied identity must have been verified for these files by the caller.
        if identity is not None:
            identity.require(config)
        self.identity = identity
        self.engine: UciProcess | None = None
        self.closed = False
        self.name = ""
        self.options: set[str] = set()
        self.settings = {
            "Threads": str(config.threads),
            "Hash": "16",
            "MultiPV": str(config.multipv),
            "Ponder": "false",
            "EvalFile": str(config.network.resolve()),
        }
        if config.show_wdl:
            self.settings["UCI_ShowWDL"] = "true"

    def __enter__(self) -> "TeacherSession":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        self.closed = True
        if self.engine is not None:
            self.engine.close()
            self.engine = None

    def analyze(self, game: Game | GameView, config: TeacherConfig) -> TeacherAnalysis:
        try:
            return self._analyze(game, config)
        except BaseException:
            self.close()
            raise

    def _analyze(self, game: Game | GameView, config: TeacherConfig) -> TeacherAnalysis:
        if self.closed:
            raise GameError("teacher_closed", "Teacher session is closed; queries are not retried.")
        if (config.engine.resolve(), config.network.resolve()) != (
            self.config.engine.resolve(),
            self.config.network.resolve(),
        ):
            raise GameError("teacher_mismatch", "One teacher session requires the same engine and network paths.")
        if game.outcome:
            raise GameError("game_over", "Cannot query a teacher after the game ends.")
        snapshot = Snapshot(moves=list(game.moves))
        if isinstance(game, GameView):
            expected = (
                self.execution.inspect(snapshot)
                if self.execution is not None
                else GameView.from_position(inspect(restore(snapshot)))
            )
        else:
            expected = restore(snapshot)
        if expected != game:
            raise GameError("invalid_state", "Teacher input must replay from the standard initial position.")
        if self.identity is None:
            self.identity = TeacherIdentity.read(config)
        started = perf_counter()
        if self.engine is None:
            self.engine = UciProcess(config)
            engine = self.engine
            settings = self.settings
            engine.send("uci")
            handshake = engine.until("uciok")
            name = next((line.removeprefix("id name ") for line in handshake if line.startswith("id name ")), "")
            options = {
                line.split(" type ")[0].removeprefix("option name ")
                for line in handshake
                if line.startswith("option name ")
            }
            self.options = options
            if not name or not settings.keys() <= options:
                raise GameError(
                    "teacher_protocol",
                    "Teacher must identify itself and support Threads, Hash, MultiPV, Ponder, EvalFile.",
                )
            for key, value in settings.items():
                engine.send(f"setoption name {key} value {value}")
            self.name = name
        else:
            engine = self.engine
            engine.deadline = monotonic() + config.timeout_seconds
            engine.total = len(engine.pending)
        desired = {"MultiPV": str(config.multipv), "Threads": str(config.threads)}
        if config.show_wdl or "UCI_ShowWDL" in self.settings:
            desired["UCI_ShowWDL"] = str(config.show_wdl).lower()
        for key, value in desired.items():
            if key not in self.options:
                raise GameError("teacher_protocol", f"Teacher does not support {key}.")
            if self.settings.get(key) != value:
                engine.send(f"setoption name {key} value {value}")
                self.settings[key] = value
        engine.send("ucinewgame")
        engine.send("isready")
        engine.until("readyok")
        engine.send("position startpos" + (" moves " + " ".join(game.moves) if game.moves else ""))
        engine.send(f"go nodes {config.nodes}" + (f" depth {config.depth}" if config.depth is not None else ""))
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
        legal = game.legal_moves if isinstance(game, GameView) else legal_moves(game.board, game.turn)
        if move not in legal:
            raise GameError("teacher_illegal_move", f"Teacher proposed a move rejected by qi: {move}")
        nodes, depth, score = read_info(info)
        return TeacherAnalysis(
            schema_version=2 if config.depth is None or config.multipv != 1 or config.show_wdl else 1,
            adapter_version=(
                "uci-teacher-v2" if config.depth is None or config.multipv != 1 or config.show_wdl else "uci-teacher-v1"
            ),
            snapshot=snapshot,
            state_hash=game.state_hash,
            move=move,
            engine_name=self.name,
            engine_sha256=self.identity.engine_sha256,
            network_sha256=self.identity.network_sha256,
            settings=self.settings,
            requested_nodes=config.nodes,
            requested_depth=config.depth,
            timeout_seconds=config.timeout_seconds,
            reported_nodes=nodes,
            reported_depth=depth,
            score=score if config.multipv == 1 else None,
            elapsed_ms=(perf_counter() - started) * 1000,
            search_info=info,
        )


def analyze(game: Game, config: TeacherConfig) -> TeacherAnalysis:
    with TeacherSession(config) as session:
        return session.analyze(game, config)
