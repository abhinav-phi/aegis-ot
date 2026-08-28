"""KB builder: loads configs/kb markdown corpus into DB + vector store.

Production corpus contains ONLY trusted/public documents (R11). Hostile
fixtures are built separately into eval collections by the attack suite.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RagChunk, RagDocument
from pipeline.rag.chunking import chunk_document, doc_hash
from pipeline.rag.retriever import PROD_COLLECTION
from pipeline.rag.vectorstore import get_vector_store

FRONTMATTER_SEP = "---"


def _parse_doc(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta: dict = {"tier": "trusted", "title": path.stem, "source": f"configs/kb/{path.name}"}
    if text.startswith(FRONTMATTER_SEP):
        _, header, body = text.split(FRONTMATTER_SEP, 2)
        for line in header.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        text = body
    return {"meta": meta, "text": text}


def _collection_present(store, collection: str) -> bool:
    try:
        store.query(collection, "probe", k=1)
        return True
    except FileNotFoundError:
        return False


def _reindex_from_db(db: Session, store, collection: str) -> None:
    """Re-seed a wiped vector collection from DB rows (idempotent, INV-016).

    build_kb is DB-idempotent: on a re-run it skips documents whose
    doc_hash already exists, so if the vector collection was removed
    (e.g. store wiped between runs) it would otherwise never be rebuilt.
    """
    from sqlalchemy import select

    rows = db.execute(
        select(RagChunk, RagDocument)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .where(RagDocument.collection == collection)
    ).all()
    if not rows:
        return
    ids, texts, metas = [], [], []
    for chunk, doc in rows:
        ids.append(chunk.chroma_id)
        texts.append(chunk.chunk_text)
        metas.append({"tier": doc.tier, "source": doc.source,
                      "section": chunk.section, "doc_key": doc.source,
                      "chunk_db_id": str(chunk.id),
                      "fields": {}})
    store.upsert(collection, ids, texts, metas)


def build_kb(db: Session, *, collection: str = PROD_COLLECTION,
             root: Path = Path("configs/kb")) -> int:
    if collection != PROD_COLLECTION:
        raise ValueError("build_kb is production-only; hostile fixtures use the eval builder")
    store = get_vector_store()
    if not _collection_present(store, collection):
        _reindex_from_db(db, store, collection)
    count = 0
    for md in sorted(Path(root).glob("**/*.md")):
        parsed = _parse_doc(md)
        tier = parsed["meta"].get("tier", "trusted")
        if tier == "hostile":
            raise ValueError(f"hostile doc {md} may never enter the production corpus")
        dhash = doc_hash(parsed["text"])
        existing = db.execute(
            select(RagDocument).where(RagDocument.doc_hash == dhash,
                                      RagDocument.collection == collection)
        ).scalar_one_or_none()
        if existing:
            continue
        doc = RagDocument(
            title=parsed["meta"].get("title", md.stem),
            source=parsed["meta"].get("source", md.name),
            tier=tier, doc_hash=dhash, version=1, collection=collection,
        )
        db.add(doc)
        db.flush()
        chunks = chunk_document(parsed["text"])
        ids, texts, metas = [], [], []
        for i, ch in enumerate(chunks):
            chroma_id = f"{doc.id}:{i}"
            db.add(RagChunk(
                document_id=doc.id, chroma_id=chroma_id, section=ch["section"],
                chunk_text=ch["text"], chunk_hash=ch["chunk_hash"],
                token_count=ch["token_count"],
            ))
            ids.append(chroma_id)
            texts.append(ch["text"])
            metas.append({
                "tier": tier, "source": doc.source, "section": ch["section"],
                "doc_key": doc.source, "chunk_db_id": str(ch["id"]) if hasattr(ch, "id") else None,
                "fields": parsed["meta"].get("fields") or {},
            })
        if ids:
            # chunk_db_id needs the DB ids; flush then re-fetch (autoflush off).
            db.flush()
            rows = db.execute(select(RagChunk).where(RagChunk.document_id == doc.id)).scalars()
            by_id = {r.chroma_id: str(r.id) for r in rows}
            metas = [{**m, "chunk_db_id": by_id[i]} for i, m in zip(ids, metas)]
            store.upsert(collection, ids, texts, metas)
        count += 1
    db.flush()
    return count


def _fixture_source(run_key: str, title: str) -> str:
    """UNIQUE(source, version) requires one row per (source) within a run."""
    slug = "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")
    return f"fixture:{run_key}:{slug}"


def build_eval_fixture_kb(db: Session, *, run_key: str, docs: list[dict]) -> str:
    """Hostile fixture builder (RAG-06): eval collection ONLY."""
    collection = f"aegis_kb_eval_{run_key}"
    store = get_vector_store()
    ids, texts, metas = [], [], []
    doc_ids: list[str] = []
    for d in docs:
        dhash = doc_hash(d["text"])
        doc = RagDocument(
            title=d["title"], source=d.get("source") or _fixture_source(run_key, d["title"]),
            tier=d.get("tier", "hostile"), doc_hash=dhash, version=1,
            collection=collection,
        )
        db.add(doc)
        db.flush()
        doc_ids.append(doc.id)
        for i, ch in enumerate(chunk_document(d["text"])):
            chroma_id = f"{doc.id}:{i}"
            db.add(RagChunk(
                document_id=doc.id, chroma_id=chroma_id, section=ch["section"],
                chunk_text=ch["text"], chunk_hash=ch["chunk_hash"],
                token_count=ch["token_count"],
            ))
            ids.append(chroma_id)
            texts.append(ch["text"])
            metas.append({"tier": d.get("tier", "hostile"), "source": doc.source,
                          "section": ch["section"], "doc_key": doc.source,
                          "fields": d.get("fields") or {}})
    if ids:
        # Persist chunks first so citation identity can be resolved from the DB.
        db.flush()
        rows = db.execute(
            select(RagChunk).where(RagChunk.document_id.in_(doc_ids))
        ).scalars()
        by_id = {r.chroma_id: str(r.id) for r in rows}
        metas = [{**m, "chunk_db_id": by_id[i]} for i, m in zip(ids, metas)]
        store.upsert(collection, ids, texts, metas)
    db.flush()
    return collection
