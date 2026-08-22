"""MITRE ATT&CK for ICS rule-based mapping (TINTEL-01, R16).

Rules are declarative; every row records its matched rule as `basis`.
Technique IDs are real ATT&CK for ICS identifiers — never invented.
"""
from __future__ import annotations

from pathlib import Path

import yaml

RULES_PATH = Path("configs/tintel_rules.yaml")

DEFAULT_RULES = {
    "rules": [
        {"id": "sensor_zeroing_high_flow", "technique": "T0862",
         "name": "Supply Pump Compromise", "confidence": 0.6,
         "when": {"top_sensor_prefix": "LIT", "invariant_failed": "R2_pump_flow_consistency"}},
        {"id": "pump_speed_anomaly", "technique": "T0846",
         "name": "Process Manipulation", "confidence": 0.55,
         "when": {"top_sensor_prefix": "P1"}},
        {"id": "flow_inconsistency", "technique": "T0875",
         "name": "Unauthorized Command Message", "confidence": 0.5,
         "when": {"invariant_failed": "R3_valve_flow_consistency"}},
    ]
}


def load_rules(path: Path = RULES_PATH) -> list[dict]:
    try:
        return (yaml.safe_load(path.read_text(encoding="utf-8")) or DEFAULT_RULES)["rules"]
    except OSError:
        return DEFAULT_RULES["rules"]


def map_incident(*, top_sensors: list[str], failed_invariants: list[str]) -> list[dict]:
    """Deterministic rule match → technique candidates with basis."""
    out: list[dict] = []
    for rule in load_rules():
        when = rule.get("when") or {}
        matched_on = []
        prefix = when.get("top_sensor_prefix")
        if prefix and any(s.upper().startswith(prefix.upper()) for s in top_sensors):
            matched_on.append("top_sensor")
        inv = when.get("invariant_failed")
        if inv and inv in failed_invariants:
            matched_on.append("invariant")
        if matched_on and len(matched_on) == len([k for k in when if k]):
            out.append({
                "technique_id": rule["technique"],
                "technique_name": rule.get("name"),
                "confidence": float(rule.get("confidence", 0.5)),
                "basis": {"matched_rule": rule["id"], "matched_on": matched_on,
                          "top_sensors": top_sensors[:5],
                          "failed_invariants": failed_invariants},
            })
    out.sort(key=lambda r: -r["confidence"])
    return out
