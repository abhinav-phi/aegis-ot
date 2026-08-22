"""Shared API dependencies: DB session, request-id middleware context."""
from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request


def request_id_dep(request: Request) -> str:
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    from app.core.logging import request_id_ctx

    request_id_ctx.set(rid)
    request.state.request_id = rid
    return rid


def audit_context(request: Request) -> dict:
    """Common kwargs for the audit service."""
    from app.core.security import get_client_ip

    return {"ip": get_client_ip(request), "request_id": getattr(request, "request_id", "-")}


def ok(data: dict | list) -> dict:
    return {"ok": True, "data": data}


def bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    return auth.removeprefix("Bearer ").strip() or None


cookie_token: Callable = lambda request: request.cookies.get("aegis_refresh")
