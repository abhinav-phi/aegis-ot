"""E2E offline demo + EXP-08 suite through real services (scripted backend)."""
from __future__ import annotations


def test_exp08_suite_runs_and_hardened_beats_naive(db):
    from eval.attack_suite.runner import run_attack_suite

    result = run_attack_suite(db)
    assert result["cases"] >= 30
    assert result["naive"]["asr"] > result["hardened"]["asr"] or \
        result["relative_reduction"] > 0
    assert result["hardened"]["block_rate_on_unsafe"] >= 0.0


def test_exp09_battery_all_attempts_rejected(db, scenario):
    # Pre-amend so the 'execute_superseded_revision' attempt is meaningful.
    from app.services.approval_service import amend
    from eval.experiments import run_exp09

    amend(db, approval_id=scenario["approval"].id, approver=scenario["analyst"],
          steps_patch=[{"step_no": 1, "params": {"level_pct": 70.0}}])
    seed = {"incident": str(scenario["incident"].id),
            "plan": str(scenario["plan"].id),
            "approval": str(scenario["approval"].id),
            "run": str(scenario["run"].id)}
    result = run_exp09(db, seed)
    assert result["all_rejected"], result["attempts"]


def test_demo_flow_offline(db, users):
    from app.services.demo_service import run_demo

    result = run_demo(db, created_by=str(users["analyst"].id))
    assert result["naive"]["executed"] is False
    assert "SIMULATED" in result["labels"]
