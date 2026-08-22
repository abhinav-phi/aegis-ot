"""INV-010: naive variant lockout across all paths."""
from __future__ import annotations

import pytest

from app.core.canonical import steps_hash
from app.core.exceptions import ForbiddenError
from app.db.models import AgentRun, MitigationPlan
from pipeline.sandbox.simulator import execute_plan


def _naive_plan(db, scenario, users) -> MitigationPlan:
    scenario["run"].status = "completed"  # free the single-active-run slot
    db.flush()
    run = AgentRun(config_hash="t", incident_id=scenario["incident"].id, model_name="t",
                   variant="naive", status="running",
                   created_by=users["analyst"].id)
    db.add(run)
    db.flush()
    steps = [{"step_no": 1, "action": "set_pump_speed", "target": "P-101",
              "params": {"speed_pct": 10.0}, "citations": []}]
    plan = MitigationPlan(incident_id=scenario["incident"].id, agent_run_id=run.id,
                          revision_no=1, steps=steps, steps_hash=steps_hash(steps),
                          status="draft_only")
    db.add(plan)
    db.flush()
    return plan


def test_naive_execution_forbidden_at_sandbox(db, scenario, users):
    plan = _naive_plan(db, scenario, users)
    with pytest.raises(ForbiddenError, match="naive"):
        execute_plan(db, plan_id=plan.id, actor_id=users["admin"].id)


def test_naive_plan_cannot_be_approved(db, scenario, users):
    from app.services.validator_service import validate_plan_revision

    plan = _naive_plan(db, scenario, users)
    validate_plan_revision(db, plan=plan)  # runs, but status stays draft_only
    assert plan.status == "draft_only"
    from app.db.models import ApprovalRequest
    from sqlalchemy import select

    rows = db.execute(select(ApprovalRequest).where(
        ApprovalRequest.plan_id == plan.id)).scalars().all()
    assert rows == [], "naive plans must never create approval requests"


def test_naive_service_gate(db, scenario, users):
    from app.services.agent_service import assert_not_naive_plan

    plan = _naive_plan(db, scenario, users)
    with pytest.raises(ForbiddenError):
        assert_not_naive_plan(db, plan)
