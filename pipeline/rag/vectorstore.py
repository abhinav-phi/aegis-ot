"""Vector store abstraction: in-process deterministic store + Chroma adapter.

Collections are named per mode: `aegis_kb_prod` (trusted/public only) and
`aegis_kb_eval_{run}` (attack fixtures). Collection separation is the R11
boundary — the retriever additionally hard-filters tiers.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from pipeline.rag.embeddings import get_embedder


class VectorRecord:
    def __init__(self, chroma_id: str, text: str, metadata: dict, score: float = 0.0):
        self.id = chroma_id
        self.text = text
        self.metadata = metadata
        self.score = score


class LocalVectorStore:
    """Deterministic in-process cosine store persisted under local_vector_root."""

    def __init__(self, root: str):
        self.root = Path(root)
        self._collections: dict[str, dict] = {}

    def _dir(self, collection: str) -> Path:
        p = self.root / collection
        p.mkdir(parents=True, exist_ok=True)
        return p

    def upsert(self, collection: str, ids: list[str], texts: list[str],
               metadatas: list[dict]) -> None:
        emb = get_embedder()
        vectors = emb.embed(texts)
        d = self._dir(collection)
        vec_file, store_file = d / "vectors.npy", d / "store.json"
        if vec_file.exists() and store_file.exists():
            # Merge semantics: existing ids are kept as-is (first write wins),
            # new ids are appended. Matches the Chroma adapter's upsert and
            # makes multi-call builders (build_kb upserts per document) safe.
            old_vectors = np.load(vec_file)
            old_store = json.loads(store_file.read_text(encoding="utf-8"))
            seen = set(old_store["ids"])
            merged_ids = list(old_store["ids"])
            merged_texts = list(old_store["texts"])
            merged_metas = list(old_store["metas"])
            new_vecs: list[np.ndarray] = []
            for cid, text, meta, vec in zip(ids, texts, metadatas, vectors):
                if cid in seen:
                    continue
                seen.add(cid)
                merged_ids.append(cid)
                merged_texts.append(text)
                merged_metas.append(meta)
                new_vecs.append(vec)
            if not new_vecs:
                return
            vectors = np.vstack([old_vectors, np.asarray(new_vecs, dtype=np.float32)])
            store = {"ids": merged_ids, "texts": merged_texts,
                     "metas": merged_metas}
        else:
            store = {"ids": ids, "texts": texts, "metas": metadatas}
        np.save(d / "vectors.npy", vectors)
        (d / "store.json").write_text(
            json.dumps(store, ensure_ascii=False), encoding="utf-8"
        )

    def query(self, collection: str, query_text: str, k: int = 5,
              where_tiers: list[str] | None = None) -> list[VectorRecord]:
        import json

        d = self._dir(collection)
        vec_file, store_file = d / "vectors.npy", d / "store.json"
        if not vec_file.exists() or not store_file.exists():
            raise FileNotFoundError(f"collection_missing:{collection}")
        vectors = np.load(vec_file)
        store = json.loads(store_file.read_text(encoding="utf-8"))
        q = get_embedder().embed([query_text])[0]
        scores = vectors @ q
        order = np.argsort(-scores)
        out: list[VectorRecord] = []
        for i in order:
            meta = store["metas"][int(i)]
            if where_tiers is not None and meta.get("tier") not in where_tiers:
                continue
            out.append(VectorRecord(store["ids"][int(i)], store["texts"][int(i)],
                                    meta, float(scores[int(i)])))
            if len(out) >= k:
                break
        return out


class ChromaVectorStore:
    def __init__(self, host: str, port: int):
        import chromadb  # optional dependency

        self.client = chromadb.HttpClient(host=host, port=port)

    def upsert(self, collection: str, ids: list[str], texts: list[str],
               metadatas: list[dict]) -> None:
        col = self.client.get_or_create_collection(collection)
        emb = get_embedder()
        col.upsert(ids=ids, documents=texts, metadatas=metadatas,
                   embeddings=emb.embed(texts).tolist())

    def query(self, collection: str, query_text: str, k: int = 5,
              where_tiers: list[str] | None = None) -> list[VectorRecord]:
        col = self.client.get_collection(collection)
        emb = get_embedder()
        where = {"tier": {"$in": where_tiers}} if where_tiers else None
        res = col.query(query_embeddings=emb.embed([query_text]).tolist(),
                        n_results=k, where=where)
        out = []
        for i, cid in enumerate(res["ids"][0]):
            out.append(VectorRecord(cid, res["documents"][0][i],
                                    res["metadatas"][0][i], float(res["distances"][0][i])))
        return out


def get_vector_store():
    from app.core.config import get_settings

    s = get_settings()
    if s.vector_store == "chroma":
        return ChromaVectorStore(s.chroma_host, s.chroma_port)
    return LocalVectorStore(s.local_vector_root)
