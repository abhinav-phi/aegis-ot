"""Plan revision immutability enforcement (DEC-001, INV-005).

Layer 1 (portable): SQLAlchemy before_update listener rejects changes to
protected columns. Layer 2 (PostgreSQL): BEFORE UPDATE trigger in migration
0002 raises even if the ORM is bypassed with raw SQL.
"""
from __future__ import annotations

from sqlalchemy import event

from app.core.exceptions import ConflictError

PROTECTED_PLAN_COLUMNS = (
    "steps", "steps_hash", "incident_id", "agent_run_id", "revision_no", "supersedes_id",
)


def register_immutability_listeners() -> None:
    from app.db.models.validator import MitigationPlan

    @event.listens_for(MitigationPlan, "before_update")
    def _protect_plan(mapper, connection, target):  # noqa: ANN001
        state = target._sa_instance_state
        for attr in PROTECTED_PLAN_COLUMNS:
            hist = state.attrs[attr].history
            if hist.has_changes():
                raise ConflictError("plan_revision_immutable")
