"""RAG tables: documents, chunks, retrieval events (CHG-DB-15/-16)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col


class RagDocument(Base):
    __tablename__ = "rag_documents"
    __table_args__ = (UniqueConstraint("source", "version", name="uq_ragdoc_source_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False, default="trusted")
    doc_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    superseded: Mapped[bool] = mapped_column(nullable=False, default=False)
    collection: Mapped[str] = mapped_column(String(64), nullable=False, default="aegis_kb_prod")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("chroma_id", name="uq_ragchunk_chroma_id"),
        UniqueConstraint("document_id", "chunk_hash", name="uq_ragchunk_doc_hash"),  # CHG-DB-16
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rag_documents.id"), nullable=False)
    chroma_id: Mapped[str] = mapped_column(String(80), nullable=False)
    section: Mapped[str | None] = mapped_column(String(300))
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


Index("ix_chunk_doc", RagChunk.document_id)


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"))
    collection: Mapped[str] = mapped_column(String(64), nullable=False, default="aegis_kb_prod")
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    query_text: Mapped[str | None] = mapped_column(Text)
    top_chunk_ids: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    tiers_retrieved: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )
