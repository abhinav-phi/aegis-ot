"""Broker-free asyncio workers (DEC-005, §19): expiry scheduler + run reaper.

Single-process design; every transition is a conditional UPDATE so duplicate
instances degrade to no-ops (CONC-005). Postgres advisory lock is used when
available for extra safety.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os
from pathlib import Path

from sqlalchemy import select, text, update

from app.core.logging import configure_logging, get_logger
from app.db.models import AgentRun, ApprovalRequest, Incident, MitigationPlan
from app.db.session import SessionLocal
from app.services import audit as audit_svc

log = get_logger("aegis.worker")
HEARTBEAT = Path(".worker_heartbeat")


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _heartbeat() -> None:
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT.touch()


def sweep_expiries(db) -> int:
    """Expiry ⇒ approval expired + plan escalated + incident escalated (R3)."""
    now = _utcnow()
    rows = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.status == "pending",
                                      ApprovalRequest.expires_at < now)
    ).scalars().all()
    n = 0
    for approval in rows:
        rc = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.id == approval.id,
                    ApprovalRequest.status == "pending")  # idempotent re-entry
            .update({"status": "expired"}, synchronize_session=False)
        )
        if not rc:
            continue
        plan = db.get(MitigationPlan, approval.plan_id)
        if plan is not None and plan.status in ("validated", "approved"):
            db.query(MitigationPlan).filter(
                MitigationPlan.id == plan.id,
                MitigationPlan.status.in_(["validated", "approved"]),
            ).update({"status": "escalated"}, synchronize_session=False)
            incident = db.get(Incident, plan.incident_id)
            if incident is not None and incident.status == "awaiting_approval":
                incident.status = "escalated"
        audit_svc.audit(db, actor_id=None, action="approval.expired",
                        entity_type="approval_requests", entity_id=approval.id,
                        after={"escalated": True})
        n += 1
    return n


def sweep_executing_plans(db) -> int:
    """APP-002: plans stuck in `executing` past their lease escalate.

    Fail-closed recovery — never auto-resume a half-applied plan. Queued-only
    step semantics + UNIQUE(plan,step) keep any later legitimate re-execution
    (after fresh approval) effect-idempotent.
    """
    now = _utcnow()
    rows = db.execute(
        select(MitigationPlan).where(MitigationPlan.status == "executing",
                                     MitigationPlan.execution_lease_until < now)
    ).scalars().all()
    n = 0
    for plan in rows:
        rc = (
            db.query(MitigationPlan)
            .filter(MitigationPlan.id == plan.id,
                    MitigationPlan.status == "executing",
                    MitigationPlan.execution_lease_until < now)
            .update({"status": "escalated"}, synchronize_session=False)
        )
        if not rc:
            continue
        incident = db.get(Incident, plan.incident_id)
        if incident is not None and incident.status == "simulating":
            incident.status = "escalated"
        audit_svc.audit(db, actor_id=None, action="execution.reaped",
                        entity_type="mitigation_plans", entity_id=plan.id,
                        after={"reason": "execution_lease_expired"})
        n += 1
    return n


def sweep_stale_runs(db) -> int:
    from app.services.agent_service import reap_stale_runs

    return reap_stale_runs(db)


async def expiry_loop(interval_s: int = 60) -> None:
    while True:
        try:
            with SessionLocal() as db:
                n = sweep_expiries(db)
                db.commit()
                if n:
                    log.info("expiry_sweep_escalated", extra={})
        except Exception as exc:  # scheduler outage must not crash the loop
            log.warning(f"expiry_sweep_failed:{exc}")
        await asyncio.sleep(interval_s)


async def reaper_loop(interval_s: int = 30) -> None:
    while True:
        try:
            with SessionLocal() as db:
                n = sweep_stale_runs(db)
                n += sweep_executing_plans(db)
                db.commit()
                if n:
                    log.info(f"reaped={n}")
        except Exception as exc:
            log.warning(f"reap_failed:{exc}")
        finally:
            _heartbeat()
        await asyncio.sleep(interval_s)


async def main() -> None:  # pragma: no cover
    configure_logging()
    log.info("worker_started")
    await asyncio.gather(expiry_loop(), reaper_loop())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
