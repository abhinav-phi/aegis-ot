"""Policy engine: action/target registry + plan-level composition rules (R2).

Implements C2 (strict allowlist: unknown fields/types/ranges rejected), C4
(canonical risk classification), and the plan-level composition policy
(VAL-002): `forbidden_combinations` (never co-occur) and `required_order`
(first action must precede the second when both are present).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.core.exceptions import ValidationFailed

_PARAM_TYPES = {"string": str, "float": float, "int": int, "bool": bool}


@dataclass
class ParamSpec:
    type: str = "float"
    required: bool = False
    min: float | None = None
    max: float | None = None

    def validate(self, key: str, value) -> str | None:
        want = _PARAM_TYPES[self.type]
        if isinstance(value, bool) and self.type != "bool":
            return f"{key}: bool not allowed"
        if not isinstance(value, want):
            return f"{key}: expected {self.type}"
        if self.type in ("float", "int"):
            v = float(value)
            if self.min is not None and v < self.min:
                return f"{key}: below minimum {self.min}"
            if self.max is not None and v > self.max:
                return f"{key}: above maximum {self.max}"
        return None


@dataclass
class ActionSpec:
    name: str
    risk: str
    targets: list[str] = field(default_factory=list)
    params: dict[str, ParamSpec] = field(default_factory=dict)
    citation_free_read: bool = False


class PolicyRegistry:
    def __init__(self, actions: dict[str, ActionSpec],
                 forbidden_combinations: list[tuple[str, str]] | None = None,
                 required_order: list[tuple[str, str]] | None = None,
                 evidence_freshness_s: int | None = None):
        self.actions = actions
        self.forbidden_combinations = forbidden_combinations or []
        self.required_order = required_order or []
        self.evidence_freshness_s = evidence_freshness_s

    def get(self, action: str) -> ActionSpec | None:
        # Canonical exact-match lookup only (VAL-004: no fuzzy aliasing).
        return self.actions.get(action)


def load_registry(path: str | Path = "configs/policy/actions.yaml") -> PolicyRegistry:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    actions: dict[str, ActionSpec] = {}
    for name, spec in (raw.get("actions") or {}).items():
        params = {
            k: ParamSpec(
                type=v.get("type", "float"),
                required=bool(v.get("required", False)),
                min=v.get("min"),
                max=v.get("max"),
            )
            for k, v in (spec.get("params") or {}).items()
        }
        actions[name] = ActionSpec(
            name=name,
            risk=spec.get("risk", "forbidden"),
            targets=list(spec.get("targets") or []),
            params=params,
            citation_free_read=bool(spec.get("citation_free_read", False)),
        )
    combos = [tuple(c) for c in (raw.get("forbidden_combinations") or [])]
    order = [tuple(o) for o in (raw.get("required_order") or [])]
    freshness = raw.get("evidence_freshness_s")
    return PolicyRegistry(actions, combos, order,
                          int(freshness) if freshness else None)


def check_allowlist(registry: PolicyRegistry, step: dict) -> tuple[bool, str]:
    """C2 per-step. Unknown fields are REJECTED (VAL-003 strict schema)."""
    allowed_keys = {"step_no", "action", "target", "params", "citations"}
    unknown = set(step.keys()) - allowed_keys
    if unknown:
        return False, f"unknown_fields:{sorted(unknown)}"
    action = step.get("action")
    target = step.get("target")
    if not isinstance(action, str) or not isinstance(target, str):
        return False, "action/target must be strings"
    spec = registry.get(action)
    if spec is None:
        return False, f"unregistered_action:{action}"
    if "*" not in spec.targets and target not in spec.targets:
        if not any(t.endswith("*") and target.startswith(t[:-1]) for t in spec.targets):
            return False, f"target_not_allowed:{action}:{target}"
    params = step.get("params")
    if not isinstance(params, dict):
        return False, "params must be an object"
    extra = set(params.keys()) - set(spec.params.keys())
    if extra:
        return False, f"unknown_param_fields:{sorted(extra)}"
    missing = [k for k, p in spec.params.items() if p.required and k not in params]
    if missing:
        return False, f"missing_required_params:{missing}"
    errors = [
        msg for key, value in params.items()
        if (msg := spec.params[key].validate(key, value))
    ]
    if errors:
        return False, ";".join(errors)
    return True, "ok"


def risk_class_of(registry: PolicyRegistry, action: str) -> str:
    """C4. Unregistered actions classify as forbidden (fail-closed)."""
    spec = registry.get(action)
    return spec.risk if spec else "forbidden"


def check_plan_composition(registry: PolicyRegistry, steps: list[dict]) -> dict:
    """VAL-002: deterministic cross-step composition analysis.

    Returns {combination_blocks: [(a,b)], order_conflicts: [(first,then)]}.
    """
    actions_in_order = [str(s.get("action")) for s in
                        sorted(steps, key=lambda s: s.get("step_no", 0))]
    present = set(actions_in_order)
    combination_blocks = [
        (a, b) for a, b in registry.forbidden_combinations
        if a in present and b in present
    ]
    order_conflicts = []
    for first, then in registry.required_order:
        if first in present and then in present:
            if actions_in_order.index(then) < actions_in_order.index(first):
                order_conflicts.append((first, then))
    return {"combination_blocks": combination_blocks,
            "order_conflicts": order_conflicts}


def load_default_registry() -> PolicyRegistry:
    try:
        return load_registry()
    except (OSError, ValidationFailed):
        return PolicyRegistry({})
