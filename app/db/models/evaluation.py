"""Evaluation + audit tables (CHG-DB-12 injection_cases, CHG-DB-17 stage ledger)."""
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
from app.db.models.enums import EVAL_RUN_STATUSES, check_in


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[str] = mapped_column(String(24), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    dataset_run_ids: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    model_version_ids: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    stage_ledger: Mapped[dict] = mapped_column(json_col(), nullable=False, default=dict)  # CHG-DB-17
    heartbeat_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    llm_backend: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(check_in("status", EVAL_RUN_STATUSES), name="ck_evalrun_status_enum"),
        UniqueConstraint("experiment_id", "config_hash", "status",
                         name="uq_evalrun_exp_cfg_status"),
    )


class MetricRow(Base):
    __tablename__ = "metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_runs.id"))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Double, nullable=False)
    extra: Mapped[dict | None] = mapped_column(json_col())
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


Index("ix_metrics_run", MetricRow.evaluation_run_id, MetricRow.source)


class ChannelReduction(Base):
    """ROB-01/02 arm record (ROB-02)."""

    __tablename__ = "channel_reductions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_runs.id"), nullable=False)
    full_channel_model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_versions.id"), nullable=False
    )
    reduced_channel_model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_versions.id")
    )
    mask: Mapped[list] = mapped_column(json_col(), nullable=False)
    reduction_pct: Mapped[float] = mapped_column(Double, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics: Mapped[dict] = mapped_column(json_col(), nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


class InjectionCase(Base):
    """Per-case ground truth + outcome for the adversarial suite (DEC-020)."""

    __tablename__ = "injection_cases"
    __table_args__ = (
        UniqueConstraint("evaluation_run_id", "case_id", "variant",
                         name="uq_injcase_run_case_variant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_runs.id"))
    family: Mapped[str] = mapped_column(String(8), nullable=False)  # F1..F7
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    variant: Mapped[str] = mapped_column(String(24), nullable=False)
    gt_unsafe: Mapped[bool] = mapped_column(nullable=False)
    proposed_unsafe: Mapped[bool] = mapped_column(nullable=False, default=False)
    blocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    approved: Mapped[bool | None] = mapped_column()
    executed: Mapped[bool] = mapped_column(nullable=False, default=False)
    verdict: Mapped[str | None] = mapped_column(String(24))
    refusal: Mapped[bool] = mapped_column(nullable=False, default=False)
    extra: Mapped[dict | None] = mapped_column(json_col())
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


class AuditLog(Base):
    """Append-only audit trail (INV-013). No UPDATE/DELETE grants (CHG-DB-19)."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(String(36))
    before: Mapped[dict | None] = mapped_column(json_col())
    after: Mapped[dict | None] = mapped_column(json_col())
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="-")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


Index("ix_audit_actor", AuditLog.actor_id, AuditLog.created_at)
Index("ix_audit_entity", AuditLog.entity_type, AuditLog.entity_id)
