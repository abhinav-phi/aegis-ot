"""The ONLY executor in the codebase (R4). Defense-in-depth execution gate.

Independently re-verifies (INV-003/005/010/017) before applying anything:
  1. plan exists, revision not superseded
  2. agent variant != naive
  3. incident state allows execution
  4. active validator result bound to plan hash
  5. approval (approved, unexpired, bound to plan hash) for write/control
  6. recomputed steps hash == stored/validator/approval hashes
Then applies steps idempotently (queued-only resume, UNIQUE(plan,step)).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical import steps_hash
from app.core.exceptions import ConflictError, ExecHashMismatch, ForbiddenError
from app.db.models import (
    AgentRun,
    ApprovalRequest,
    Incident,
    MitigationPlan,
    SimulatedAction,
    ValidatorResult,
)
from app.services import audit as audit_svc
from app.services.state import incident_transition, plan_transition
from pipeline.sandbox.plant_model import PlantModel


def _utcnow() -> dt.datetime:
    from app.core.timeutil import utcnow

    return utcnow()


def _aware(value):
    from app.core.timeutil import aware

    return aware(value)


def _verify_binding(db: Session, plan: MitigationPlan) -> tuple[str, ValidatorResult | None]:
    recomputed = steps_hash(plan.steps)
    if recomputed != plan.steps_hash:
        raise ExecHashMismatch("stored_steps_hash_mismatch")
    # HASH-002: when canonical bytes exist they are the authoritative source —
    # recompute from THEM and assert they decode back to the stored steps, so
    # mutation of either representation is detected.
    if plan.canonical_bytes is not None:
        import json as _json

        from app.core.canonical import content_hash, loads_strict

        decoded = loads_strict(plan.canonical_bytes.decode("utf-8"))
        if content_hash(decoded) != recomputed or decoded != plan.steps:
            raise ExecHashMismatch("canonical_bytes_binding_invalid")

    vr = db.get(ValidatorResult, plan.active_validator_result_id) \
        if plan.active_validator_result_id else None
    if vr is None or not vr.is_active or vr.plan_hash != recomputed or vr.plan_id != plan.id:
        raise ExecHashMismatch("validator_binding_missing_or_stale")
    return recomputed, vr


def _require_approval_if_gated(db: Session, plan: MitigationPlan, risk_classes: set[str],
                               now: dt.datetime) -> ApprovalRequest | None:
    gated = risk_classes & {"write", "control"}
    approval = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.plan_id == plan.id,
            ApprovalRequest.status.in_(["pending", "approved", "superseded"]),
        )
    ).scalars().first()
    if not gated:
        return None
    # INV-003: control/write requires an approved, unexpired, hash-bound row.
    if approval is None or approval.status != "approved":
        raise ForbiddenError("execution_requires_approved_approval_row")
    if approval.expires_at is None or \
            _aware(approval.expires_at) <= now:
        raise ConflictError("approval_expired")
    return approval


def execute_plan(db: Session, *, plan_id, actor_id, ip: str | None = None) -> dict:
    now = _utcnow()
    plan = db.get(MitigationPlan, plan_id)
    if plan is None:
        raise ConflictError("plan_not_found")
    if plan.status in ("superseded", "draft_only"):
        raise ForbiddenError(f"plan_status_{plan.status}_not_executable")

    run = db.get(AgentRun, plan.agent_run_id)
    # INV-010: naive variants can never execute.
    if run is None or run.variant == "naive":
        raise ForbiddenError("naive_variant_execution_forbidden")

    incident = db.get(Incident, plan.incident_id)
    # INV-017: stale/closed incidents never execute.
    if incident is None or incident.status != "awaiting_approval":
        raise ConflictError(f"incident_state_{incident.status if incident else 'missing'}_not_executable")

    recomputed, validator_result = _verify_binding(db, plan)

    risks = {rc["risk"] for rc in (validator_result.risk_classes or [])}
    approval = _require_approval_if_gated(db, plan, risks, now)
    if approval is not None and approval.plan_hash != recomputed:
        raise ExecHashMismatch("approval_hash_mismatch")
    if any(rc in ("write", "control") for rc in risks) and plan.status != "approved":
        raise ConflictError("plan_not_approved")

    # Claim execution atomically: approved -> executing, with a lease so the
    # worker reaper can recover a crashed executor (APP-002). Fail-closed:
    # stale leases escalate; they never auto-resume into a half-applied plan.
    lease_s = 600  # ≥ 2× worst-case per-step budget; reaped otherwise
    plan_transition(db, plan.id, "approved", "executing",
                    extra={"execution_lease_until":
                                  now + dt.timedelta(seconds=lease_s)})
    incident_transition(db, incident.id, "awaiting_approval", "simulating")
    audit_svc.audit(db, actor_id=actor_id, action="sandbox.execute_started",
                    entity_type="mitigation_plans", entity_id=plan.id,
                    after={"hash": recomputed}, ip_address=ip)

    # Idempotent step rows.
    existing = {
        sa.step_no: sa
        for sa in db.execute(select(SimulatedAction).where(SimulatedAction.plan_id == plan.id))
        .scalars()
    }
    rows: list[SimulatedAction] = []
    for step in sorted(plan.steps, key=lambda s: s.get("step_no", 0)):
        no = int(step.get("step_no", 0))
        if no in existing:
            rows.append(existing[no])
            continue
        row = SimulatedAction(
            plan_id=plan.id, plan_hash=recomputed,
            approval_request_id=approval.id if approval else None,
            step_no=no, action=step["action"], target=step["target"],
            params=step.get("params") or {},
            risk_class=next((r["risk"] for r in validator_result.risk_classes
                             if r["step_no"] == no), "read"),
            status="queued",
        )
        db.add(row)
        rows.append(row)
    db.flush()

    plant = PlantModel()
    failed: list[SimulatedAction] = []
    # APP-001 semantics: apply steps in order; on FIRST failure stop
    # immediately, mark all remaining queued steps `blocked`, keep
    # already-applied effects as recorded SIMULATED history, and escalate.
    for idx, row in enumerate(rows):
        if row.status != "queued":  # resume semantics: only queued work retried
            continue
        try:
            effect = plant.apply(row.action, row.target, dict(row.params or {}))
            row.status = "executed"
            row.simulated_effect = effect
            row.executed_at = now
            row.sim_config_hash = "plant-actions-v1"   # REPRO-001
            row.plant_model_version = "surrogate-1.0"  # REPRO-001
        except Exception as exc:  # sandbox error → fail-closed escalation
            row.status = "failed"
            row.error_detail = str(exc)[:500]
            row.sim_config_hash = "plant-actions-v1"
            row.plant_model_version = "surrogate-1.0"
            failed.append(row)
            for later in rows[idx + 1:]:
                if later.status == "queued":
                    later.status = "blocked"
                    later.error_detail = "not_executed_after_step_failure"
            break

    if failed:
        plan_transition(db, plan.id, "executing", "escalated")
        incident_transition(db, incident.id, "simulating", "escalated")
        audit_svc.audit(db, actor_id=actor_id, action="sandbox.failed",
                        entity_type="mitigation_plans", entity_id=plan.id,
                        after={"failed_steps": [f.step_no for f in failed]},
                        ip_address=ip)
        raise ConflictError("sandbox_step_failure_escalated")

    plan_transition(db, plan.id, "executing", "executed")
    incident_transition(db, incident.id, "simulating", "closed",
                        extra={"closed_reason": "resolved"})
    audit_svc.audit(db, actor_id=actor_id, action="sandbox.executed",
                    entity_type="mitigation_plans", entity_id=plan.id,
                    after={"steps": len(rows)}, ip_address=ip)
    return {"plan_id": str(plan.id), "executed_steps": len(rows),
            "label": "SIMULATED", "state_snapshot": plant.snapshot_plant_state("PLANT", {})}
