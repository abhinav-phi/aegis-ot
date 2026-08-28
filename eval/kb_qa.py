"""RAG-04 retrieval QA: 20 canned queries with expected-source ground truth."""
from __future__ import annotations

from datetime import UTC

CANNED_QUERIES: list[dict] = [
    {"q": "high level alarm response procedure", "expect_source_contains": ["SPD-017", "playbook"]},
    {"q": "pump speed reduction steps", "expect_source_contains": ["SPD-017"]},
    {"q": "level sensor false reading verification", "expect_source_contains": ["SPD-017"]},
    {"q": "T0875 technique description", "expect_source_contains": ["mitre"]},
    {"q": "supply pump compromise technique", "expect_source_contains": ["mitre"]},
    {"q": "process manipulation ATT&CK ICS", "expect_source_contains": ["mitre"]},
    {"q": "valve flow consistency check", "expect_source_contains": ["plant-manual", "invariant"]},
    {"q": "tank level operating range", "expect_source_contains": ["plant-manual"]},
    {"q": "MV-501 valve purpose", "expect_source_contains": ["plant-manual"]},
    {"q": "incident response first steps OT", "expect_source_contains": ["playbook"]},
    {"q": "when to escalate an incident", "expect_source_contains": ["playbook"]},
    {"q": "who approves control actions", "expect_source_contains": ["playbook", "policy"]},
    {"q": "sandbox execution meaning", "expect_source_contains": ["plant-manual", "policy"]},
    {"q": "LIT-101 sensor semantics", "expect_source_contains": ["plant-manual"]},
    {"q": "FIT-101 flow range", "expect_source_contains": ["plant-manual"]},
    {"q": "maintenance ticket workflow", "expect_source_contains": ["playbook"]},
    {"q": "invariant R4 meaning", "expect_source_contains": ["plant-manual", "invariant"]},
    {"q": "unauthorized command message detection", "expect_source_contains": ["mitre"]},
    {"q": "water treatment stage 6", "expect_source_contains": ["plant-manual"]},
    {"q": "verify invariants before action", "expect_source_contains": ["playbook"]},
]

assert len(CANNED_QUERIES) == 20


def evaluate_retriever(retrieve_fn) -> dict:
    """hit-rate@5 and MRR against expected source substrings."""
    hits, rr = 0, []
    for item in CANNED_QUERIES:
        res = retrieve_fn(item["q"])
        rank = 0
        for pos, cite in enumerate((res.get("citations") or [])[:5], start=1):
            src = str(cite.get("source", "")).lower()
            if any(exp.lower() in src for exp in item["expect_source_contains"]):
                rank = pos
                break
        if rank:
            hits += 1
            rr.append(1.0 / rank)
        else:
            rr.append(0.0)
    return {"hit_rate_at_5": hits / len(CANNED_QUERIES),
            "mrr": sum(rr) / len(rr), "n_queries": len(CANNED_QUERIES)}


def run_kb_qa(db, *, created_by=None) -> dict:
    """RAG-04 corpus run: build the production KB from configs/kb (trusted +
    public only — hostile content rejected by the builder per R11), then score
    retrieval on the 20 canned queries. Metrics land in evaluation_runs/metrics.
    """
    from datetime import datetime

    from sqlalchemy.orm import Session  # noqa: F401

    from app.core.canonical import content_hash
    from app.db.models import MetricRow
    from pipeline.rag.kb import build_kb
    from pipeline.rag.retriever import retrieve

    docs_built = build_kb(db)

    def _retrieve(q: str) -> dict:
        return retrieve(db, query=q, mode="production")

    scores = evaluate_retriever(_retrieve)
    config_hash = content_hash({"rag04": "canned20", "docs": docs_built})
    from eval.experiments import _open_run

    run = _open_run(db, experiment_id="RAG-04", config_hash=config_hash,
                    notes=f"corpus run over configs/kb ({docs_built} docs)",
                    llm_backend=None, created_by=created_by)
    db.query(MetricRow).filter(MetricRow.evaluation_run_id == run.id).delete()
    for name, value in scores.items():
        db.add(MetricRow(evaluation_run_id=run.id, source="rag",
                         metric_name=name, value=float(value)))
    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    db.flush()
    return {"evaluation_run_id": str(run.id), "documents": docs_built, **scores}


if __name__ == "__main__":  # pragma: no cover
    from app.db.session import SessionLocal, ensure_lite_schema

    ensure_lite_schema()
    with SessionLocal() as _db:
        _result = run_kb_qa(_db)
        _db.commit()
        print(_result)
