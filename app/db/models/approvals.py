"""Approval requests (Option A: ONE per plan revision; CHG-DB-09/-18)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.db.models.enums import APPROVAL_STATUSES, check_in


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(check_in("status", APPROVAL_STATUSES), name="ck_appr_status_enum"),
        # Option A / INV-008: at most one live approval per plan revision.
        Index("uq_appr_live_per_plan", "plan_id", unique=True,
              postgresql_where=text("status IN ('pending','approved')"),
              sqlite_where=text("status IN ('pending','approved')")),
        # CHG-DB-18: expiry scheduler scan.
        Index("ix_appr_expiry_pending", "expires_at",
              postgresql_where=text("status = 'pending'"),
              sqlite_where=text("status = 'pending'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mitigation_plans.id"), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # INV-005
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
