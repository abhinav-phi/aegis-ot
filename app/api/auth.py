"""Auth + users + health routers (§14 contract)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.exceptions import ForbiddenError
from app.core.security import (
    Principal,
    current_principal,
    get_client_ip,
    hash_password,
    require_admin,
)
from app.db.models import User, UserRole
from app.db.session import get_db
from app.services import audit as audit_svc
from app.services import auth_service

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RoleIn(BaseModel):
    role: str


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str | None = None
    role: str = "viewer"


@router.post("/auth/login")
def login(payload: LoginIn, request: Request, response: Response,
          db: Session = Depends(get_db)):
    result = auth_service.login(
        db, response, email=payload.email, password=payload.password,
        ip=get_client_ip(request))
    return ok(result)


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = auth_service.cookie_raw_token(request)
    return ok(auth_service.refresh(db, response, raw))


@router.post("/auth/logout")
def logout(request: Request, response: Response,
           principal: Principal = Depends(current_principal),
           db: Session = Depends(get_db)):
    raw = auth_service.cookie_raw_token(request)
    auth_service.logout(db, response, raw, actor_id=principal.user_id)
    return ok({"logged_out": True})


@router.get("/auth/me")
def me(principal: Principal = Depends(current_principal)):
    return ok({"user_id": principal.user_id, "role": principal.role})


# ---------------------------------------------------------------- users
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")
def list_users(db: Session = Depends(get_db),
               _admin: Principal = Depends(require_admin)):
    rows = db.execute(select(User)).scalars().all()
    roles = {r.user_id: r.role for r in db.execute(select(UserRole)).scalars()}
    return ok([{"id": str(u.id), "email": u.email, "display_name": u.display_name,
                "is_active": u.is_active, "role": roles.get(u.id)}
               for u in rows])


@users_router.post("", status_code=201)
def create_user(payload: UserIn, db: Session = Depends(get_db),
                admin: Principal = Depends(require_admin)):
    user = User(email=payload.email, password_hash=hash_password(payload.password),
                display_name=payload.display_name)
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role=payload.role))
    audit_svc.audit(db, actor_id=admin.user_id, action="user.created",
                    entity_type="users", entity_id=user.id,
                    after={"role": payload.role})
    return ok({"id": str(user.id)})


@users_router.patch("/{user_id}")
def update_user(user_id: str, request: Request,
                db: Session = Depends(get_db),
                admin: Principal = Depends(require_admin)):
    body = request.query_params
    user = db.get(User, user_id)
    if user is None:
        raise ForbiddenError("user_not_found")
    before = {"is_active": user.is_active}
    if "is_active" in body:
        user.is_active = body["is_active"].lower() in ("true", "1")
    audit_svc.audit(db, actor_id=admin.user_id, action="user.updated",
                    entity_type="users", entity_id=user.id, before=before,
                    after={"is_active": user.is_active})
    return ok({"id": str(user.id), "is_active": user.is_active})


@users_router.put("/{user_id}/role")
def set_role(user_id: str, payload: RoleIn, db: Session = Depends(get_db),
             admin: Principal = Depends(require_admin)):
    from app.core.exceptions import NotFoundError
    from app.core.security import ROLE_ORDER

    if payload.role not in ROLE_ORDER:
        raise ForbiddenError("invalid_role")
    row = db.execute(select(UserRole).where(UserRole.user_id == user_id)).scalar_one_or_none()
    if row is None:
        if db.get(User, user_id) is None:
            raise NotFoundError("user_not_found")
        row = UserRole(user_id=user_id, role=payload.role)
        db.add(row)
    else:
        row.role = payload.role  # R14: server-authoritative via this endpoint only
    audit_svc.audit(db, actor_id=admin.user_id, action="user.role_set",
                    entity_type="user_roles", entity_id=user_id,
                    after={"role": payload.role})
    return ok({"user_id": user_id, "role": payload.role})


# ---------------------------------------------------------------- health
health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}


@health_router.get("/health/worker")
def worker_health():
    import datetime as dt
    from pathlib import Path

    hb = Path(".worker_heartbeat")
    alive = False
    if hb.exists():
        age = dt.datetime.now(dt.UTC).timestamp() - hb.stat().st_mtime
        alive = age < 60
    return {"worker_alive": alive}
