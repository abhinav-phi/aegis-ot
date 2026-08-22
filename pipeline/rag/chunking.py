"""Heading-aware chunking (~200-400 words, overlap 32) with chunk hashes."""
from __future__ import annotations

import hashlib
import re

from app.core.canonical import content_hash

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")


def _split_headings(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title, buffer = "preamble", []
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            if buffer:
                sections.append((current_title, "\n".join(buffer)))
            current_title = m.group(2).strip()
            buffer = []
        else:
            buffer.append(line)
    if buffer:
        sections.append((current_title, "\n".join(buffer)))
    return [(t, b.strip()) for t, b in sections if b.strip()]


def chunk_document(text: str, *, target_words: int = 300, min_words: int = 80,
                   overlap: int = 32) -> list[dict]:
    chunks: list[dict] = []
    for section_title, body in _split_headings(text):
        words = body.split()
        if not words:
            continue
        start = 0
        idx = 0
        while start < len(words):
            piece = words[start:start + target_words]
            if len(piece) >= min_words or start == 0:
                text_piece = " ".join(piece)
                chunks.append({
                    "section": section_title,
                    "text": text_piece,
                    "token_count": len(piece),
                    "chunk_hash": content_hash({"section": section_title, "text": text_piece}),
                })
                idx += 1
            if start + target_words >= len(words):
                break
            start += target_words - overlap
    # Global dedupe by content hash.
    seen: set[str] = set()
    unique = [c for c in chunks if not (c["chunk_hash"] in seen or seen.add(c["chunk_hash"]))]
    return unique


def doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
