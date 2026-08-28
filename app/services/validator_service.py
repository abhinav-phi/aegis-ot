"""Validation service: binds C1–C5 outcome to the plan revision hash (INV-005).

Creates a ValidatorResult, supersedes prior results, advances plan status:
  allow            → validated (read-only auto-sim path may follow)
  require_approval → validated + approval request created
  block            → rejected
  escalate         → escalated
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical import steps_hash
from app.core.config import get_settings
from app.db.models import (
    AgentRun,
    ApprovalRequest,
    Incident,
    MitigationPlan,
    ValidatorResult,
)
from app.services import audit as audit_svc
from app.services.state import plan_transition
from pipeline.detect.invariances import failed_rules_for_incident
from pipeline.validator.engine import EvidenceIndex, validate_plan
from pipeline.validator.policy import load_default_registry


def build_evidence_index(db: Session, run_id) -> EvidenceIndex:
    from app.db.models import AgentMessage

    idx = EvidenceIndex()
    msgs = db.execute(select(AgentMessage).where(AgentMessage.agent_run_id == run_id)).scalars()
    for m in msgs:
        payload = m.payload or {}
        result = payload.get("result") if isinstance(payload.get("result"), dict) else None
        candidates: list[dict] = []
        if isinstance(payload.get("evidence"), dict):
            candidates.append(payload["evidence"])
        if result:
            candidates.append(result)
        candidates.extend(
            result.get("evidence", []) if isinstance(result, dict) else [])
        for c in candidates:
            eid = c.get("validator_evidence_id") or c.get("evidence_id")
            if not eid:
                continue
            fields = dict(c.get("fields") or {})
            result = payload.get("result") if isinstance(payload.get("result"), dict) else None
            if m.tool_name in ("query_latest", "query_history") and \
                    isinstance(result, dict) and "score" in result:
                fields.setdefault("score", result["score"])
            idx[str(eid)] = {
                "tier": c.get("tier", "public"),
                "source": c.get("source") or f"tool:{m.tool_name}",
                "fields": fields,
                "text": str(c.get("text") or ""),
            }
    return idx


def prior_c5_categories(db: Session, incident_id, exclude_plan_id) -> list[str | None]:
    rows = db.execute(
        select(ValidatorResult)
        .join(MitigationPlan, ValidatorResult.plan_id == MitigationPlan.id)
        .where(MitigationPlan.incident_id == incident_id,
               MitigationPlan.id != exclude_plan_id)
        .order_by(ValidatorResult.created_at.desc())
        .limit(2)
    ).scalars().all()
    return [r.c5_category for r in rows]


def validate_plan_revision(db: Session, *, plan: MitigationPlan,
                           actor_id=None, ip: str | None = None) -> ValidatorResult:
    """Full re-validation entry point (used on creation AND after amendment)."""
    h = steps_hash(plan.steps)
    if h != plan.steps_hash:
        from app.core.exceptions import ExecHashMismatch

        raise ExecHashMismatch("plan_hash_mismatch_at_validation")
    # HASH-002: canonical-bytes binding — recompute digest ONLY from the
    # stored canonical form and assert it decodes back to the stored steps.
    if plan.canonical_bytes is not None:
        from app.core.canonical import content_hash, loads_strict

        stored = plan.canonical_bytes
        if content_hash(loads_strict(stored.decode("utf-8"))) != h or \
                __import__("json").loads(stored) != plan.steps:
            from app.core.exceptions import ExecHashMismatch

            raise ExecHashMismatch("canonical_bytes_binding_invalid")

    run = db.get(AgentRun, plan.agent_run_id)
    incident = db.get(Incident, plan.incident_id)

    # Supersede previous active results across this revision chain.
    _deactivate_results(db, plan)

    index = build_evidence_index(db, plan.agent_run_id)
    failed_invariants = failed_rules_for_incident(db, incident)
    outcome = validate_plan(
        plan.steps, index,
        registry=load_default_registry(),
        failed_invariants=failed_invariants,
        prior_c5_categories=prior_c5_categories(db, plan.incident_id, plan.id),
    )

    vr = ValidatorResult(
        plan_id=plan.id, plan_hash=h, verdict=outcome.verdict,
        checks=outcome.checks, risk_classes=outcome.risk_classes,
        c5_category=outcome.c5_category, is_active=True,
    )
    db.add(vr)
    db.flush()
    plan.active_validator_result_id = vr.id

    # INV-010 / R44: naive variants are recorded but stay locked to draft_only;
    # no status advance and no approval request may ever be created.
    naive_locked = run is not None and run.variant == "naive"

    if plan.status == "draft_for_validation" and not naive_locked:
        new_status = {
            "allow": "validated",
            "require_approval": "validated",
            "block": "rejected",
            "escalate": "escalated",
        }[outcome.verdict]
        extra = {"active_validator_result_id": vr.id}
        if new_status == "validated":
            plan_transition(db, plan.id, "draft_for_validation", "validated",
                            extra=extra)
        elif new_status == "rejected":
            plan_transition(db, plan.id, "draft_for_validation", "rejected",
                            extra=extra)
        else:
            plan_transition(db, plan.id, "draft_for_validation", "escalated",
                            extra=extra)
        if new_status == "escalated":
            from app.services.state import incident_transition

            incident_transition(db, incident.id, "analyzing", "escalated")

    if outcome.verdict == "require_approval" and not naive_locked:
        _create_approval(db, plan=plan, plan_hash=h, requested_by=run.created_by
                         if run else None)

    audit_svc.audit(db, actor_id=actor_id, action="validator.validated",
                    entity_type="mitigation_plans", entity_id=plan.id,
                    after={"verdict": outcome.verdict, "hash": h}, ip_address=ip)
    db.refresh(plan)
    return vr


def _create_approval(db: Session, *, plan: MitigationPlan, plan_hash: str,
                     requested_by) -> ApprovalRequest | None:
    existing = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.plan_id == plan.id,
                                      ApprovalRequest.status == "pending")
    ).scalar_one_or_none()
    if existing:
        return existing
    approval = ApprovalRequest(
        plan_id=plan.id, plan_hash=plan_hash, status="pending",
        requested_by=requested_by,
        expires_at=dt.datetime.now(dt.UTC)
        + dt.timedelta(hours=get_settings().approval_expiry_hours),
    )
    db.add(approval)
    db.flush()

    # Incident follows into awaiting_approval when a gate is actually required.
    incident = db.get(Incident, plan.incident_id)
    if incident is not None and incident.status == "analyzing":
        from app.services.state import incident_transition

        incident_transition(db, incident.id, "analyzing", "awaiting_approval")
    return approval


def _chain_ids(db: Session, plan: MitigationPlan) -> list:
    ids = [plan.id]
    cur = plan
    while cur.supersedes_id:
        cur = db.get(MitigationPlan, cur.supersedes_id)
        if cur is None:
            break
        ids.append(cur.id)
    return ids


def _deactivate_results(db: Session, plan: MitigationPlan) -> None:
    from sqlalchemy import update

    db.execute(
        update(ValidatorResult)
        .where(ValidatorResult.plan_id.in_(_chain_ids(db, plan)),
               ValidatorResult.is_active.is_(True))
        .values(is_active=False)
    )
