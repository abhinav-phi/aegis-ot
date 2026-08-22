"""Authentication & authorization primitives (DEC-012, §14 contract).

- Access: HS256 JWT, 15 min, claims {sub, role, jti, exp}, Bearer header.
- Refresh: opaque 256-bit random token, SHA-256 hashed at rest, 7-day TTL,
  httpOnly Secure SameSite=Lax cookie, rotated on every use, family revocation
  on reuse-detection.
- Passwords: Argon2id, minimum length 12.
- Login limiter: in-process fixed window per (ip, email).
- RBAC: server-side only (R14). Roles: admin > analyst > viewer.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError, ForbiddenError, RateLimited
from app.db.session import get_db

Role = Literal["admin", "analyst", "viewer"]
ROLE_ORDER: dict[str, int] = {"viewer": 0, "analyst": 1, "admin": 2}
MIN_PASSWORD_LEN = 12

_ph = PasswordHasher()
_SETTINGS = get_settings()
REFRESH_COOKIE = "aegis_refresh"


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError("password_too_short")
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, ValueError):
        return False


def create_access_token(user_id: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": secrets.token_hex(8),
        "iat": now,
        "exp": now + _SETTINGS.access_token_minutes * 60,
        "iss": "aegis-ot",
    }
    return jwt.encode(payload, _SETTINGS.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SETTINGS.secret_key, algorithms=["HS256"], issuer="aegis-ot")
    except jwt.ExpiredSignatureError as e:
        raise AuthError("token_expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthError("invalid_token") from e


def new_refresh_token() -> tuple[str, str]:
    """Return (plaintext, sha256-hash). Only the hash is persisted."""
    raw = secrets.token_urlsafe(32)  # 256 bits
    return raw, hashlib.sha256(raw.encode()).hexdigest()


class LoginLimiter:
    """Fixed-window failure counter keyed by (ip, email)."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._fails: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, key: tuple[str, str]) -> None:
        q = self._fails[key]
        now = time.time()
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_attempts:
            raise RateLimited("login_attempts_exceeded")

    def record_failure(self, key: tuple[str, str]) -> None:
        self._fails[key].append(time.time())

    def reset(self, key: tuple[str, str]) -> None:
        self._fails.pop(key, None)


limiter = LoginLimiter(_SETTINGS.login_max_attempts, _SETTINGS.login_window_minutes * 60)


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=_SETTINGS.refresh_token_days * 86400,
        httponly=True,
        secure=_SETTINGS.env != "dev",
        samesite="lax",
        path="/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/auth")


def get_client_ip(request: Request) -> str:
    # Server-observed socket peer only; no blind X-Forwarded-For trust.
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------- RBAC deps
class Principal:
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def has_role(self, minimum: str) -> bool:
        return ROLE_ORDER.get(self.role, -1) >= ROLE_ORDER[minimum]


def principal_from_request(
    request: Request, db: Session = Depends(get_db)
) -> Principal:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthError("missing_bearer_token")
    claims = decode_access_token(auth.removeprefix("Bearer ").strip())
    from app.db.models import User, UserRole

    user = db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise AuthError("inactive_or_unknown_user")
    role = db.execute(select(UserRole.role).where(UserRole.user_id == user.id)).scalar_one_or_none()
    return Principal(user_id=str(user.id), role=role or "viewer")


def current_principal(principal: Principal = Depends(principal_from_request)) -> Principal:
    return principal


def require_role(minimum: Role):
    def dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.has_role(minimum):
            raise ForbiddenError("insufficient_role")
        return principal

    return dep


require_analyst = require_role("analyst")
require_admin = require_role("admin")
