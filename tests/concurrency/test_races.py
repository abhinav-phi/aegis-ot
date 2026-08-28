"""Concurrency: double execute, approve-execute race, duplicate agent run."""
from __future__ import annotations

import pytest

from app.core.exceptions import ConflictError
from app.services.approval_service import approve
from pipeline.sandbox.simulator import execute_plan


def test_double_execute_rejected(db, scenario):
    approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])
    execute_plan(db, plan_id=scenario["plan"].id, actor_id=scenario["analyst"].user_id)
    with pytest.raises(ConflictError):
        execute_plan(db, plan_id=scenario["plan"].id,
                     actor_id=scenario["analyst"].user_id)


def test_execute_without_approval_rejected(db, scenario):
    with pytest.raises(Exception) as e:
        execute_plan(db, plan_id=scenario["plan"].id,
                     actor_id=scenario["analyst"].user_id)
    assert "approval" in str(e.value) or "not_approved" in str(e.value) or \
        e.type.__name__ in ("ForbiddenError", "ConflictError")


def test_duplicate_active_agent_run_blocked(db, scenario, users):
    from sqlalchemy.exc import IntegrityError

    from app.db.models import AgentRun

    # INV-015 is enforced at the DB level by the partial unique index; assert
    # the specific integrity violation rather than a blind Exception.
    with pytest.raises(IntegrityError):
        AgentRun(config_hash="t", incident_id=scenario["incident"].id, model_name="x",
                 variant="grounded", status="running")
        db.add(AgentRun(config_hash="t", incident_id=scenario["incident"].id, model_name="x",
                        variant="grounded", status="running"))
        db.flush()


def test_execute_on_closed_incident_rejected(db, scenario):
    approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])
    inc = scenario["incident"]
    inc.status = "closed"
    inc.closed_reason = "no_action"
    db.flush()
    with pytest.raises(ConflictError):
        execute_plan(db, plan_id=scenario["plan"].id,
                     actor_id=scenario["analyst"].user_id)
