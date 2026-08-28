"""Incident lifecycle service (§11 state machine, DEC-008)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.db.models import Anomaly, Detection, Incident
from app.services.audit import audit
from app.services.state import incident_transition

SEVERITY_THRESHOLDS = {"critical": 6.0, "high": 3.0, "medium": 1.5}  # score → severity
GROUPING_GAP_S = 60


def _severity_for(score: float) -> str:
    for name, floor in SEVERITY_THRESHOLDS.items():
        if score >= floor:
            return name
    return "low"


def create_incidents_from_detections(db: Session, *, dataset_run_id,
                                     actor_id=None) -> list[Incident]:
    """Group adjacent anomalous windows (gap ≤ 60 s); link anomalies (CHG-DB-05)."""
    rows = db.execute(
        select(Detection)
        .where(Detection.dataset_run_id == dataset_run_id, Detection.is_anomaly.is_(True))
        .order_by(Detection.window_start)
    ).scalars().all()
    if not rows:
        return []

    groups: list[list[Detection]] = [[rows[0]]]
    for d in rows[1:]:
        prev_end = groups[-1][-1].window_start
        if (d.window_start - prev_end).total_seconds() <= GROUPING_GAP_S:
            groups[-1].append(d)
        else:
            groups.append([d])

    existing_starts = {
        i.start_ts for i in db.execute(
            select(Incident).where(Incident.dataset_run_id == dataset_run_id)).scalars()
    }
    created: list[Incident] = []
    now = dt.datetime.now(dt.UTC)
    for g in groups:
        if g[0].window_start in existing_starts:
            continue  # idempotent grouping on rerun
        peak = max(x.score for x in g)
        incident = Incident(
            dataset_run_id=dataset_run_id, start_ts=g[0].window_start,
            end_ts=g[-1].window_start, severity=_severity_for(peak),
            status="open", title=f"Incident {g[0].window_start:%Y-%m-%d %H:%M}",
            created_by=actor_id, created_at=now,
        )
        db.add(incident)
        db.flush()
        anomalies = db.execute(
            select(Anomaly).join(Detection, Anomaly.detection_id == Detection.id)
            .where(Detection.dataset_run_id == dataset_run_id,
                   Detection.window_start >= g[0].window_start,
                   Detection.window_start <= g[-1].window_start)
        ).scalars().all()
        for a in anomalies:
            a.incident_id = incident.id
        created.append(incident)
    audit(db, actor_id=actor_id, action="incident.created", entity_type="incidents",
          after={"count": len(created)})
    return created


def get_incident_or_404(db: Session, incident_id) -> Incident:
    from app.core.exceptions import NotFoundError

    inc = db.get(Incident, incident_id)
    if inc is None:
        raise NotFoundError("incident_not_found")
    return inc


def close_no_action(db: Session, *, incident_id, actor_id, ip=None) -> Incident:
    inc = get_incident_or_404(db, incident_id)
    incident_transition(db, inc.id, "open", "closed",
                        extra={"closed_reason": "no_action", "closed_by": actor_id})
    audit(db, actor_id=actor_id, action="incident.closed", entity_type="incidents",
          entity_id=inc.id, after={"reason": "no_action"}, ip_address=ip)
    db.refresh(inc)
    return inc


def resolve_escalation(db: Session, *, incident_id, actor_id, ip=None) -> Incident:
    inc = get_incident_or_404(db, incident_id)
    incident_transition(db, inc.id, "escalated", "closed",
                        extra={"closed_reason": "escalated", "closed_by": actor_id})
    audit(db, actor_id=actor_id, action="incident.escalation_resolved",
          entity_type="incidents", entity_id=inc.id, ip_address=ip)
    db.refresh(inc)
    return inc


def retry_after_rejection(db: Session, *, incident_id) -> None:
    """rejected → analyzing is allowed only when a new run actually starts;
    the agent-run creation endpoint performs the transition."""
    inc = get_incident_or_404(db, incident_id)
    if inc.status not in ("open", "rejected"):
        raise ConflictError(f"cannot_start_run_from_{inc.status}")
