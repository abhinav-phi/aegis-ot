"""Immutable plan revisions + validator results (DEC-001, CHG-DB-07/-08).

A mitigation plan, once inserted, is immutable: `steps`, `steps_hash`,
`incident_id`, `agent_run_id`, `revision_no`, `supersedes_id` are protected by
an ORM event listener (app/db/immutability.py) AND a PostgreSQL BEFORE UPDATE
trigger (migration 0002). Amendments create NEW revision rows.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col
from app.db.models.enums import PLAN_STATUSES, VERDICTS, check_in


class MitigationPlan(Base):
    __tablename__ = "mitigation_plans"
    __table_args__ = (
        CheckConstraint(check_in("status", PLAN_STATUSES), name="ck_plan_status_enum"),
        UniqueConstraint("agent_run_id", "revision_no", name="uq_plan_run_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    revision_no: Mapped[int] = mapped_column(nullable=False, default=1)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mitigation_plans.id"))
    steps: Mapped[list] = mapped_column(json_col(), nullable=False)
    steps_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # DEC-001
    canonical_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)   # HASH-001/002
    revision_created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # SEC-002
    execution_lease_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # APP-002
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft_for_validation")
    active_validator_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("validator_results.id", use_alter=True)
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


class ValidatorResult(Base):
    __tablename__ = "validator_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mitigation_plans.id"), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # CHG-DB-08
    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    checks: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    risk_classes: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    c5_category: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # CHG-DB-08
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


ValidatorResult.__table__.append_constraint(
    CheckConstraint(check_in("verdict", VERDICTS), name="ck_vr_verdict_enum")
)
