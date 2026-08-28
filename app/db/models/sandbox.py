"""Simulated actions (CHG-DB-10: hash binding, risk class, failure state)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col
from app.db.models.enums import ACTION_STATUSES, RISK_CLASSES, check_in


class SimulatedAction(Base):
    __tablename__ = "simulated_actions"
    __table_args__ = (
        CheckConstraint(check_in("status", ACTION_STATUSES), name="ck_sim_status_enum"),
        CheckConstraint(check_in("risk_class", RISK_CLASSES), name="ck_sim_risk_enum"),
        UniqueConstraint("plan_id", "step_no", name="uq_sim_plan_step"),  # INV-009
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mitigation_plans.id"), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # INV-005
    approval_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("approval_requests.id")
    )
    step_no: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(json_col(), nullable=False, default=dict)
    risk_class: Mapped[str] = mapped_column(String(16), nullable=False)
    sim_config_hash: Mapped[str | None] = mapped_column(String(64))       # REPRO-001
    plant_model_version: Mapped[str | None] = mapped_column(String(32))   # REPRO-001
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    simulated_effect: Mapped[dict | None] = mapped_column(json_col())
    error_detail: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )
    executed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
