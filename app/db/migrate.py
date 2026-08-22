"""Alembic CLI wrapper (API-001): `python -m app.db.migrate [upgrade|stamp|current]`.

Backs the `make setup` acceptance path. URL comes from app settings.
"""
from __future__ import annotations

import sys

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def _config() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "app/db/migrations")
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    return cfg


def upgrade() -> None:
    command.upgrade(_config(), "head")


def stamp(revision: str = "head") -> None:
    command.stamp(_config(), revision)


def current() -> None:
    command.current(_config())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if cmd == "upgrade":
        upgrade()
    elif cmd == "stamp":
        stamp(*(sys.argv[2:3] or ["head"]))
    elif cmd == "current":
        current()
    else:
        print(f"unknown command: {cmd}")
        sys.exit(2)
