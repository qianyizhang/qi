"""Frozen benchmark identities and deterministic, reusable paired game slots."""

from dataclasses import replace
from itertools import combinations
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qi.artifacts import digest
from qi.evaluation import Corpus, EvalSpec, Opening
from qi.players import PlayerConfig, bind_config
from qi.players.catalog import get_player
from qi.protocol import Snapshot

Identifier = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @property
    def sha256(self) -> str:
        return digest(self.model_dump(mode="json"))


class BookStart(Record):
    id: Identifier
    family: str = Field(min_length=1)
    source_game: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    description: str = Field(min_length=1)
    snapshot: Snapshot


class Book(Record):
    schema_version: Literal[1] = 1
    id: Identifier
    use: Literal["development", "locked-test", "smoke"]
    provenance: str = Field(min_length=1)
    selection: str = Field(min_length=1)
    starts: list[BookStart] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_starts(self) -> Self:
        ids, boards = set(), set()
        for start in self.starts:
            game = start.snapshot.game()
            board = (game.board, game.turn)
            if game.outcome or start.id in ids or board in boards:
                raise ValueError("Book starts must be nonterminal with unique IDs and board/turn states.")
            if not game.moves and self.use != "smoke":
                raise ValueError("The initial board is a separate diagnostic, not a rated book start.")
            ids.add(start.id)
            boards.add(board)
        return self

    def corpus(self, ids: list[str]) -> Corpus:
        starts = {start.id: start for start in self.starts}
        return Corpus(
            id=self.id,
            provenance=self.provenance,
            openings=[Opening(id=id, description=starts[id].description, snapshot=starts[id].snapshot) for id in ids],
        )


class Entrant(Record):
    id: Identifier
    label: str = Field(min_length=1)
    config: PlayerConfig
    player_version: str = ""

    @property
    def identity(self) -> str:
        return digest({"config": self.model_dump(mode="json")["config"], "player_version": self.player_version})

    def freeze(self) -> "Entrant":
        config = bind_config(self.config)
        version = get_player(config.kind).info.version
        if self.player_version and self.player_version != version:
            raise ValueError(f"Player version changed for {self.id}.")
        return self.model_copy(update={"config": config, "player_version": version})


class RatingMethod(Record):
    id: Literal["davidson-map-v1"] = "davidson-map-v1"
    anchor_elo: Literal[1000] = 1000
    strength_prior_sd: Literal[800] = 800
    red_prior_sd: Literal[400] = 400
    draw_prior_sd: Literal[2] = 2
    bootstrap_replicates: Literal[200] = 200
    bootstrap_seed: int = 731
    minimum_families: Literal[8] = 8


class BenchmarkSeries(Record):
    schema_version: Literal[1] = 1
    id: Identifier
    label: str = Field(min_length=1)
    book: Book
    references: list[Entrant] = Field(min_length=2)
    anchor: Identifier
    rating: RatingMethod = Field(default_factory=RatingMethod)

    @model_validator(mode="after")
    def valid_panel(self) -> Self:
        ids = [p.id for p in self.references]
        if len(set(ids)) != len(ids) or self.anchor not in ids:
            raise ValueError("Reference IDs must be unique and include the anchor.")
        if len({p.identity for p in self.references}) != len(ids):
            raise ValueError("Duplicate reference configurations do not define different entrants.")
        return self


class BenchmarkSpec(Record):
    schema_version: Literal[1] = 1
    protocol: Literal["benchmark-pairs-v1"] = "benchmark-pairs-v1"
    series: BenchmarkSeries
    mode: Literal["round-robin", "gauntlet"] = "round-robin"
    candidates: list[Entrant] = Field(default_factory=list)
    starts: list[str] = Field(min_length=1)
    standard_start: bool = True
    heldout_evidence: str = "Not audited against entrant training data; no certified held-out claim."

    @property
    def entrants(self) -> dict[str, Entrant]:
        return {p.id: p for p in self.series.references + self.candidates}

    @model_validator(mode="after")
    def valid_plan(self) -> Self:
        all_players = self.series.references + self.candidates
        if len(self.entrants) != len(all_players) or len({p.identity for p in all_players}) != len(all_players):
            raise ValueError("Entrant IDs and pinned configurations must be unique.")
        if self.mode == "gauntlet" and not self.candidates:
            raise ValueError("A gauntlet needs at least one candidate.")
        if self.mode == "round-robin" and self.candidates:
            raise ValueError("Bootstrap round robin contains references only; add candidates through a gauntlet.")
        known = {s.id for s in self.series.book.starts}
        if len(set(self.starts)) != len(self.starts) or not set(self.starts) <= known:
            raise ValueError("Selected starts must be unique entries in the series book.")
        return self

    def freeze(self) -> "BenchmarkSpec":
        series = self.series.model_copy(update={"references": [p.freeze() for p in self.series.references]})
        return BenchmarkSpec.model_validate(
            self.model_copy(
                update={
                    "series": series,
                    "candidates": [p.freeze() for p in self.candidates],
                }
            ).model_dump()
        )

    def matchups(self) -> list[tuple[str, str]]:
        # A gauntlet retains the supporting reference matrix as reusable evidence.
        return list(combinations(sorted(self.entrants), 2))

    def slots(self) -> list["GameSlot"]:
        indexed = {s.id: (i, s, False) for i, s in enumerate(self.series.book.starts)}
        starts = [indexed[id] for id in self.starts]
        if self.standard_start:
            starts.append(
                (
                    len(self.series.book.starts),
                    BookStart(
                        id="standard-initial",
                        family="standard-initial",
                        source_game="standard-initial",
                        source_url="qi:xiangqi-training-v1",
                        description="Standard initial board diagnostic",
                        snapshot=Snapshot(),
                    ),
                    True,
                )
            )
        result = []
        for a, b in self.matchups():
            for index, start, diagnostic in starts:
                for side in ("red", "black"):
                    ca = replace(self.entrants[a].config, seed=self.entrants[a].config.seed + 2 * index)
                    cb = replace(self.entrants[b].config, seed=self.entrants[b].config.seed + 2 * index)
                    key = digest(
                        {
                            "series": self.series.sha256,
                            "a": self.entrants[a].identity,
                            "b": self.entrants[b].identity,
                            "start": start.sha256,
                            "side": side,
                        }
                    )
                    result.append(
                        GameSlot(
                            id=key, a=a, b=b, a_side=side, start=start, diagnostic=diagnostic, config_a=ca, config_b=cb
                        )
                    )
        return result


class GameSlot(Record):
    id: str
    a: str
    b: str
    a_side: Literal["red", "black"]
    start: BookStart
    diagnostic: bool
    config_a: PlayerConfig
    config_b: PlayerConfig

    def evaluation_spec(self) -> EvalSpec:
        return EvalSpec(
            schema_version=2 if self.config_a.binding_sha256 or self.config_b.binding_sha256 else 1,
            corpus=Corpus(
                id=self.start.id,
                provenance=self.start.source_url,
                openings=[
                    Opening(
                        id=self.start.id,
                        description=self.start.description,
                        snapshot=self.start.snapshot,
                    )
                ],
            ),
            player_a=self.config_a,
            player_b=self.config_b,
        )
