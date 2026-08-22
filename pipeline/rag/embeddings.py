"""Embedders. Pinned per collection for reproducibility (DEC-017).

Default offline backend: deterministic feature-hashing embedder (no external
deps, stable across machines). Sentence-transformers used automatically when
installed AND configured; the active name+version is always recorded with the
collection so retrieval results are reproducible.
"""
from __future__ import annotations

import hashlib

import numpy as np

EMBEDDING_BACKEND = "aegis-hashing-embedder-v1"
DIM = 256


class Embedder:
    name = EMBEDDING_BACKEND
    dim = DIM

    def embed(self, texts: list[str]) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError


class HashingEmbedder(Embedder):
    """Deterministic bag-of-3-gram feature hashing, L2-normalized."""

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            norm = t.lower()
            grams = [norm[j:j + 3] for j in range(max(1, len(norm) - 2))]
            for g in grams:
                h = int.from_bytes(hashlib.md5(g.encode()).digest()[:8], "little")
                out[i, h % self.dim] += 1.0
            n = float(np.linalg.norm(out[i]))
            if n > 0:
                out[i] /= n
        return out


def get_embedder() -> Embedder:
    try:  # optional upgrade path; pinned name recorded either way
        from sentence_transformers import SentenceTransformer  # type: ignore

        class ST(Embedder):
            name = "all-MiniLM-L6-v2"

            def __init__(self):
                self._m = SentenceTransformer("all-MiniLM-L6-v2")
                self.dim = int(self._m.get_sentence_embedding_dimension())

            def embed(self, texts):
                v = self._m.encode(texts, normalize_embeddings=True)
                import numpy as np

                return np.asarray(v, dtype=np.float32)

        return ST()
    except Exception:
        return HashingEmbedder()


def embed_query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()
