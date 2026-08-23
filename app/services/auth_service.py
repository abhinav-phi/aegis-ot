"""Authentication service: login, refresh rotation with family revocation,
logout, role assignment (DEC-012, §14 contract)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.security import (
    REFRESH_COOKIE,
    clear_refresh_cookie,
    create_access_token,
    limiter,
    new_refresh_token,
    set_refresh_cookie,
    verify_password,
)
from app.db.models import RefreshToken, User, UserRole
from app.services.audit import audit


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def login(db: Session, response: Response, *, email: str, password: str,
          ip: str, request_id: str = "-") -> dict:
    key = (ip, email)
    limiter.check(key)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    # Uniform failure semantics (anti-enumeration): identical error + timing shape.
    if user is None or not verify_password(user.password_hash, password):
        if user is not None:
            limiter.record_failure(key)
            audit(db, actor_id=None, action="auth.login_failed", entity_type="user",
                  entity_id=str(user.id), ip_address=ip)
        else:
            limiter.record_failure(key)
            audit(db, actor_id=None, action="auth.login_failed", entity_type="user",
                  ip_address=ip)
        raise AuthError("invalid_credentials", code="invalid_credentials")
    if not user.is_active:
        raise AuthError("invalid_credentials", code="invalid_credentials")

    raw, token_hash = new_refresh_token()
    family = str(uuid.uuid4())
    db.add(RefreshToken(
        user_id=user.id, token_hash=token_hash, family=family,
        expires_at=_utcnow() + dt.timedelta(days=get_settings().refresh_token_days),
    ))
    user.last_login_at = _utcnow()
    role_row = db.execute(select(UserRole.role).where(UserRole.user_id == user.id)).scalar_one_or_none()
    role = role_row or "viewer"
    audit(db, actor_id=user.id, action="auth.login", entity_type="user", after={"role": role})
    token = create_access_token(str(user.id), role)
    set_refresh_cookie(response, raw)
    return {"access_token": token, "token_type": "bearer", "role": role}


def refresh(db: Session, response: Response, raw_token: str | None) -> dict:
    if not raw_token:
        raise AuthError("missing_refresh_token", code="missing_refresh_token")
    token_hash = __import__("hashlib").sha256(raw_token.encode()).hexdigest()
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    # Reuse detection: a rotated/revoked token presented again ⇒ revoke family.
    if row is not None and (row.revoked_at is not None or row.expires_at < _utcnow()):
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family == row.family, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_utcnow())
        )
        audit(db, actor_id=row.user_id, action="auth.refresh_reuse_detected",
              entity_type="refresh_family", entity_id=row.family,
              after={"revoked_family": row.family})
        raise AuthError("invalid_refresh_token", code="invalid_refresh_token")
    if row is None or row.expires_at < _utcnow():
        raise AuthError("invalid_refresh_token", code="invalid_refresh_token")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthError("invalid_refresh_token", code="invalid_refresh_token")

    new_raw, new_hash = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=new_hash, family=row.family,
        expires_at=_utcnow() + dt.timedelta(days=get_settings().refresh_token_days),
    ))
    row.revoked_at = _utcnow()  # rotate: old token dies immediately

    role_row = db.execute(select(UserRole.role).where(UserRole.user_id == user.id)).scalar_one_or_none()
    role = role_row or "viewer"
    token = create_access_token(str(user.id), role)
    set_refresh_cookie(response, new_raw)
    audit(db, actor_id=user.id, action="auth.refresh", entity_type="user")
    return {"access_token": token, "token_type": "bearer", "role": role}


def logout(db: Session, response: Response, raw_token: str | None, actor_id: str | None) -> None:
    if raw_token:
        token_hash = __import__("hashlib").sha256(raw_token.encode()).hexdigest()
        row = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none()
        if row is not None:
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.family == row.family, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=_utcnow())
            )
            audit(db, actor_id=actor_id, action="auth.logout", entity_type="user")
    clear_refresh_cookie(response)


def cookie_raw_token(request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE)
