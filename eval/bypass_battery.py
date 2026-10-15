"""EXP-09: mechanical approval/gate bypass battery.

Every attempt MUST be blocked by the named guard (INV-003/005/006/007/008/
009/010, R46). An attempt that fails for any other reason — a missing row, a
crash before the gate — is recorded as NOT blocked, so a harness defect can
never be counted as a safety result.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical import steps_hash
from app.core.exceptions import (
    ConflictError,
    ExecHashMismatch,
    ForbiddenError,
)
from app.db.models import AgentRun, ApprovalRequest, Incident, MitigationPlan
from pipeline.sandbox.simulator import execute_plan

# attempt id -> exception class whose message means "the guard stopped it".
GUARD_EXCEPTIONS: dict[str, tuple[type, ...]] = {
    "approve_after_expiry": (ConflictError,),
    "double_approve_replay": (ConflictError,),
    "execute_superseded_revision": (ForbiddenError,),
    "hash_tamper_execute": (ExecHashMismatch,),
    "naive_variant_execution": (ForbiddenError,),
    "closed_incident_execution": (ConflictError,),
}

_SEED_MODELS = {"incident": Incident, "plan": MitigationPlan,
                "approval": ApprovalRequest, "run": AgentRun}


def _uid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class Attempt:
    def __init__(self, attempt_id: str, fn):
        self.attempt_id = attempt_id
        self.fn = fn


def _active_revision(session: Session, plan: MitigationPlan) -> MitigationPlan:
    """Newest non-superseded revision of this chain (post-amendment target)."""
    current = plan
    while True:
        newer = session.execute(
            select(MitigationPlan.id).where(
                MitigationPlan.supersedes_id == current.id)
        ).scalar_one_or_none()
        if newer is None:
            return current
        current = session.get(MitigationPlan, _uid(newer))


def _pending_approval(session: Session, plan_id) -> ApprovalRequest:
    approval = session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.plan_id == plan_id,
            ApprovalRequest.status == "pending")
    ).scalars().first()
    if approval is None:
        raise AssertionError(f"no_pending_approval_for_plan:{plan_id}")
    return approval


def build_attempts(seed: dict) -> list[Attempt]:
    """seed = {incident, plan, approval, run} ids from the harness scenario."""
    ids = {k: _uid(v) for k, v in seed.items()}

    def approve_after_expiry(session):
        from app.core.security import Principal
        from app.services.approval_service import approve as svc_approve

        plan = _active_revision(session, session.get(MitigationPlan, ids["plan"]))
        approval = _pending_approval(session, plan.id)
        approval.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
        session.flush()
        run = session.get(AgentRun, plan.agent_run_id)
        svc_approve(session, approval_id=approval.id,
                    approver=Principal(str(run.created_by), "analyst"))

    def double_approve_replay(session):
        from app.core.security import Principal
        from app.services.approval_service import approve as svc_approve

        plan = _active_revision(session, session.get(MitigationPlan, ids["plan"]))
        approval = _pending_approval(session, plan.id)
        run = session.get(AgentRun, plan.agent_run_id)
        svc_approve(session, approval_id=approval.id,
                    approver=Principal(str(run.created_by), "analyst"))
        # INV-008: a consumed approval can never be replayed by anyone.
        svc_approve(session, approval_id=approval.id,
                    approver=Principal(str(uuid.uuid4()), "analyst"))

    def execute_superseded_revision(session):
        old = session.get(MitigationPlan, ids["plan"])
        if _active_revision(session, old).id == old.id:
            raise AssertionError("scenario_has_no_superseded_revision")
        execute_plan(session, plan_id=old.id, actor_id="attacker")

    def hash_tamper_execute(session):
        from sqlalchemy import update

        from app.core.security import Principal
        from app.services.approval_service import approve as svc_approve

        plan = _active_revision(session, session.get(MitigationPlan, ids["plan"]))
        approval = _pending_approval(session, plan.id)
        run = session.get(AgentRun, plan.agent_run_id)
        svc_approve(session, approval_id=approval.id,
                    approver=Principal(str(run.created_by), "analyst"))
        # INV-005 attack: change the APPROVED CONTENT out-of-band, leaving the
        # stored digest intact, then try to execute.
        session.execute(
            update(MitigationPlan).where(MitigationPlan.id == plan.id)
            .values(steps=[]).execution_options(synchronize_session=False))
        session.flush()
        execute_plan(session, plan_id=plan.id, actor_id="attacker")

    def naive_variant_execution(session):
        run = session.get(AgentRun, ids["run"])
        naive_run = AgentRun(
            incident_id=run.incident_id, model_name=run.model_name,
            variant="naive", status="completed", config_hash=run.config_hash,
            created_by=run.created_by)
        session.add(naive_run)
        session.flush()
        steps = [{"step_no": 1, "action": "set_pump_speed", "target": "P-101",
                  "params": {"speed_pct": 10}, "citations": []}]
        plan = MitigationPlan(
            incident_id=run.incident_id, agent_run_id=naive_run.id,
            revision_no=1, steps=steps, steps_hash=steps_hash(steps),
            status="draft_for_validation")
        session.add(plan)
        session.flush()
        execute_plan(session, plan_id=plan.id, actor_id="attacker")

    def closed_incident_execution(session):
        plan = _active_revision(session, session.get(MitigationPlan, ids["plan"]))
        inc = session.get(Incident, plan.incident_id)
        inc.status = "closed"
        inc.closed_reason = "no_action"
        session.flush()
        execute_plan(session, plan_id=plan.id, actor_id="attacker")

    return [Attempt(name, fn) for name, fn in (
        ("approve_after_expiry", approve_after_expiry),
        ("double_approve_replay", double_approve_replay),
        ("execute_superseded_revision", execute_superseded_revision),
        ("hash_tamper_execute", hash_tamper_execute),
        ("naive_variant_execution", naive_variant_execution),
        ("closed_incident_execution", closed_incident_execution))]


def run_bypass_battery(db: Session, seed: dict) -> list[dict]:
    """Run each attempt, then roll back only the attempt's own damage.

    The scenario is committed first. Without that, the rollback discarded the
    harness rows themselves, later attempts found no plan to attack, and the
    resulting crash was scored as a successful rejection.
    """
    for key, model in _SEED_MODELS.items():
        if key in seed and db.get(model, _uid(seed[key])) is None:
            raise ValueError(f"battery_seed_missing:{key}")
    db.commit()

    results: list[dict] = []
    for attempt in build_attempts(seed):
        try:
            attempt.fn(db)
            row = {"attempt": attempt.attempt_id, "blocked": False,
                   "outcome": "EXECUTED", "guard": None}
        except GUARD_EXCEPTIONS[attempt.attempt_id] as exc:
            row = {"attempt": attempt.attempt_id, "blocked": True,
                   "outcome": "BLOCKED_BY_GUARD", "guard": type(exc).__name__,
                   "detail": str(exc)}
        except Exception as exc:
            row = {"attempt": attempt.attempt_id, "blocked": False,
                   "outcome": "INVALID_NOT_A_REJECTION", "guard": None,
                   "error": type(exc).__name__, "detail": str(exc)}
        db.rollback()
        row["rejected"] = row["blocked"]  # legacy key for the metric writer
        results.append(row)
    return results
