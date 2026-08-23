"""C5 consistency: evidence-field entailment + invariant-direction rules.

Deterministic (AEGIS-04): field matching and a static direction table only.
- Field match: any param whose key exists in cited evidence must equal the
  evidence value within tolerance; mismatch ⇒ flag category `field_mismatch`.
- Direction: if an invariant rule failed for the incident, actions listed in
  the direction table are inconsistent ⇒ flag category `invariant_conflict`.
Persistent C5 = same failure category on the two most recent validations of
the same incident ⇒ escalate (VAL-005).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

TOLERANCE = 1e-6


@dataclass
class ConsistencyResult:
    status: str  # pass | flag | escalate_input
    category: str | None = None
    detail: str = ""
    mismatches: list[str] = field(default_factory=list)


def load_direction_rules(path: str | Path = "configs/invariants.yaml") -> list[dict]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return list(raw.get("direction_rules") or [])


def check_consistency(
    step: dict,
    index,
    failed_invariants: list[str],
    direction_rules: list[dict] | None = None,
) -> ConsistencyResult:
    mismatches: list[str] = []

    # 1) Evidence-field consistency (only trusted citations considered).
    from pipeline.validator.provenance import has_trusted_support

    if has_trusted_support(step, index):
        for cid in step.get("citations") or []:
            ev = index.get(cid)
            if not ev or ev["tier"] != "trusted":
                continue
            fields = ev.get("fields") or {}
            for key, value in (step.get("params") or {}).items():
                if key in fields:
                    expected = fields[key]
                    try:
                        ok = abs(float(expected) - float(value)) <= TOLERANCE
                    except (TypeError, ValueError):
                        ok = str(expected) == str(value)
                    if not ok:
                        mismatches.append(f"{key}:{value}!={expected}")

    # 2) Invariant-direction consistency.
    rules = direction_rules if direction_rules is not None else load_direction_rules()
    action = step.get("action")
    conflict = None
    for rule in rules:
        if rule.get("when_rule_fails") in failed_invariants and \
           action in (rule.get("forbid_actions") or []):
            conflict = rule.get("when_rule_fails")
            break

    if conflict:
        return ConsistencyResult("flag", "invariant_conflict",
                                 f"direction_conflict:{conflict}", mismatches)
    if mismatches:
        return ConsistencyResult("flag", "field_mismatch",
                                 ";".join(mismatches[:5]), mismatches)
    return ConsistencyResult("pass", None, "consistent")


def is_persistent(current_category: str | None, prior_categories: list[str | None]) -> bool:
    """Same failure category on the two most recent validations ⇒ escalate."""
    if current_category is None:
        return False
    return bool(prior_categories) and prior_categories[-1] == current_category
