"""Small generation adapter over the AB-DATA-007 collection; no alternate data store."""

from qi.protocol import Snapshot
from qi.teacher import TeacherAnalysis, TeacherConfig, TeacherIdentity
from qi.training_data.contracts import state_fingerprint
from qi.training_data.store import AnalysisPayload, AnalysisSpec, Collection, OccurrencePayload, RunPayload


def analysis_spec(config: TeacherConfig, identity: TeacherIdentity) -> AnalysisSpec:
    settings = {"Threads": str(config.threads), "Hash": "16", "MultiPV": str(config.multipv), "Ponder": "false"}
    if config.show_wdl:
        settings["UCI_ShowWDL"] = "true"
    return AnalysisSpec(
        supervision={
            "target": "legal-teacher-move-v1",
            "authority": "teacher-preference",
            "adapter": "uci-teacher-v2"
            if config.depth is None or config.multipv != 1 or config.show_wdl
            else "uci-teacher-v1",
            "engine_sha256": identity.engine_sha256,
            "network_sha256": identity.network_sha256,
            "settings": settings,
            "nodes": config.nodes,
            "depth": config.depth,
        },
        timeout_seconds=float(config.timeout_seconds),
    )


class CollectionIO:
    """Keep collection SQL details out of actor and sampler policies.

    The only adapter-specific write is bounded per-game telemetry in the existing
    extensible actor payload. It never changes a trajectory or identity column.
    """

    def __init__(self, collection: Collection):
        self.store = collection

    def continuation(self, prior_run: int | None, recipe: dict) -> dict[str, int]:
        """Freeze references to disposed work; never move or relabel prior rows.

        Only an explicit continuation may adopt a legacy split-guard failure.
        Generic failures and interrupted attempts remain eligible for regeneration.
        """
        if prior_run is None:
            return {}
        row = self.store.db.execute(
            "SELECT status,json(payload) FROM generation_runs WHERE id=?", (prior_run,)
        ).fetchone()
        if row is None or row[0] == "running":
            raise ValueError("Continuation requires an existing inactive run.")
        prior = RunPayload.model_validate_json(row[1])
        if prior.config.get("recipe") != recipe or prior.config.get("continued_from_run") is not None:
            raise ValueError("Continuation requires the identical recipe and a direct original run.")
        inherited = {}
        for row in self.store.db.execute(
            "SELECT id,logical_key,status,stop_reason,failure,trajectory,split FROM games WHERE run_id=? ORDER BY id",
            (prior_run,),
        ):
            eligible = row["status"] == "complete"
            if row["status"] == "failed" and (
                row["stop_reason"] == "rejected-trajectory"
                or (row["stop_reason"] == "error" and row["failure"] == "Exact trajectory crosses splits.")
            ):
                eligible = bool(
                    self.store.db.execute(
                        "SELECT 1 FROM games WHERE trajectory=? AND split!=? AND status='complete'",
                        (row["trajectory"], row["split"]),
                    ).fetchone()
                )
                if not eligible:
                    raise ValueError("Retained rejection no longer has its opposite-split evidence.")
            if eligible:
                game = self.store.game(row["id"])
                if "generation_result" not in game.actor or state_fingerprint(game.snapshot) != row["trajectory"]:
                    raise ValueError("Continuation requires finalized generation evidence.")
                game.snapshot.game()
                if row["logical_key"] in inherited:
                    raise ValueError("Ambiguous disposed identity in continuation.")
                inherited[row["logical_key"]] = row["id"]
        return inherited

    def rejected_game(self, run: int, key: str) -> int | None:
        row = self.store.db.execute(
            "SELECT id FROM games WHERE run_id=? AND logical_key=? "
            "AND status='failed' AND stop_reason='rejected-trajectory' ORDER BY id LIMIT 1",
            (run, key),
        ).fetchone()
        return row[0] if row else None

    def occurrence(self, game_id: int, snapshot: Snapshot, metadata=None) -> int:
        occurrence = self.store.occurrence(game_id, snapshot)
        if metadata:
            row = self.store.db.execute(
                "SELECT json(payload) FROM position_occurrences WHERE id=?", (occurrence,)
            ).fetchone()
            payload = OccurrencePayload.model_validate_json(row[0])
            for key, value in metadata.items():
                if key in payload.metadata and payload.metadata[key] != value:
                    raise ValueError("Occurrence metadata conflict: " + key)
                payload.metadata[key] = value
            with self.store.db:
                self.store.db.execute(
                    "UPDATE position_occurrences SET payload=jsonb(?) WHERE id=?",
                    (payload.model_dump_json(), occurrence),
                )
        return occurrence

    def validate_parent(self, source, excluded: set[str]):
        if source.parent_trajectory is None:
            return
        from qi.players.policy.encoding import input_key

        rows = self.store.db.execute(
            "SELECT id FROM games WHERE trajectory=? AND status='complete'", (source.parent_trajectory,)
        ).fetchall()
        if not rows:
            raise ValueError("Generated parent must be a completed trajectory in this collection.")
        for row in rows:
            parent = self.store.game(row[0])
            prefix = source.start.snapshot
            if (
                parent.family != source.start.family_id
                or parent.split != source.split
                or parent.snapshot.moves[: len(prefix.moves)] != prefix.moves
                or not len(parent.initial.moves) <= len(prefix.moves) < len(parent.snapshot.moves)
            ):
                raise ValueError("Generated start must preserve its parent's prefix, family and split.")
        if input_key(source.start.snapshot.game()) in excluded:
            raise ValueError("Generated start is a reserved observation.")

    def generated_start(self, game_id: int, ply: int):
        """Materialize a portable start descriptor before freezing the child recipe."""
        from qi.training_data.contracts import StartingPosition

        parent = self.store.game(game_id)
        status = self.store.db.execute("SELECT status FROM games WHERE id=?", (game_id,)).fetchone()[0]
        if status != "complete" or not len(parent.initial.moves) <= ply < len(parent.snapshot.moves) or ply == 0:
            raise ValueError("Choose a noninitial prefix within a completed parent's continuation.")
        trajectory = state_fingerprint(parent.snapshot)
        return StartingPosition(
            id=f"generated-{trajectory[:16]}-{ply}",
            version="1",
            family_id=parent.family,
            snapshot=Snapshot(moves=parent.snapshot.moves[:ply]),
            themes=parent.themes,
        ), trajectory

    def completed_game(self, run: int, key: str) -> int | None:
        row = self.store.db.execute(
            "SELECT id FROM games WHERE run_id=? AND logical_key=? AND status='complete'", (run, key)
        ).fetchone()
        return row[0] if row else None

    def record_game_result(self, game_id: int, result: dict):
        payload = self.store.game(game_id)
        payload.actor["generation_result"] = result
        with self.store.db:
            changed = self.store.db.execute(
                "UPDATE games SET payload=jsonb(?) WHERE id=? AND status='running'",
                (payload.model_dump_json(), game_id),
            )
            if changed.rowcount != 1:
                raise ValueError("Only a running game may finalize generation telemetry.")

    def success(self, occurrence: int, spec: AnalysisSpec) -> TeacherAnalysis | None:
        spec_id = self.store.spec(spec)
        row = self.store.first_success(occurrence, spec_id)
        if row is None:
            return None
        payload = self.store.db.execute("SELECT json(payload) FROM analyses WHERE id=?", (row[0],)).fetchone()[0]
        answer = AnalysisPayload.model_validate_json(payload).answer
        if answer is None or answer.snapshot != self.store.snapshot(occurrence):
            raise ValueError("Stored successful analysis differs from its occurrence.")
        return answer

    def retain(self, occurrence: int, answer: TeacherAnalysis):
        spec = AnalysisSpec.from_analysis(answer)
        if self.success(occurrence, spec) is None:
            attempt = self.store.begin_analysis(occurrence, self.store.spec(spec))
            try:
                self.store.finish_analysis(attempt, answer)
            except BaseException as exc:
                self.store.finish_analysis(attempt, failure=str(exc), raw=[answer.model_dump_json()])
                raise
