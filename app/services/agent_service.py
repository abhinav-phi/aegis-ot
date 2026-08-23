"""Agent service: run creation (DEC-005), lease claim, audit, naive lockout."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError
from app.db.models import AgentRun, Incident
from app.services import audit as audit_svc
from app.services.state import incident_transition

# AGENT-001 lease parameters — derived, not arbitrary:
# worst-case step = LLM timeout 90 s × 1 retry + tool budget ⇒ TTL ≥ 2× step.
LEASE_TTL_S = 300
HEARTBEAT_S = 100  # ≤ TTL/3 so a live worker always outlives the reaper window


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def create_and_start_run(db: Session, *, incident: Incident, variant: str,
                         actor_id, ip: str | None = None) -> AgentRun:
    from pipeline.agent.runner import create_run

    # INV-015: ≤1 active run per incident — enforced below AND by the DB
    # partial unique index. Re-entry from `analyzing` is permitted only when
    # no active run exists (e.g. naive→hardened comparison arms, AppFlow §4).
    if incident.status not in ("open", "rejected", "analyzing"):
        raise ConflictError(f"cannot_start_run_from_{incident.status}")

    active = db.execute(
        select(AgentRun).where(AgentRun.incident_id == incident.id,
                               AgentRun.status == "running")
    ).scalar_one_or_none()
    if active is not None:
        raise ConflictError("active_run_exists_for_incident")

    # rejected → analyzing on retry; open → analyzing on first run.
    if incident.status == "rejected":
        incident_transition(db, incident.id, "rejected", "analyzing")
    elif incident.status == "open":
        incident_transition(db, incident.id, "open", "analyzing")

    run = create_run(db, incident=incident, variant=variant, created_by=actor_id)
    audit_svc.audit(db, actor_id=actor_id, action="agent.run_created",
                    entity_type="agent_runs", entity_id=run.id,
                    after={"variant": variant}, ip_address=ip)
    return run


def claim_lease(db: Session, run_id, minutes: int | None = None) -> bool:
    """Worker claim: only expired/absent leases can be taken."""
    ttl = minutes if minutes is not None else LEASE_TTL_S // 60
    rc = (
        db.query(AgentRun)
        .filter(AgentRun.id == run_id, AgentRun.status == "running")
        .filter((AgentRun.lease_until.is_(None)) | (AgentRun.lease_until < _utcnow()))
        .update({"lease_until": _utcnow() + dt.timedelta(minutes=ttl)},
                synchronize_session=False)
    )
    return rc == 1


def renew_lease(db: Session, run_id, seconds: int | None = None) -> None:
    """AGENT-001: conditional heartbeat — a 0-row update means the reaper or
    an interrupt path already took the run; callers must stop writing."""
    secs = seconds if seconds is not None else HEARTBEAT_S
    db.query(AgentRun).filter(
        AgentRun.id == run_id,
        AgentRun.status == "running",
    ).update({"lease_until": _utcnow() + dt.timedelta(seconds=secs)},
             synchronize_session=False)


def assert_run_active(db: Session, run_id) -> None:
    """AGENT-001 stale-writer guard: raises once the run is no longer running."""
    from app.core.exceptions import ForbiddenError

    row = db.execute(
        select(AgentRun.status).where(AgentRun.id == run_id)
    ).scalar_one_or_none()
    if row != "running":
        raise ForbiddenError("stale_agent_run_write_rejected")


def assert_not_naive_plan(db: Session, plan) -> None:
    """INV-010 service-layer gate (sandbox re-checks independently)."""
    run = db.get(AgentRun, plan.agent_run_id)
    if run is not None and run.variant == "naive":
        raise ForbiddenError("naive_variant_execution_forbidden")


def reap_stale_runs(db: Session, max_idle_minutes: int = 15) -> int:
    """Reaper: running runs with expired leases → interrupted (AGENT-005)."""
    stale = db.execute(
        select(AgentRun).where(AgentRun.status == "running",
                               AgentRun.lease_until < _utcnow())
    ).scalars().all()
    n = 0
    for run in stale:
        run.status = "interrupted"
        run.ended_at = _utcnow()
        n += 1
        audit_svc.audit(db, actor_id=None, action="agent.run_reaped",
                        entity_type="agent_runs", entity_id=run.id)
    return n
