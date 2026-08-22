"""Incidents and MITRE ATT&CK for ICS mappings (TINTEL-01, CHG-DB-06/-14)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col
from app.db.models.enums import INCIDENT_STATUSES, SEVERITIES, check_in


_CLOSED_REASONS_SQL = "('resolved','no_action','escalated')"


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(check_in("status", INCIDENT_STATUSES), name="ck_incident_status_enum"),
        CheckConstraint(check_in("severity", SEVERITIES), name="ck_incident_severity_enum"),
        CheckConstraint(
            f"(status = 'closed') = (closed_reason IN {_CLOSED_REASONS_SQL})",
            name="ck_incident_closed_reason_pairing",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_runs.id"), nullable=False)
    start_ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    title: Mapped[str | None] = mapped_column(Text)
    closed_reason: Mapped[str | None] = mapped_column(String(16))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # CHG-DB-06
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )


Index("ix_incident_status", Incident.status)
Index("ix_incident_time", Incident.start_ts, Incident.end_ts)


class ThreatMapping(Base):
    __tablename__ = "threat_mappings"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_tm_confidence_range"),
        UniqueConstraint("incident_id", "technique_id", name="uq_tm_incident_technique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    technique_id: Mapped[str] = mapped_column(String(12), nullable=False)
    confidence: Mapped[float] = mapped_column(Double, nullable=False)
    basis: Mapped[dict] = mapped_column(json_col(), nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )
