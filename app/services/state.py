"""Conditional state-transition helper (DEC-007, INV-007/008/009).

Every lifecycle change is a single conditional UPDATE filtered on the expected
source status; rowcount 0 ⇒ ConflictError. This makes races (double approve,
double execute, expiry races, duplicate schedulers) collapse into 409s.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.db.models import AgentRun, ApprovalRequest, Incident, MitigationPlan


def transition(
    db: Session,
    model: type,
    *,
    entity_id,
    from_status: str,
    to_status: str,
    extra_values: dict | None = None,
    status_column: str = "status",
    entity_name: str = "",
) -> int:
    table = model.__table__
    values = {status_column: to_status, **(extra_values or {})}
    rc = (
        db.query(model)
        .filter(
            getattr(model, "id") == entity_id,
            getattr(model, status_column) == from_status,
        )
        .update(values, synchronize_session=False)
    )
    if rc == 0:
        raise ConflictError(
            f"{entity_name or model.__name__}: expected status={from_status!r}, "
            f"transition to {to_status!r} refused"
        )
    return rc


# Convenience wrappers for the most safety-critical machines -----------------

def incident_transition(db: Session, incident_id, from_status: str, to_status: str,
                        extra: dict | None = None) -> int:
    return transition(db, Incident, entity_id=incident_id, from_status=from_status,
                      to_status=to_status, extra_values=extra, entity_name="incident")


def plan_transition(db: Session, plan_id, from_status: str, to_status: str,
                    extra: dict | None = None) -> int:
    return transition(db, MitigationPlan, entity_id=plan_id, from_status=from_status,
                      to_status=to_status, extra_values=extra, entity_name="plan")


def approval_transition(db: Session, approval_id, from_status: str, to_status: str,
                        extra: dict | None = None) -> int:
    return transition(db, ApprovalRequest, entity_id=approval_id, from_status=from_status,
                      to_status=to_status, extra_values=extra, entity_name="approval")


def agent_run_transition(db: Session, run_id, from_status: str, to_status: str,
                         extra: dict | None = None) -> int:
    return transition(db, AgentRun, entity_id=run_id, from_status=from_status,
                      to_status=to_status, extra_values=extra, entity_name="agent_run")
