"""SQLAlchemy engine/session management."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@event.listens_for(engine, "connect")
def _fk_pragma(dbapi_conn, _record):  # pragma: no cover - driver specific
    if _settings.database_url.startswith("sqlite"):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_lite_schema() -> None:
    """SQLite-only convenience for offline CLIs (demo/eval/pilot/kb_qa):
    create tables when the database is empty. PostgreSQL goes through
    Alembic (`python -m app.db.migrate` / make setup) — never this path."""
    if not _settings.database_url.startswith("sqlite"):
        return
    from app.db.immutability import register_immutability_listeners
    from app.db.models.base import Base

    register_immutability_listeners()
    Base.metadata.create_all(engine)
