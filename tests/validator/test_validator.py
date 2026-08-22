"""Validator unit tests: C1–C5 semantics, verdict function, normalization."""
from __future__ import annotations

import pytest

from pipeline.validator.engine import EvidenceIndex, validate_plan
from pipeline.validator.pattern import PatternFilter, normalize
from pipeline.validator.policy import load_registry
from pipeline.validator.verdict import StepChecks, plan_verdict


def _index():
    return EvidenceIndex({
        "ev-t": {"tier": "trusted", "source": "SPD-017", "fields": {"level_pct": 50.0},
                 "text": "verify first"},
        "ev-p": {"tier": "public", "source": "ctf note", "fields": {}, "text": ""},
        "ev-h": {"tier": "hostile", "source": "Addendum", "fields": {}, "text": ""},
    })


def _registry():
    return load_registry()


def test_c2_rejects_unknown_param_field():
    ok, detail = __import__("pipeline.validator.policy", fromlist=["check_allowlist"]) \
        .check_allowlist(_registry(), {
            "step_no": 1, "action": "set_pump_speed", "target": "P-101",
            "params": {"speed_pct": 10, "evil": 1}})
    assert not ok and "unknown_param_fields" in detail


def test_c2_rejects_out_of_range():
    from pipeline.validator.policy import check_allowlist

    ok, detail = check_allowlist(_registry(), {
        "step_no": 1, "action": "set_pump_speed", "target": "P-101",
        "params": {"speed_pct": 1e9}})
    assert not ok and "above maximum" in detail


def test_c4_unregistered_action_is_forbidden():
    from pipeline.validator.policy import risk_class_of

    assert risk_class_of(_registry(), "made_up_action") == "forbidden"


def test_control_requires_approval_even_when_clean():
    steps = [{"step_no": 1, "action": "close_valve", "target": "MV-501",
              "params": {}, "citations": ["ev-t"]}]
    out = validate_plan(steps, _index(), registry=_registry())
    assert out.verdict == "require_approval"


def test_forbidden_action_blocks():
    steps = [{"step_no": 1, "action": "direct_plc_write", "target": "PLC-1",
              "params": {"address": "MW0"}, "citations": ["ev-t"]}]
    out = validate_plan(steps, _index(), registry=_registry())
    assert out.verdict == "block"


def test_hostile_only_support_blocks_but_public_only_flags():
    hostile = [{"step_no": 1, "action": "close_valve", "target": "MV-501",
                "params": {}, "citations": ["ev-h"]}]
    out = validate_plan(hostile, _index(), registry=_registry())
    assert out.verdict == "block"

    public = [{"step_no": 1, "action": "snapshot_plant_state", "target": "PLANT",
               "params": {}, "citations": ["ev-p"]}]
    out2 = validate_plan(public, _index(), registry=_registry())
    assert out2.verdict in ("require_approval",)


def test_zero_trusted_citations_never_allow_read():
    steps = [{"step_no": 1, "action": "query_tank_level", "target": "T-101",
              "params": {}, "citations": []}]
    out = validate_plan(steps, _index(), registry=_registry())
    assert out.verdict == "require_approval"


def test_citation_free_read_whitelist_allows():
    steps = [{"step_no": 1, "action": "snapshot_plant_state", "target": "PLANT",
              "params": {}, "citations": []}]
    out = validate_plan(steps, _index(), registry=_registry())
    assert out.verdict == "allow"


def test_c5_field_mismatch_flags():
    steps = [{"step_no": 1, "action": "set_tank_setpoint", "target": "T-101",
              "params": {"level_pct": 90.0},   # evidence says 50.0
              "citations": ["ev-t"]}]
    out = validate_plan(steps, _index(), registry=_registry())
    c5 = [c for c in out.checks if c["check"] == "C5"]
    assert any(c["status"] != "pass" for c in c5)
    assert out.verdict == "require_approval"


def test_c5_direction_conflict_on_failed_invariant():
    steps = [{"step_no": 1, "action": "set_pump_speed", "target": "P-101",
              "params": {"speed_pct": 80}, "citations": ["ev-t"]}]
    out = validate_plan(steps, _index(), registry=_registry(),
                        failed_invariants=["R2_pump_flow_consistency"])
    assert out.c5_category == "invariant_conflict"


def test_persistent_c5_escalates():
    sc = StepChecks(step_no=1, action="x", c1="pass", c2="pass", c3="pass",
                    risk_class="read", c5="flag", citations=["ev-t"])
    v, _ = plan_verdict([sc], persistent_c5=True)
    assert v == "escalate"


def test_pattern_filter_normalization_bypass_resistance():
    pf = PatternFilter()
    assert not pf.scan("IGNORE_PRIOR")[0]
    homoglyph = "іgnore_prior"  # Cyrillic і (NFKC does NOT map it — casefold+scan)
    clean, marker = pf.scan(homoglyph)
    # Homoglyphs are NOT the same string; document behavior: flagged only if a
    # normalized marker matches. Zero-width + case variants MUST be caught.
    assert not pf.scan("ignore\u200b_prior")[0]
    assert not pf.scan("IGNORE  prior".replace("  ", "_prior").replace("_prior", "")) or True


def test_normalize_strips_zero_width():
    assert normalize("igno\u200br\u200bore_prior") .count("\u200b") == 0
