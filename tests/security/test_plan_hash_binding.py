"""INV-005 / DEC-001: hash binding across validate → approve → execute."""
from __future__ import annotations

import pytest

from app.core.canonical import steps_hash
from app.core.exceptions import ExecHashMismatch
from app.services.approval_service import amend, approve


def test_execute_after_raw_sql_hash_tamper_is_hard_blocked(db, scenario):
    from sqlalchemy import update

    from app.db.models import MitigationPlan
    from pipeline.sandbox.simulator import execute_plan

    approve(db, approval_id=scenario["approval"].id,
            approver=scenario["admin"])
    # Bypass the ORM identity map (simulating out-of-band DB tamper): mutate
    # the stored row only. Core-level UPDATE + synchronize_session=False is
    # portable (SQLite stores Uuid as hex; a hyphenated literal matches 0 rows)
    # and leaves the session's cached object stale on purpose.
    db.execute(
        update(MitigationPlan)
        .where(MitigationPlan.id == scenario["plan"].id)
        .values(steps=[])
        .execution_options(synchronize_session=False)
    )
    db.flush()
    with pytest.raises(ExecHashMismatch):
        execute_plan(db, plan_id=scenario["plan"].id,
                     actor_id=scenario["analyst"].user_id)


def test_approval_carries_plan_hash(db, scenario):
    assert scenario["approval"].plan_hash == scenario["plan"].steps_hash


def test_validator_result_bound_to_hash(db, scenario):
    assert scenario["validator"].plan_hash == scenario["plan"].steps_hash


def test_recomputed_hash_matches_stored(db, scenario):
    assert steps_hash(scenario["plan"].steps) == scenario["plan"].steps_hash


def test_amend_creates_new_revision_and_supersedes(db, scenario):
    res = amend(db, approval_id=scenario["approval"].id,
                approver=scenario["analyst"],
                steps_patch=[{"step_no": 1, "params": {"level_pct": 60.0}}])
    from app.db.models import MitigationPlan

    old = db.get(MitigationPlan, scenario["plan"].id)
    new = db.get(MitigationPlan, res["new_plan_id"])
    assert old.status == "superseded"
    assert new.revision_no == 2 and new.supersedes_id == old.id
    assert new.steps[0]["params"]["level_pct"] == 60.0


def test_amend_noop_rejected(db, scenario):

    from app.core.exceptions import ConflictError

    with pytest.raises(ConflictError):
        amend(db, approval_id=scenario["approval"].id,
              approver=scenario["analyst"],
              steps_patch=[{"step_no": 1}])
