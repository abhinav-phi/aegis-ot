"""v1.1 hardening columns + revision-monotonicity trigger (HASH/SEC/APP/REPRO).

Revision ID: 0003_hardening_v11
Revises: 0002_hardening_triggers
Create Date: 2026-08-22

Adds:
- mitigation_plans.canonical_bytes        (HASH-001/002)
- mitigation_plans.revision_created_by    (SEC-002 distinct-approver binding)
- mitigation_plans.execution_lease_until  (APP-002 executing-state reaper)
- simulated_actions.sim_config_hash       (REPRO-001)
- simulated_actions.plant_model_version   (REPRO-001)
- PG trigger: revision_no must strictly increase along supersedes chain (HB-08)

SQLite dev/test DBs get the columns via batch mode; the trigger is PG-only and
mirrored by a service-level assertion in approval_service.amend.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_hardening_v11"
down_revision = "0002_hardening_triggers"
branch_labels = None
depends_on = None

MONOTONIC_FN = """
CREATE OR REPLACE FUNCTION aegis_check_revision_monotonic() RETURNS trigger AS $$
BEGIN
    IF NEW.supersedes_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM mitigation_plans p
            WHERE p.id = NEW.supersedes_id AND p.revision_no >= NEW.revision_no
        ) THEN
            RAISE EXCEPTION 'revision_not_monotonic';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

MONOTONIC_TRIGGER = """
CREATE TRIGGER trg_revision_monotonic
BEFORE INSERT ON mitigation_plans
FOR EACH ROW EXECUTE FUNCTION aegis_check_revision_monotonic()
"""


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _existing_columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    # 0001 builds from current model metadata, so fresh databases already
    # carry these columns; guard every addition for idempotency.
    plan_have = _existing_columns("mitigation_plans")
    with op.batch_alter_table("mitigation_plans") as b:
        if "canonical_bytes" not in plan_have:
            b.add_column(sa.Column("canonical_bytes", sa.LargeBinary(), nullable=True))
        if "revision_created_by" not in plan_have:
            b.add_column(sa.Column("revision_created_by", sa.Uuid(), nullable=True))
        if "execution_lease_until" not in plan_have:
            b.add_column(sa.Column("execution_lease_until",
                                   sa.DateTime(timezone=True), nullable=True))
    sim_have = _existing_columns("simulated_actions")
    with op.batch_alter_table("simulated_actions") as b:
        if "sim_config_hash" not in sim_have:
            b.add_column(sa.Column("sim_config_hash", sa.String(64), nullable=True))
        if "plant_model_version" not in sim_have:
            b.add_column(sa.Column("plant_model_version", sa.String(32), nullable=True))
    if _is_postgres():
        op.execute(MONOTONIC_FN)
        op.execute(MONOTONIC_TRIGGER)


def downgrade() -> None:
    if _is_postgres():
        op.execute("DROP TRIGGER IF EXISTS trg_revision_monotonic ON mitigation_plans")
        op.execute("DROP FUNCTION IF EXISTS aegis_check_revision_monotonic()")
        op.execute("ALTER TABLE mitigation_plans DROP CONSTRAINT IF EXISTS fk_plans_revision_author")
    sim_have = _existing_columns("simulated_actions")
    with op.batch_alter_table("simulated_actions") as b:
        if "plant_model_version" in sim_have:
            b.drop_column("plant_model_version")
        if "sim_config_hash" in sim_have:
            b.drop_column("sim_config_hash")
    plan_have = _existing_columns("mitigation_plans")
    with op.batch_alter_table("mitigation_plans") as b:
        if "execution_lease_until" in plan_have:
            b.drop_column("execution_lease_until")
        if "revision_created_by" in plan_have:
            b.drop_column("revision_created_by")
        if "canonical_bytes" in plan_have:
            b.drop_column("canonical_bytes")
