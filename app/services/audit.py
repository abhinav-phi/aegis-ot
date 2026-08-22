"""Centralized audit service (R13, INV-013).

Every security-sensitive mutation calls `audit()` inside the SAME transaction
as the mutation: the API session commits once, so a rollback removes both the
mutation and its audit row, and a commit guarantees both.
"""
from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, request_id_ctx
from app.db.models import AuditLog

log = get_logger("aegis.audit")

_CSV_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def audit(
    db: Session,
    *,
    actor_id: str | uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Insert one audit row on the caller's open transaction."""
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        before=before,
        after=after,
        request_id=request_id_ctx.get(),
        ip_address=ip_address,
    )
    db.add(row)
    db.flush()
    return row


def audit_failure(*, action: str, entity_type: str,
                  entity_id: str | None = None,
                  detail: dict | None = None) -> None:
    """AUD-001: failure-path audit in a FRESH transaction.

    The caller's transaction is rolling back (that's why this is a failure);
    writing here would be discarded. A separate short-lived session commits
    the forensic row independently. Never raises.
    """
    try:
        from app.db.session import SessionLocal

        with SessionLocal() as db2:
            row = AuditLog(
                actor_id=None, action=action, entity_type=entity_type,
                entity_id=entity_id, after=detail,
                request_id=request_id_ctx.get(),
            )
            db2.add(row)
            db2.commit()
    except Exception as exc:  # noqa: BLE001 — forensics must never break the path
        log.warning(f"audit_failure_write_failed:{exc}")


def _csv_safe(value: Any) -> str:
    """Neutralize spreadsheet formula injection (SEC-009)."""
    text = "" if value is None else str(value)
    if text.startswith(_CSV_DANGEROUS_PREFIXES):
        return "'" + text
    return text.replace("\r", " ").replace("\n", " ")


def export_csv(db: Session) -> str:
    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at)).scalars()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "created_at", "actor_id", "action", "entity_type",
         "entity_id", "request_id", "ip_address", "before", "after"]
    )
    for r in rows:
        writer.writerow(
            [
                _csv_safe(r.id), _csv_safe(r.created_at), _csv_safe(r.actor_id),
                _csv_safe(r.action), _csv_safe(r.entity_type), _csv_safe(r.entity_id),
                _csv_safe(r.request_id), _csv_safe(r.ip_address),
                _csv_safe(r.before), _csv_safe(r.after),
            ]
        )
    log.info("audit.export")
    return buf.getvalue()
