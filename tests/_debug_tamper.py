import os
os.environ.setdefault("AEGIS_OT_ENV", "dev")

from tests.conftest import *  # noqa
from tests.conftest import engine, TestingSession  # noqa
import pytest
from sqlalchemy import text

from app.services.approval_service import approve
from pipeline.sandbox.simulator import execute_plan, _verify_binding


def test_debug_tamper(db, users):
    from tests.conftest import make_evidence_index  # noqa: F401
    # build scenario manually via fixture logic
    from app.core.canonical import steps_hash
    from app.db.models import AgentRun, ApprovalRequest, Dataset, DatasetRun, Incident, MitigationPlan
    import datetime as dt
    from app.services.validator_service import validate_plan_revision

    ds = Dataset(key="synthetic", display_name="t", sha256="0" * 64,
                 sensor_columns=["FIT101", "LIT101"])
    db.add(ds); db.flush()
    drun = DatasetRun(dataset_id=ds.id, run_name="t-train", config_hash="t",
                      split_role="train", minio_root="x/", status="completed")
    db.add(drun); db.flush()
    inc = Incident(dataset_run_id=drun.id,
                   start_ts=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
                   end_ts=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
                   severity="high", status="open")
    db.add(inc); db.flush()
    run = AgentRun(config_hash="t", incident_id=inc.id, model_name="s",
                   variant="grounded_validated", status="running",
                   created_by=users["analyst"].id)
    db.add(run); db.flush()
    inc.status = "awaiting_approval"; db.flush()
    steps = [{"step_no": 1, "action": "set_tank_setpoint", "target": "T-101",
              "params": {"level_pct": 50.0}, "citations": ["ev-trusted"]}]
    plan = MitigationPlan(incident_id=inc.id, agent_run_id=run.id, revision_no=1,
                          steps=steps, steps_hash=steps_hash(steps),
                          status="draft_for_validation")
    db.add(plan); db.flush()
    validate_plan_revision(db, plan=plan)
    appr = db.execute(__import__("sqlalchemy").select(ApprovalRequest)
                      .where(ApprovalRequest.plan_id == plan.id)).scalar_one()
    from app.core.security import Principal

    admin = Principal(str(users["admin"].id), "admin")
    res = approve(db, approval_id=appr.id, approver=admin)
    print("APPROVE:", res)
    db.execute(text("UPDATE mitigation_plans SET steps = :s WHERE id = :i"),
               {"s": "[]", "i": str(plan.id)})
    db.flush()
    p2 = db.get(MitigationPlan, plan.id)
    print("steps now:", p2.steps, "hash:", p2.steps_hash[:8])
    try:
        execute_plan(db, plan_id=plan.id, actor_id=admin.user_id)
        print("EXECUTED?! BAD")
    except Exception as e:
        print("RAISED:", type(e).__name__, str(e)[:80])
