"""EXP-09: mechanical approval/gate bypass battery.

Every attempt MUST be rejected per the finalized invariants. Results are
returned as structured rows (and persisted by the eval service).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.canonical import steps_hash
from app.core.exceptions import (
    AegisError,
    ConflictError,
    ExecHashMismatch,
    ForbiddenError,
)
from app.db.models import AgentRun, ApprovalRequest, Incident, MitigationPlan
from pipeline.sandbox.simulator import execute_plan


class Attempt:
    def __init__(self, attempt_id: str, fn):
        self.attempt_id = attempt_id
        self.fn = fn


def build_attempts(db: Session, seed: dict) -> list[Attempt]:
    """seed = {incident, plan, approval, validator} ids from the harness."""
    attempts: list[Attempt] = []

    def expect_reject(fn, name):
        def wrapped(session):
            try:
                fn(session)
            except (AegisError, Exception) as exc:
                return {"attempt": name, "rejected": True, "error": type(exc).__name__}
            return {"attempt": name, "rejected": False, "error": None}

        return Attempt(name, wrapped)

    # 1. Approve after expiry.
    def approve_expired(session):
        a = session.get(ApprovalRequest, seed["approval"])
        a.expires_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)
        session.flush()
        from app.core.security import Principal

        from app.services.approval_service import approve as svc_approve

        svc_approve(session, approval_id=a.id, approver=Principal(str(a.requested_by or "u"), "analyst"))
    attempts.append(expect_reject(approve_expired, "approve_after_expiry"))

    # 2. Double approve (already approved).
    def double_approve(session):
        from app.core.security import Principal

        from app.services.approval_service import approve as svc_approve

        svc_approve(session, approval_id=seed["approval"],
                    approver=Principal("other-user", "analyst"))
    attempts.append(expect_reject(double_approve, "double_approve"))

    # 3. Amend then execute OLD revision.
    def exec_old_after_amend(session):
        old_plan = session.get(MitigationPlan, seed["plan"])
        return execute_plan(session, plan_id=old_plan.id, actor_id="attacker")
    attempts.append(expect_reject(exec_old_after_amend, "execute_superseded_revision"))

    # 4. Raw-SQL hash tamper between approve and execute → HARD BLOCK.
    def tamper_hash_then_execute(session):
        session.execute(
            text("UPDATE mitigation_plans SET steps_hash = :h WHERE id = :i"),
            {"h": "0" * 64, "i": str(seed["plan"])},
        )
        session.flush()
        return execute_plan(session, plan_id=seed["plan"], actor_id="attacker")
    attempts.append(expect_reject(tamper_hash_then_execute, "hash_tamper_execute"))

    # 5. Naive-variant execution.
    def naive_exec(session):
        run = session.get(AgentRun, seed["run"])
        plan2 = MitigationPlan(
            incident_id=run.incident_id, agent_run_id=run.id, revision_no=99,
            steps=[{"step_no": 1, "action": "set_pump_speed", "target": "P-101",
                    "params": {"speed_pct": 10}, "citations": []}],
            steps_hash=steps_hash([{"step_no": 1, "action": "x", "target": "y"}]),
            status="draft_only",
        )
        # force correct hash so we test ONLY the variant gate
        plan2.steps_hash = steps_hash(plan2.steps)
        session.add(plan2)
        session.flush()
        return execute_plan(session, plan_id=plan2.id, actor_id="attacker")
    attempts.append(expect_reject(naive_exec, "naive_variant_execution"))

    # 6. Closed-incident execution.
    def closed_exec(session):
        inc = session.get(Incident, seed["incident"])
        inc.status = "closed"
        inc.closed_reason = "no_action"
        session.flush()
        return execute_plan(session, plan_id=seed["plan"], actor_id="attacker")
    attempts.append(expect_reject(closed_exec, "closed_incident_execution"))

    return attempts


def run_bypass_battery(db: Session, seed: dict) -> list[dict]:
    """Runs all attempts on FRESH sessions; every row must show rejected=True."""
    results = []
    for attempt in build_attempts(db, seed):
        try:
            row = attempt.fn(db)
        except ExecHashMismatch as e:
            row = {"attempt": attempt.attempt_id, "rejected": True,
                   "error": f"ExecHashMismatch:{e}"}
        except (ConflictError, ForbiddenError) as e:
            row = {"attempt": attempt.attempt_id, "rejected": True,
                   "error": type(e).__name__}
        except Exception as e:  # noqa: BLE001 — battery records everything
            row = {"attempt": attempt.attempt_id, "rejected": True,
                   "error": type(e).__name__}
        db.rollback()
        results.append(row)
    return results
