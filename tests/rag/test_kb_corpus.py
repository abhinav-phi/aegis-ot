"""KB corpus assertions: ≥10 playbooks, all parse, all trusted tier, build succeeds."""
from __future__ import annotations

from pathlib import Path

import pytest

KB_ROOT = Path("configs/kb")


def test_playbook_count():
    """RAG-01: ≥10 team-authored response playbooks (trusted tier)."""
    playbooks = sorted(KB_ROOT.glob("playbook_*.md"))
    assert len(playbooks) >= 10, f"found {len(playbooks)} playbooks, need ≥10"


def test_playbooks_parse_and_trusted():
    """Every playbook frontmatter parses and has tier=trusted."""
    from pipeline.rag.kb import _parse_doc

    for pb in sorted(KB_ROOT.glob("playbook_*.md")):
        parsed = _parse_doc(pb)
        assert parsed["meta"]["tier"] == "trusted", f"{pb.name} not trusted"
        assert parsed["meta"]["title"], f"{pb.name} missing title"
        assert parsed["text"], f"{pb.name} empty body"


@pytest.mark.parametrize("source",
                         [p.name for p in sorted(KB_ROOT.glob("playbook_*.md"))])
def test_playbook_source_frontmatter(source):
    """The source: field in frontmatter must match the actual filename."""
    pb = KB_ROOT / source
    raw = pb.read_text(encoding="utf-8")
    header, _ = raw.split("---", 2)[1].strip(), raw.split("---", 2)[-1]
    meta = {}
    for line in header.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    assert meta.get("source", "").endswith(source), f"{source}: source mismatch"


def test_build_kb_succeeds(db, monkeypatch):
    """build_kb completes without error on the full corpus (local store)."""
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "vector_store", "local")
    monkeypatch.setattr(s, "local_vector_root", ".test-vectors")

    # ensure a clean vector store path
    import shutil
    from pathlib import Path

    from pipeline.rag.kb import build_kb
    from pipeline.rag.vectorstore import LocalVectorStore

    p = Path(".test-vectors") / "aegis_kb_prod"
    if p.exists():
        shutil.rmtree(p)

    store = LocalVectorStore(".test-vectors")
    import pipeline.rag.retriever as rmod
    monkeypatch.setattr(rmod, "get_vector_store", lambda: store)

    count = build_kb(db)
    assert count >= 10, f"build_kb returned {count} docs, expected ≥10"


def test_no_hostile_in_corpus():
    """No hostile-tier documents in the production KB directory."""
    from pipeline.rag.kb import _parse_doc

    for md in sorted(KB_ROOT.glob("**/*.md")):
        parsed = _parse_doc(md)
        assert parsed["meta"].get("tier") != "hostile", \
            f"{md.name} is hostile — belongs in eval fixtures only"


def test_vectorstore_upsert_merges(monkeypatch):
    """Multiple upsert calls accumulate — they don't clobber."""
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "vector_store", "local")
    monkeypatch.setattr(s, "local_vector_root", ".test-merge")

    import shutil
    from pathlib import Path

    from pipeline.rag.vectorstore import LocalVectorStore

    p = Path(".test-merge")
    if p.exists():
        shutil.rmtree(p)
    store = LocalVectorStore(".test-merge")
    store.upsert("merge_test", ["a", "b"], ["hello", "world"],
                 [{"tier": "trusted"}, {"tier": "trusted"}])
    store.upsert("merge_test", ["c", "a"], ["third", "duplicate"],
                 [{"tier": "public"}, {"tier": "trusted"}])
    recs = store.query("merge_test", "hello", k=5)
    sources = {r.metadata["tier"] for r in recs}
    assert len(recs) == 3, f"expected 3 merged, got {len(recs)}"
    assert "trusted" in sources and "public" in sources
    shutil.rmtree(p, ignore_errors=True)


def test_build_kb_rebuilds_when_collection_wiped(db, monkeypatch):
    """build_kb detects a missing collection and re-seeds from DB."""
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "vector_store", "local")
    monkeypatch.setattr(s, "local_vector_root", ".test-wipe")

    import shutil
    from pathlib import Path

    import pipeline.rag.kb as kbmod
    import pipeline.rag.retriever as rmod
    from pipeline.rag.kb import _collection_present, build_kb
    from pipeline.rag.vectorstore import LocalVectorStore

    p = Path(".test-wipe")
    if p.exists():
        shutil.rmtree(p)
    store = LocalVectorStore(".test-wipe")
    monkeypatch.setattr(kbmod, "get_vector_store", lambda: store)
    monkeypatch.setattr(rmod, "get_vector_store", lambda: store)

    # First build populates DB + store
    n1 = build_kb(db)
    assert n1 > 0, "first build produced no docs"
    assert _collection_present(store, "aegis_kb_prod")

    # Wipe the store files, keep DB rows
    prod_dir = p / "aegis_kb_prod"
    shutil.rmtree(prod_dir, ignore_errors=True)
    assert not _collection_present(store, "aegis_kb_prod"), "collection should be gone"

    # Second build should re-seed from DB
    n2 = build_kb(db)
    assert n2 == 0, "second build should produce 0 new docs (existing in DB)"
    assert _collection_present(store, "aegis_kb_prod"), "collection must be restored"

    # Verify retrieval works
    recs = store.query("aegis_kb_prod", "high level alarm", k=5)
    assert len(recs) > 0, "retrieval should return results after re-index"

    # Clean up
    shutil.rmtree(p, ignore_errors=True)