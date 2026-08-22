"""Shared test fixtures: SQLite in-memory DB + FastAPI overrides + seeds."""
from __future__ import annotations

import datetime as dt
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("AEGIS_OT_ENV", "dev")
os.environ.setdefault("AEGIS_OT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("AEGIS_OT_DATABASE_URL", "sqlite://")
os.environ.setdefault("AEGIS_OT_OBJECT_STORE", "local")
os.environ.setdefault("AEGIS_OT_LOCAL_OBJECT_ROOT", ".test-objects")
os.environ.setdefault("AEGIS_OT_VECTOR_STORE", "local")
os.environ.setdefault("AEGIS_OT_LOCAL_VECTOR_ROOT", ".test-vectors")
os.environ.setdefault("AEGIS_OT_LLM_BACKEND", "scripted")

from app.core.canonical import steps_hash  # noqa: E402
from app.db.immutability import register_immutability_listeners  # noqa: E402
from app.db.models import (  # noqa: E402
    AgentRun,
    ApprovalRequest,
    Dataset,
    DatasetRun,
    Detection,
    Incident,
    MitigationPlan,
    User,
    UserRole,
    ValidatorResult,
)
from app.db.models.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.db.session import get_db  # noqa: E402

register_immutability_listeners()

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    s = TestingSession()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@pytest.fixture
def client(db):
    def override():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def users(db) -> dict[str, User]:
    from app.core.security import hash_password

    out = {}
    for email, role in [("admin@example.com", "admin"), ("analyst@example.com", "analyst"),
                        ("analyst2@example.com", "analyst"), ("viewer@example.com", "viewer")]:
        u = User(email=email, password_hash=hash_password("password-12-chars"))
        db.add(u)
        db.flush()
        db.add(UserRole(user_id=u.id, role=role))
        out[role if role != "analyst" or "analyst" not in out else "analyst2"] = u
    out["analyst2"] = db.execute(select(User).where(User.email == "analyst2@example.com")).scalar_one()
    db.flush()
    return out


SAFE_STEPS = [{
    "step_no": 1, "action": "set_tank_setpoint", "target": "T-101",
    "params": {"level_pct": 50.0}, "citations": ["ev-trusted"],
}]


def make_evidence_index() -> dict:
    return {"ev-trusted": {"tier": "trusted", "source": "SPD-017 playbook",
                           "fields": {}, "text": "SPD-017 verify first"}}


@pytest.fixture
def scenario(db, users) -> dict:
    """Full validated+approved scenario built through REAL services."""
    from app.core.security import Principal
    from app.services.validator_service import validate_plan_revision

    ds = Dataset(key="synthetic", display_name="t", sha256="0" * 64,
                 sensor_columns=["FIT101", "LIT101"])
    db.add(ds)
    db.flush()
    drun = DatasetRun(dataset_id=ds.id, run_name="t-train", config_hash="t",
                      split_role="train", minio_root="x/", status="completed")
    db.add(drun)
    db.flush()
    inc = Incident(dataset_run_id=drun.id, start_ts=dt.datetime(2026, 1, 1,
                   tzinfo=dt.timezone.utc), end_ts=dt.datetime(2026, 1, 1,
                   tzinfo=dt.timezone.utc), severity="high", status="open")
    db.add(inc)
    db.flush()
    run = AgentRun(incident_id=inc.id, model_name="scripted-offline",
                   variant="grounded_validated", status="running",
                   config_hash="test-config-hash",  # schema-derived: NOT NULL (TEST-002)
                   created_by=users["analyst"].id)
    db.add(run)
    db.flush()
    incident_transition_helper(db, inc)
    plan = MitigationPlan(incident_id=inc.id, agent_run_id=run.id, revision_no=1,
                          steps=SAFE_STEPS, steps_hash=steps_hash(SAFE_STEPS),
                          status="draft_for_validation")
    db.add(plan)
    db.flush()
    validate_plan_revision(db, plan=plan)
    approval = db.execute(select(ApprovalRequest).where(
        ApprovalRequest.plan_id == plan.id)).scalar_one()
    vr = db.get(ValidatorResult, plan.active_validator_result_id)
    return {"incident": inc, "run": run, "plan": plan, "approval": approval,
            "validator": vr, "analyst": Principal(str(users["analyst"].id), "analyst"),
            "admin": Principal(str(users["admin"].id), "admin"),
            "analyst2": Principal(str(users["analyst2"].id), "analyst"),
            "viewer": Principal(str(users["viewer"].id), "viewer")}


def incident_transition_helper(db, inc) -> None:
    inc.status = "awaiting_approval"
    db.flush()
