"""Trust-firewalled retriever (R11, DEC-010, INV-012).

Production mode hard-excludes `hostile` EVEN IF the caller requests it — the
requested filter is intersected with the mode allowlist and denials are
recorded. Evaluation mode may include hostile but only against an eval
collection (enforced here, not by convention).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.canonical import content_hash
from app.core.logging import get_logger
from app.db.models import RagChunk, RagDocument, RetrievalEvent
from pipeline.rag.vectorstore import get_vector_store

log = get_logger("aegis.rag")

PROD_COLLECTION = "aegis_kb_prod"
MODE_ALLOWLIST = {
    "production": ("trusted", "public"),
    "evaluation": ("trusted", "public", "hostile"),
}

RETRIEVAL_UNAVAILABLE = "RETRIEVAL_UNAVAILABLE"
NO_EVIDENCE = "NO_EVIDENCE"


def retrieve(db: Session | None, *, query: str, mode: str = "production",
             requested_tiers: list[str] | None = None, k: int = 5,
             agent_run_id=None) -> dict:
    """Returns {status, citations:[...], evidence:[...]}.

    status ∈ ok | no_evidence | retrieval_unavailable | tier_denied
    """
    allow = set(MODE_ALLOWLIST.get(mode, MODE_ALLOWLIST["production"]))
    tiers = [t for t in (requested_tiers or list(allow)) if t in allow]
    # Denials are recorded on EVERY outcome path — even when retrieval itself
    # is unavailable — so a hostile request can never pass silently (INV-012).
    denied = bool(set(requested_tiers or []) - allow)
    collection = PROD_COLLECTION if mode == "production" else "aegis_kb_eval"

    started = dt.datetime.now(dt.UTC)
    try:
        store = get_vector_store()
        records = store.query(collection, query, k=k, where_tiers=tiers or None)
    except FileNotFoundError as e:
        result = {"status": RETRIEVAL_UNAVAILABLE, "citations": [], "evidence": [],
                  "flag": "TIER_DENIED" if denied else str(e)}
        _record_event(db, agent_run_id, collection, query, [], [], "retrieval_unavailable", started)
        return result
    except Exception as e:  # any backend failure degrades, never fabricates
        log.warning("rag.backend_failure", exc_info=e)
        result = {"status": RETRIEVAL_UNAVAILABLE, "citations": [], "evidence": []}
        if denied:
            result["flag"] = "TIER_DENIED"
        _record_event(db, agent_run_id, collection, query, [], [], "retrieval_unavailable", started)
        return result

    # DB-backed citation identity + stale-version metadata.
    citations, evidence = [], []
    for rec in records:
        chunk = db.get(RagChunk, rec.metadata.get("chunk_db_id")) if db else None
        doc = db.get(RagDocument, chunk.document_id) if chunk else None
        stale = bool(doc and doc.superseded)
        cid = f"ev-{rec.id}"
        tier = rec.metadata.get("tier", "public")
        citations.append({
            "evidence_id": cid, "chunk_id": rec.id,
            "doc_id": str(doc.id) if doc else rec.metadata.get("doc_key"),
            "source": rec.metadata.get("source"), "section": rec.metadata.get("section"),
            "tier": tier, "score": round(rec.score, 4), "stale": stale,
        })
        evidence.append({
            "evidence_id": cid, "tier": tier, "source": rec.metadata.get("source"),
            "fields": rec.metadata.get("fields") or {}, "text": rec.text[:1200],
            "stale": stale,
        })

    _record_event(db, agent_run_id, collection, query,
                  [c["chunk_id"] for c in citations], [c["tier"] for c in citations],
                  "ok" if citations else "no_evidence", started)
    status = "ok" if citations else NO_EVIDENCE
    result = {"status": status, "citations": citations, "evidence": evidence}
    if denied:
        result["flag"] = "TIER_DENIED"  # hostile requested outside evaluation mode
    return result


def _record_event(db, agent_run_id, collection, query, chunk_ids, tiers, status, started) -> None:
    if db is None:
        return
    latency = int((dt.datetime.now(dt.UTC) - started).total_seconds() * 1000)
    db.add(RetrievalEvent(
        agent_run_id=agent_run_id, collection=collection,
        query_hash=content_hash(query), query_text=query[:2000],
        top_chunk_ids=chunk_ids, tiers_retrieved=tiers, status=status,
        latency_ms=latency,
    ))
    db.flush()
