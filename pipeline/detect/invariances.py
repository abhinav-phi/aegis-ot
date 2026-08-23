"""Declarative invariant evaluation (DET-04, R-ML-14) + C5 direction support."""
from __future__ import annotations

from pathlib import Path

import yaml

_RULES_PATH = Path("configs/invariants.yaml")


def load_rules(path: Path = _RULES_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def evaluate_invariants(window: dict) -> dict:
    """Evaluate the five declarative rules over a window payload.

    `window` carries {"scores": [floats], "sensors": {...}, "levels": {...}?}.
    Rules operate on the data actually present; missing scope ⇒ pass with note.
    """
    rules = {r["id"]: r for r in load_rules().get("rules", [])}
    results: list[dict] = []
    sensors = window.get("sensors") or {}
    levels = window.get("levels") or sensors.get("levels") or {}
    flows = sensors.get("flows") or window.get("flows") or {}
    pumps = sensors.get("pumps") or window.get("pumps") or {}
    valves = sensors.get("valves") or window.get("valves") or {}
    scores = window.get("scores") or []

    def add(rule_id: str, passed: bool, detail: str) -> None:
        results.append({"rule_id": rule_id, "pass": bool(passed), "detail": detail})

    # R1 tank level range
    bad_levels = {k: v for k, v in levels.items() if not (0.0 <= float(v) <= 100.0)}
    add("R1_tank_level_range", not bad_levels, f"violations={list(bad_levels)}" if bad_levels else "ok")

    # R2 pump on ⇒ flow > 0.5
    r2_bad = []
    for pump, st in pumps.items():
        if st.get("on") and flows.get(pump.replace("P", "FIT", 1), 1.0) <= 0.5:
            r2_bad.append(pump)
    add("R2_pump_flow_consistency", not r2_bad, f"violations={r2_bad}" if r2_bad else "ok")

    # R3 valve closed ⇒ flow < 0.1
    r3_bad = []
    for valve, st in valves.items():
        if not st.get("open", True) and flows.get(valve.replace("MV", "FIT", 1), 0.0) >= 0.1:
            r3_bad.append(valve)
    add("R3_valve_flow_consistency", not r3_bad, f"violations={r3_bad}" if r3_bad else "ok")

    # R4 level rate limit (needs level series)
    series = window.get("level_series") or []
    ok = True
    for i in range(1, len(series)):
        if abs(series[i] - series[i - 1]) > 2.0:
            ok = False
            break
    add("R4_level_rate_limit", ok, "rate within bound" if ok else "rate exceeded")

    # R5 flow range
    r5_bad = {k: v for k, v in flows.items() if not (0.0 <= float(v) <= 15.0)}
    add("R5_flow_range", not r5_bad, f"violations={list(r5_bad)}" if r5_bad else "ok")

    # Score sanity: NaN/Inf never silently scored (R-ML-07).
    import math

    for i, s in enumerate(scores):
        if not math.isfinite(float(s)):
            add("R0_score_finite", False, f"non-finite score at {i}")
            break

    failed = [r["rule_id"] for r in results if not r["pass"]]
    # Attach each result to its declarative definition (R35: knobs live in
    # configs; THREAT-04: every check maps to its documented source).
    for r in results:
        meta = rules.get(r["rule_id"]) or {}
        r["expr"] = meta.get("expr")
        r["source"] = meta.get("source")
    return {"checks": results, "failed": failed, "all_pass": not failed}


def failed_rules_for_incident(db, incident) -> list[str]:
    """Best-effort invariant outcomes attached to the incident (C5 input)."""
    if incident is None:
        return []
    from app.db.models import Anomaly, AnomalyExplanation

    rows = db.execute(
        select(AnomalyExplanation.invariant_checks)
        .join(Anomaly, AnomalyExplanation.anomaly_id == Anomaly.id)
        .where(Anomaly.incident_id == incident.id)
        .limit(5)
    ).scalars().all()
    failed: set[str] = set()
    for checks in rows:
        for c in checks or []:
            if not c.get("pass", True):
                failed.add(c.get("rule_id"))
    return sorted(failed)


from sqlalchemy import select
