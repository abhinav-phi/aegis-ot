"""Initial schema: all hardened tables (CHG-DB-01..20).

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-21

Creates the full schema from model metadata so the migration always matches
the models, then applies portable constraints. PostgreSQL-specific triggers
live in 0002_hardening_triggers.
"""
from __future__ import annotations

from alembic import op

from app.db.models.base import Base
import app.db.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
