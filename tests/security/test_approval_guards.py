"""INV-007/008 + distinct-approver rule: expiry, replay, self-approval."""
from __future__ import annotations

import datetime as dt

import pytest

from app.core.exceptions import ConflictError, ForbiddenError
from app.services.approval_service import approve, deny


def test_approve_after_expiry_rejected(db, scenario):
    scenario["approval"].expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    db.flush()
    with pytest.raises(ConflictError, match="expired"):
        approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])


def test_double_approve_rejected(db, scenario):
    approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])
    with pytest.raises(ConflictError):
        approve(db, approval_id=scenario["approval"].id, approver=scenario["analyst2"])


def test_deny_after_approve_rejected(db, scenario):
    approve(db, approval_id=scenario["approval"].id, approver=scenario["admin"])
    with pytest.raises(ConflictError):
        deny(db, approval_id=scenario["approval"].id, approver=scenario["analyst2"],
             reason="late")


def test_self_approval_for_control_forbidden(db, users):
    """Control-class plan initiated by analyst X cannot be approved by X."""
    from app.core.canonical import steps_hash
    from app.db.models import AgentRun, Incident, MitigationPlan
    from app.services.validator_service import validate_plan_revision

    ds = db.query(Incident).first()  # any incident row works for wiring
    inc = ds if ds else None
    if inc is None:
        from tests.conftest import make_evidence_index  # noqa: F401

        pytest.skip("no incident seeded")
    run = AgentRun(config_hash="t", incident_id=inc.id, model_name="t", variant="grounded_validated",
                   status="running", created_by=users["analyst"].id)
    db.add(run)
    db.flush()
    steps = [{"step_no": 1, "action": "close_valve", "target": "MV-501",
              "params": {}, "citations": []}]
    plan = MitigationPlan(incident_id=inc.id, agent_run_id=run.id, revision_no=1,
                          steps=steps, steps_hash=steps_hash(steps),
                          status="draft_for_validation")
    db.add(plan)
    db.flush()
    validate_plan_revision(db, plan=plan)
    from sqlalchemy import select

    from app.db.models import ApprovalRequest

    approval = db.execute(select(ApprovalRequest).where(
        ApprovalRequest.plan_id == plan.id)).scalar_one()
    with pytest.raises(ForbiddenError, match="distinct_approver"):
        approve(db, approval_id=approval.id, approver=users["analyst"])
    # A different analyst CAN approve.
    res = approve(db, approval_id=approval.id, approver=users["analyst2"])
    assert res["status"] == "approved"
