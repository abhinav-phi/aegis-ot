"""State-machine conformance: every valid edge + forbidden edges."""
from __future__ import annotations

import pytest

from app.core.exceptions import ConflictError
from app.services.approval_service import approve, deny
from app.services.state import incident_transition, plan_transition


def test_valid_edges_open_to_analyzing(db, scenario):
    inc = scenario["incident"]
    incident_transition(db, inc.id, "awaiting_approval", "analyzing")  # back-edge allowed
    incident_transition(db, inc.id, "analyzing", "awaiting_approval")


def test_forbidden_edge_closed_to_anything(db, scenario):
    inc = scenario["incident"]
    inc.status = "closed"
    inc.closed_reason = "no_action"
    db.flush()
    with pytest.raises(ConflictError):
        incident_transition(db, inc.id, "open", "analyzing")


def test_plan_validated_to_approved_via_approval(db, scenario):
    approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])
    assert scenario["plan"].status == "approved"


def test_plan_deny_rejected(db, scenario):
    deny(db, approval_id=scenario["approval"].id, approver=scenario["analyst2"],
         reason="not safe")
    assert scenario["plan"].status == "rejected"
    assert scenario["incident"].status == "rejected"


def test_rejected_incident_can_retry(db, scenario):
    deny(db, approval_id=scenario["approval"].id, approver=scenario["analyst2"],
         reason="not safe")
    from app.services.agent_service import create_and_start_run

    run = create_and_start_run(db, incident=scenario["incident"],
                               variant="grounded_validated",
                               actor_id=scenario["analyst"].user_id)
    assert run.status == "running"
    assert scenario["incident"].status == "analyzing"


def test_escalation_resolution(db, scenario):
    inc = scenario["incident"]
    incident_transition(db, inc.id, "awaiting_approval", "escalated")
    from app.services.incident_service import resolve_escalation

    resolved = resolve_escalation(db, incident_id=inc.id,
                                  actor_id=scenario["admin"].user_id)
    assert resolved.status == "closed" and resolved.closed_reason == "escalated"


def test_simulating_failure_escalates(db, scenario):
    """Sandbox step failure ⇒ plan+incident escalate (§11)."""
    from app.core.canonical import steps_hash
    from app.db.models import MitigationPlan

    approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])
    plan = scenario["plan"]
    # Force a step the plant model cannot apply (unknown tank) while keeping
    # the validator/approval chain intact via a fresh validated revision.
    steps = [{"step_no": 1, "action": "set_tank_setpoint", "target": "T-999",
              "params": {"level_pct": 10.0}, "citations": ["ev-trusted"]}]
    from app.services.approval_service import amend

    res = amend(db, approval_id=None if False else _pending_amend_id(db, scenario),
                approver=scenario["analyst"],
                steps_patch=steps)
    new_plan = db.get(MitigationPlan, res["new_plan_id"])
    from app.db.models import ApprovalRequest
    from sqlalchemy import select

    appr = db.execute(select(ApprovalRequest).where(
        ApprovalRequest.plan_id == new_plan.id)).scalar_one()
    approve(db, approval_id=appr.id, approver=scenario["admin"])
    with pytest.raises(ConflictError):
        from pipeline.sandbox.simulator import execute_plan

        execute_plan(db, plan_id=new_plan.id, actor_id=scenario["analyst"].user_id)
    assert new_plan.status == "escalated"


def _pending_amend_id(db, scenario):
    return scenario["approval"].id
