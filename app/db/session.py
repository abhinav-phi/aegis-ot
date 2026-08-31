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
    _heal_sqlite_column_drift(engine)


def _heal_sqlite_column_drift(engine) -> None:
    """Self-heal a dev SQLite database created by an OLDER revision of the
    models. `create_all` never adds columns to existing tables, so a stale
    dev DB would crash ORM selects on newer models (e.g. a demo run on a DB
    missing `mitigation_plans.canonical_bytes`). Heals by ALTER TABLE ADD
    COLUMN for every model column missing from an existing table — only for
    nullable columns (SQLite cannot backfill NOT NULL); anything else prints
    guidance instead of corrupting the database.
    """
    from sqlalchemy import inspect, text

    from app.db.models.base import Base

    inspector = inspect(engine)
    healed = 0
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue  # created just now by create_all
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                if not col.nullable and col.default is None and col.server_default is None:
                    print(f"lite-schema: {table.name}.{col.name} is missing and NOT NULL "
                          f"without a default — delete the dev database and re-run "
                          f"`make seed` (no safe in-place heal exists)")
                    continue
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" ' \
                      f"{col.type.compile(engine.dialect)}"
                conn.execute(text(ddl))
                healed += 1
                print(f"lite-schema: healed {table.name}.{col.name} "
                      f"on {table.name} (schema drift from older revision)")
    if healed:
        print(f"lite-schema: {healed} column(s) healed")
