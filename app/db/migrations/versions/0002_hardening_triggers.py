"""PostgreSQL hardening triggers + grants (CHG-DB-19, INV-005).

Revision ID: 0002_hardening_triggers
Revises: 0001_initial
Create Date: 2026-08-21

- BEFORE UPDATE trigger on mitigation_plans rejects any change to protected
  revision columns even when bypassing the ORM.
- Revoke UPDATE/DELETE on audit_logs from the application role (append-only).
No-ops (documented) on SQLite dev/test databases, where the ORM listener in
app/db/immutability.py provides the equivalent guarantee.
"""
from __future__ import annotations

from alembic import op

revision = "0002_hardening_triggers"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

PLAN_IMMUTABLE_FN = """
CREATE OR REPLACE FUNCTION aegis_protect_plan_revision() RETURNS trigger AS $$
BEGIN
    IF NEW.steps        IS DISTINCT FROM OLD.steps
       OR NEW.steps_hash    IS DISTINCT FROM OLD.steps_hash
       OR NEW.incident_id   IS DISTINCT FROM OLD.incident_id
       OR NEW.agent_run_id  IS DISTINCT FROM OLD.agent_run_id
       OR NEW.revision_no   IS DISTINCT FROM OLD.revision_no
       OR NEW.supersedes_id IS DISTINCT FROM OLD.supersedes_id THEN
        RAISE EXCEPTION 'plan_revision_immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

TRIGGER = """
CREATE TRIGGER trg_plan_revision_immutable
BEFORE UPDATE ON mitigation_plans
FOR EACH ROW EXECUTE FUNCTION aegis_protect_plan_revision()
"""


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    op.execute(PLAN_IMMUTABLE_FN)
    op.execute(TRIGGER)
    op.execute("REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC")


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute("DROP TRIGGER IF EXISTS trg_plan_revision_immutable ON mitigation_plans")
    op.execute("DROP FUNCTION IF EXISTS aegis_protect_plan_revision()")
