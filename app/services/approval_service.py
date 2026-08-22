"""Approval service (§17/§25 contract): approve / deny / amend with full
hash binding, expiry guards, distinct-approver rule, Option A semantics."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical import canonical_bytes, steps_hash, short_hash
from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db.models import (
    AgentRun,
    ApprovalRequest,
    Incident,
    MitigationPlan,
    ValidatorResult,
)
from app.services import audit as audit_svc
from app.services.state import approval_transition, incident_transition
from pipeline.validator.policy import load_default_registry


def _utcnow() -> dt.datetime:
    from app.core.timeutil import utcnow

    return utcnow()


def _aware(value):
    from app.core.timeutil import aware

    return aware(value)


def get_approval_or_404(db: Session, approval_id) -> ApprovalRequest:
    a = db.get(ApprovalRequest, approval_id)
    if a is None:
        raise NotFoundError("approval_not_found")
    return a


def list_pending(db: Session) -> list[ApprovalRequest]:
    return list(db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.status == "pending")
        .order_by(ApprovalRequest.created_at)
    ).scalars())


def _guards(db: Session, approval: ApprovalRequest,
            plan_statuses: tuple[str, ...] = ("validated",)) -> tuple[MitigationPlan, ValidatorResult]:
    # INV-007: pending + unexpired.
    if approval.status != "pending":
        raise ConflictError(f"approval_status_{approval.status}_not_actionable")
    if approval.expires_at is None or \
            _aware(approval.expires_at) <= _utcnow():
        approval_transition(db, approval.id, "pending", "expired")
        audit_svc.audit(db, actor_id=None, action="approval.expired_lazy",
                        entity_type="approval_requests", entity_id=approval.id)
        raise ConflictError("approval_expired")

    plan = db.get(MitigationPlan, approval.plan_id)
    if plan is None or plan.status == "superseded":
        raise ConflictError("plan_superseded_or_missing")
    # Revision currency: reject if a newer revision exists in the chain.
    newer = db.execute(
        select(MitigationPlan).where(MitigationPlan.supersedes_id == plan.id)
    ).scalar_one_or_none()
    if newer is not None:
        raise ConflictError("superseded_by_newer_revision")

    vr = db.get(ValidatorResult, plan.active_validator_result_id) \
        if plan.active_validator_result_id else None
    # INV-005 preconditions: active validator bound to this exact hash.
    if vr is None or not vr.is_active or vr.plan_hash != plan.steps_hash:
        raise ConflictError("validator_binding_invalid")
    if approval.plan_hash != plan.steps_hash:
        from app.core.exceptions import ExecHashMismatch

        raise ExecHashMismatch("approval_plan_hash_mismatch")
    if plan.status not in plan_statuses:
        raise ConflictError(f"plan_status_{plan.status}")
    return plan, vr


def approve(db: Session, *, approval_id, approver, ip: str | None = None) -> dict:
    approval = get_approval_or_404(db, approval_id)
    plan, vr = _guards(db, approval)

    run = db.get(AgentRun, plan.agent_run_id)
    risks = {r["risk"] for r in (vr.risk_classes or [])}
    if "control" in risks and get_settings().require_distinct_approver:
        # SEC-002: distinct approver binds BOTH the original run initiator AND
        # the author of the current revision (amenders cannot self-approve).
        forbidden_authors = {
            str(x) for x in (run.created_by if run else None,
                             plan.revision_created_by) if x
        }
        if str(approver.user_id) in forbidden_authors:
            raise ForbiddenError("distinct_approver_required_for_control")

    # INV-008 replay guard: consume pending atomically.
    approval_transition(db, approval.id, "pending", "approved",
                        extra={"decided_by": approver.user_id,
                               "decided_at": _utcnow()})
    from app.services.state import plan_transition

    plan_transition(db, plan.id, "validated", "approved")
    audit_svc.audit(db, actor_id=approver.user_id, action="approval.approved",
                    entity_type="approval_requests", entity_id=approval.id,
                    before={"status": "pending"},
                    after={"plan": str(plan.id), "hash": short_hash(plan.steps_hash)},
                    ip_address=ip)
    return {"approval_id": str(approval.id), "status": "approved",
            "plan_id": str(plan.id), "plan_hash_suffix": short_hash(plan.steps_hash)}


def deny(db: Session, *, approval_id, approver, reason: str,
         ip: str | None = None) -> dict:
    if not reason or not reason.strip():
        raise ConflictError("deny_reason_required")
    approval = get_approval_or_404(db, approval_id)
    plan, _vr = _guards(db, approval)
    approval_transition(db, approval.id, "pending", "denied",
                        extra={"decided_by": approver.user_id,
                               "decision_reason": reason.strip(),
                               "decided_at": _utcnow()})
    from app.services.state import plan_transition

    plan_transition(db, plan.id, "validated", "rejected")
    incident = db.get(Incident, plan.incident_id)
    if incident is not None and incident.status == "awaiting_approval":
        incident_transition(db, incident.id, "awaiting_approval", "rejected")
    audit_svc.audit(db, actor_id=approver.user_id, action="approval.denied",
                    entity_type="approval_requests", entity_id=approval.id,
                    after={"reason": reason.strip()[:500]}, ip_address=ip)
    return {"approval_id": str(approval.id), "status": "denied"}


def amend(db: Session, *, approval_id, actor, steps_patch: list[dict],
          ip: str | None = None) -> dict:
    """DEC-002/§9: new immutable revision; old approval+validation voided;
    fresh C1–C5 runs synchronously before any execution can occur."""
    approval = get_approval_or_404(db, approval_id)
    # Amendment permitted only from validated/approved revisions (audit §10).
    plan, _vr = _guards(db, approval, plan_statuses=("validated", "approved"))

    by_no = {int(p.get("step_no", 0)): p for p in steps_patch}
    new_steps = []
    changed = False
    for step in sorted(plan.steps, key=lambda s: s.get("step_no", 0)):
        no = int(step.get("step_no", 0))
        patch = by_no.get(no)
        merged = dict(step)
        if patch:
            changed = True
            allowed = {"action", "target", "params", "citations"}
            for k in allowed & set(patch.keys()):
                merged[k] = patch[k]
        new_steps.append(merged)
    if not changed:
        raise ConflictError("NO_OP_AMEND")

    new_hash = steps_hash(new_steps)
    if new_hash == plan.steps_hash:
        raise ConflictError("NO_OP_AMEND")

    latest = db.execute(
        select(MitigationPlan.revision_no).where(MitigationPlan.agent_run_id == plan.agent_run_id)
        .order_by(MitigationPlan.revision_no.desc()).limit(1)
    ).scalar_one()

    revision = MitigationPlan(
        incident_id=plan.incident_id, agent_run_id=plan.agent_run_id,
        revision_no=latest + 1, supersedes_id=plan.id,
        steps=new_steps, steps_hash=new_hash,
        canonical_bytes=canonical_bytes(new_steps),   # HASH-001
        revision_created_by=actor.user_id,            # SEC-002 author binding
        status="draft_for_validation",
    )
    db.add(revision)
    db.flush()

    # Invalidate everything derived from the old revision (same tx).
    approval_transition(db, approval.id, "pending", "superseded")
    from app.services.state import plan_transition

    plan_transition(db, plan.id, "validated", "superseded")

    from app.services.validator_service import validate_plan_revision

    validate_plan_revision(db, plan=revision, actor_id=actor.user_id, ip=ip)
    db.refresh(revision)
    audit_svc.audit(db, actor_id=actor.user_id, action="approval.amended",
                    entity_type="mitigation_plans", entity_id=revision.id,
                    before={"revision": plan.revision_no},
                    after={"revision": revision.revision_no}, ip_address=ip)

    new_approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.plan_id == revision.id,
                                      ApprovalRequest.status == "pending")
    ).scalar_one_or_none()
    return {"new_plan_id": str(revision.id), "new_revision": revision.revision_no,
            "verdict": revision.active_validator_result_id and
            db.get(ValidatorResult, revision.active_validator_result_id).verdict,
            "new_approval_id": str(new_approval.id) if new_approval else None}
