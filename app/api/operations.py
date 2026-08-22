"""Incidents, agent, validator, approvals, sandbox routers (§12 contract)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import audit_context, ok
from app.core.exceptions import ConflictError
from app.core.security import Principal, current_principal, require_analyst
from app.db.models import (
    AgentMessage,
    AgentRun,
    Anomaly,
    AnomalyExplanation,
    Detection,
    Incident,
    ThreatMapping,
)
from app.db.session import get_db
from app.services import agent_service, approval_service, incident_service
from app.services.audit import audit
from pipeline.sandbox.simulator import execute_plan

router = APIRouter(tags=["operations"])


class CloseIn(BaseModel):
    reason: str


class AgentRunIn(BaseModel):
    variant: str = "grounded_validated"


class DenyIn(BaseModel):
    reason: str = Field(min_length=1)


class AmendIn(BaseModel):
    steps_patch: list[dict]


# ---------------------------------------------------------------- incidents
@router.get("/incidents")
def list_incidents(status: str | None = None,
                   db: Session = Depends(get_db),
                   _p: Principal = Depends(current_principal)):
    q = select(Incident).order_by(Incident.start_ts.desc()).limit(200)
    if status:
        q = q.where(Incident.status == status)
    rows = db.execute(q).scalars().all()
    return ok([{"id": str(i.id), "severity": i.severity, "status": i.status,
                "start_ts": str(i.start_ts), "end_ts": str(i.end_ts),
                "title": i.title} for i in rows])


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db),
                 _p: Principal = Depends(current_principal)):
    inc = incident_service.get_incident_or_404(db, incident_id)
    anomalies = db.execute(select(Anomaly).where(Anomaly.incident_id == inc.id)).scalars().all()
    explanations = []
    for a in anomalies:
        exp = db.execute(select(AnomalyExplanation)
                         .where(AnomalyExplanation.anomaly_id == a.id)).scalar_one_or_none()
        det = db.get(Detection, a.detection_id)
        explanations.append({
            "anomaly_id": str(a.id), "score": det.score if det else None,
            "severity": a.severity, "top_sensors": a.top_sensors,
            "low_confidence": a.low_confidence,
            "hypothesis": exp.hypothesis if exp else None,
            "invariant_checks": exp.invariant_checks if exp else [],
        })
    mappings = db.execute(select(ThreatMapping)
                          .where(ThreatMapping.incident_id == inc.id)).scalars().all()
    return ok({
        "id": str(inc.id), "status": inc.status, "severity": inc.severity,
        "start_ts": str(inc.start_ts), "end_ts": str(inc.end_ts),
        "title": inc.title,
        "note": "diagnosis is hypothesis (R19)",
        "anomalies": explanations,
        "threat_mappings": [{"technique_id": t.technique_id,
                             "confidence": t.confidence, "basis": t.basis}
                            for t in mappings],
    })


@router.post("/incidents/{incident_id}/close")
def close_incident(incident_id: str, payload: CloseIn,
                   db: Session = Depends(get_db), request: Request = None,  # type: ignore[assignment]
                   p: Principal = Depends(require_analyst)):
    ctx = audit_context(request) if request else {"ip": None}
    if payload.reason == "no_action":
        inc = incident_service.close_no_action(db, incident_id=incident_id,
                                               actor_id=p.user_id, ip=ctx["ip"])
    elif payload.reason == "escalated":
        if not p.is_admin:
            raise ConflictError("admin_required_for_escalation_resolution")
        inc = incident_service.resolve_escalation(db, incident_id=incident_id,
                                                  actor_id=p.user_id, ip=ctx["ip"])
    elif payload.reason == "resolved":
        raise ConflictError("resolved_close_is_automatic_post_simulation")
    else:
        raise ConflictError("invalid_close_reason")
    return ok({"id": str(inc.id), "status": inc.status,
               "closed_reason": inc.closed_reason})


# ---------------------------------------------------------------- agent
@router.post("/incidents/{incident_id}/agent_runs", status_code=202)
def create_agent_run(incident_id: str, payload: AgentRunIn,
                     request: Request,
                     db: Session = Depends(get_db),
                     p: Principal = Depends(require_analyst)):
    from app.core.exceptions import ValidationFailed

    if payload.variant not in ("naive", "grounded", "grounded_validated"):
        raise ValidationFailed("invalid_variant")
    inc = incident_service.get_incident_or_404(db, incident_id)
    run = agent_service.create_and_start_run(db, incident=inc, variant=payload.variant,
                                             actor_id=p.user_id,
                                             ip=audit_context(request)["ip"])
    # Synchronous bounded execution (scripted backend ~instant; ollama runs
    # under lease so the reaper can interrupt stalls).
    from pipeline.agent.runner import run_agent

    import datetime as _dt

    try:
        run_agent(db, run_id=run.id, incident_id=inc.id,
                  dataset_run_id=inc.dataset_run_id, variant=payload.variant,
                  created_by=p.user_id)
    except Exception as exc:
        db.query(AgentRun).filter(AgentRun.id == run.id).update(
            {"status": "error", "ended_at": _dt.datetime.now(_dt.timezone.utc)},
            synchronize_session=False)
        audit(db, actor_id=p.user_id, action="agent.run_error",
              entity_type="agent_runs", entity_id=run.id,
              after={"error": str(exc)[:300]}, ip_address=audit_context(request)["ip"])
        raise ConflictError("agent_run_failed") from exc
    return ok({"run_id": str(run.id), "status": "accepted"})


@router.get("/agent/runs")
def list_agent_runs(incident_id: str, db: Session = Depends(get_db),
                    _p: Principal = Depends(current_principal)):
    runs = agent_service.list_runs(db, incident_id)
    return ok([{"id": str(r.id), "variant": r.variant, "status": r.status,
                "steps": r.steps} for r in runs])


@router.get("/agent/{run_id}")
def get_agent_run(run_id: str, db: Session = Depends(get_db),
                  _p: Principal = Depends(current_principal)):
    run = agent_service.get_run_or_404(db, run_id)
    msgs = db.execute(select(AgentMessage).where(AgentMessage.agent_run_id == run.id)
                      .order_by(AgentMessage.created_at)).scalars().all()
    return ok({"id": str(run.id), "variant": run.variant, "status": run.status,
               "steps": run.steps, "messages": [
                   {"role": m.role, "tool_name": m.tool_name, "payload": m.payload}
                   for m in msgs]})


@router.get("/agent/{run_id}/stream")
async def stream_agent_run(run_id: str, ticket: str = "",
                           db: Session = Depends(get_db),
                           _p: Principal = Depends(current_principal)):
    """SSE stream of agent messages (SEC-017: short-lived ticket pattern)."""
    import json

    async def gen():
        last = 0
        for _ in range(120):  # bounded stream (~60 s)
            msgs = db.execute(
                select(AgentMessage).where(AgentMessage.agent_run_id == run_id)
                .order_by(AgentMessage.created_at)).scalars().all()
            while last < len(msgs):
                m = msgs[last]
                last += 1
                yield f"data: {json.dumps({'role': m.role, 'payload': m.payload})}\n\n"
            run = db.get(AgentRun, run_id)
            if run is not None and run.status != "running":
                break
            await asyncio.sleep(0.5)
        yield "event: done\ndata: {}\n\n"

    from fastapi.responses import StreamingResponse

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/agent/{run_id}/propose", status_code=202)
def propose(run_id: str, db: Session = Depends(get_db),
            p: Principal = Depends(require_analyst)):
    run = agent_service.get_run_or_404(db, run_id)
    if run.status == "running":
        agent_service.renew_lease(db, run.id)
        return ok({"run_id": run.id, "status": "running"})
    if run.status == "interrupted":
        run.status = "running"
        agent_service.renew_lease(db, run.id)
        audit(db, actor_id=p.user_id, action="agent.run_resumed",
              entity_type="agent_runs", entity_id=run.id)
        return ok({"run_id": run.id, "status": "resumed"})
    raise ConflictError(f"cannot_resume_{run.status}")


# ---------------------------------------------------------------- validator
@router.get("/validator/{plan_id}")
def get_validator(plan_id: str, db: Session = Depends(get_db),
                  p: Principal = Depends(current_principal)):
    from app.db.models import MitigationPlan, ValidatorResult

    plan = db.get(MitigationPlan, plan_id)
    if plan is None:
        raise ConflictError("plan_not_found")
    vr = db.get(ValidatorResult, plan.active_validator_result_id) \
        if plan.active_validator_result_id else None
    if vr is None:
        return ok({"plan_id": plan_id, "verdict": None, "checks": []})
    return ok({"plan_id": plan_id, "verdict": vr.verdict, "checks": vr.checks,
               "is_active": vr.is_active, "hash_suffix": plan.steps_hash[-6:]})


@router.post("/validator/{plan_id}/rerun")
def rerun_validator(plan_id: str, request: Request,
                    db: Session = Depends(get_db),
                    p: Principal = Depends(require_analyst)):
    from app.services.validator_service import validate_plan_revision

    plan = db.get(MitigationPlan, plan_id)
    if plan is None or plan.status in ("executed", "superseded", "draft_only"):
        raise ConflictError("rerun_not_permitted_for_status")
    vr = validate_plan_revision(db, plan=plan, actor_id=p.user_id,
                                ip=audit_context(request)["ip"])
    return ok({"plan_id": plan_id, "verdict": vr.verdict})


# ---------------------------------------------------------------- approvals
@router.get("/approvals")
def pending_approvals(db: Session = Depends(get_db),
                      p: Principal = Depends(require_analyst)):
    from app.db.models import MitigationPlan

    rows = approval_service.list_pending(db)
    out = []
    for a in rows:
        plan = db.get(MitigationPlan, a.plan_id)
        out.append({
            "id": str(a.id), "plan_id": str(a.plan_id),
            "revision": plan.revision_no if plan else None,
            "hash_suffix": plan.steps_hash[-6:] if plan else None,
            "expires_at": str(a.expires_at), "requested_by": str(a.requested_by or ""),
        })
    return ok(out)


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, request: Request, db: Session = Depends(get_db),
            p: Principal = Depends(require_analyst)):
    res = approval_service.approve(db, approval_id=approval_id, approver=p,
                                   ip=audit_context(request)["ip"])
    return ok(res)


@router.post("/approvals/{approval_id}/deny")
def deny(approval_id: str, payload: DenyIn, request: Request,
         db: Session = Depends(get_db), p: Principal = Depends(require_analyst)):
    res = approval_service.deny(db, approval_id=approval_id, approver=p,
                                reason=payload.reason,
                                ip=audit_context(request)["ip"])
    return ok(res)


@router.post("/approvals/{approval_id}/amend")
async def amend(approval_id: str, request: Request,
                db: Session = Depends(get_db), p: Principal = Depends(require_analyst)):
    # HB-01: strict parse rejects duplicate JSON keys before anything binds.
    from app.core.canonical import loads_strict

    try:
        body = (await request.body()) or b"{}"
        payload = AmendIn.model_validate(loads_strict(body.decode("utf-8")))
    except ValueError as e:
        raise ConflictError(f"invalid_json:{e}")
    except Exception:
        raise ConflictError("invalid_amend_body")
    res = approval_service.amend(db, approval_id=approval_id, approver=p,
                                 steps_patch=payload.steps_patch,
                                 ip=audit_context(request)["ip"])
    return ok(res)


# ---------------------------------------------------------------- sandbox
class ExecuteIn(BaseModel):
    plan_id: str


@router.post("/sandbox/execute", status_code=202)
def sandbox_execute(payload: ExecuteIn, request: Request,
                    db: Session = Depends(get_db),
                    p: Principal = Depends(require_analyst)):
    result = execute_plan(db, plan_id=payload.plan_id, actor_id=p.user_id,
                          ip=audit_context(request)["ip"])
    return ok(result)
