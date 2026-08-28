"""Agent tools (R5: read-mostly surface). Every result carries evidence IDs
that the validator's C1 check binds to later."""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models import Detection
from pipeline.rag.retriever import retrieve
from pipeline.validator.engine import EvidenceIndex


@dataclass
class ToolContext:
    db: Session
    incident_id: str
    dataset_run_id: str
    mode: str = "production"  # production | evaluation (attack suite)
    index: EvidenceIndex = field(default_factory=EvidenceIndex)
    proposed: list[dict] = field(default_factory=list)

    def _register(self, *, tier: str, source: str, fields: dict | None = None,
                  text: str = "") -> str:
        eid = f"ev-{uuid.uuid4()}"
        self.index[eid] = {"tier": tier, "source": source,
                           "fields": fields or {}, "text": text[:1200]}
        return eid

    # -- telemetry tools ------------------------------------------------------
    def query_latest(self, args: dict) -> dict:
        rows = self._windows(limit=1)
        if not rows:
            ev = self._register(tier="trusted", source="tool:query_latest",
                                fields={}, text="no windows")
            return {"status": "NO_EVIDENCE", "evidence_ids": [ev]}
        d = rows[0]
        fields = {"score": round(d.score, 6)}
        for s in (d.top_sensors if hasattr(d, "top_sensors") else []):
            pass
        ev = self._register(tier="trusted", source="tool:query_latest", fields=fields)
        return {"window_start": str(d.window_start), "score": d.score,
                "evidence_ids": [ev]}

    def query_history(self, args: dict) -> dict:
        span = min(int(args.get("span", 10)), 60)  # AGENT-008 bound
        rows = self._windows(limit=span)
        out, evs = [], []
        for d in rows:
            ev = self._register(tier="trusted", source="tool:query_history",
                                fields={"score": round(d.score, 6)})
            evs.append(ev)
            out.append({"window_start": str(d.window_start), "score": d.score})
        if not out:
            ev = self._register(tier="trusted", source="tool:query_history")
            return {"status": "NO_EVIDENCE", "evidence_ids": [ev]}
        return {"windows": out, "evidence_ids": evs}

    def _windows(self, limit: int):
        incident_windows = (
            self.db.query(Detection)
            .filter(Detection.dataset_run_id == self.dataset_run_id)
            .order_by(Detection.window_start.desc())
            .limit(limit)
            .all()
        )
        return incident_windows

    # -- RAG tool ---------------------------------------------------------------
    def search_kb(self, args: dict) -> dict:
        res = retrieve(self.db, query=str(args.get("query", ""))[:500],
                       mode=self.mode, agent_run_id=None)
        ids = []
        for evd in res.get("evidence") or []:
            eid = self._register(tier=evd["tier"], source=f"rag:{evd['source']}",
                                 fields=evd.get("fields") or {}, text=evd["text"])
            evd["validator_evidence_id"] = eid
            ids.append(eid)
        res["evidence_ids"] = ids
        return res

    # -- invariants ---------------------------------------------------------------
    def check_invariant(self, args: dict) -> dict:
        from pipeline.detect.invariances import evaluate_invariants

        scores = [float(w["score"]) for w in self._windows(limit=60)] or [0.0]
        outcomes = evaluate_invariants({"scores": scores,
                                        "sensors": {}})
        ev = self._register(tier="trusted", source="tool:check_invariant",
                            fields={"failed_rules": outcomes["failed"]})
        return {**outcomes, "evidence_ids": [ev],
                "checked_at": dt.datetime.now(dt.UTC).isoformat()}

    # -- proposal -----------------------------------------------------------------
    def propose_action(self, args: dict) -> dict:
        step = {
            "step_no": len(self.proposed) + 1,
            "action": str(args.get("action")),
            "target": str(args.get("target")),
            "params": dict(args.get("params") or {}),
            "citations": list(dict.fromkeys(
                [str(c) for c in args.get("citations") or []])),
        }
        self.proposed.append(step)
        return {"accepted_for_draft": True, "step_no": step["step_no"],
                "note": "pre-validator draft"}


TOOL_TABLE: dict[str, str] = {
    "query_latest": "query_latest",
    "query_history": "query_history",
    "search_kb": "search_kb",
    "check_invariant": "check_invariant",
    "propose_action": "propose_action",
}


def dispatch(ctx: ToolContext, name: str, args: dict) -> dict:
    fn = getattr(ctx, TOOL_TABLE.get(name, ""), None)
    if fn is None:
        raise ValueError(f"unknown_tool:{name}")
    return fn(args)
