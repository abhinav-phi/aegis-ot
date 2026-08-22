"""Agent run + message tables (CHG-DB-13: lease + single-active-run)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col
from app.db.models.enums import AGENT_RUN_STATUSES, AGENT_VARIANTS, check_in


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(check_in("status", AGENT_RUN_STATUSES), name="ck_agentrun_status_enum"),
        CheckConstraint(check_in("variant", AGENT_VARIANTS), name="ck_agentrun_variant_enum"),
        # INV-015 / DEC-005: at most one active run per incident.
        Index("uq_agent_runs_active_per_incident", "incident_id", unique=True,
              postgresql_where=text("status = 'running'"),
              sqlite_where=text("status = 'running'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    variant: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lease_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    ended_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


Index("ix_agent_incident", AgentRun.incident_id, AgentRun.started_at)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # system|assistant|tool|user
    tool_name: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(json_col(), nullable=False)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )


Index("ix_msg_run", AgentMessage.agent_run_id, AgentMessage.created_at)

# role enum via CHECK
AgentMessage.__table__.append_constraint(
    CheckConstraint("role IN ('system','assistant','tool','user')", name="ck_msg_role_enum")
)
