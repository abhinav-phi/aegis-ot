"""Validator engine: orchestrates C1–C5 per step + plan-level composition
(VAL-002) + evidence freshness (VAL-002b), producing check rows and the
lattice verdict via the single pure function in verdict.py.

Deterministic inputs: EvidenceIndex (entries may carry `observed_at` epoch
seconds for freshness), invariant outcomes, prior C5 categories, registry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.validator import consistency as c5mod
from pipeline.validator import pattern as c3mod
from pipeline.validator import policy as c24mod
from pipeline.validator import provenance as c1mod
from pipeline.validator.verdict import StepChecks, plan_verdict


class EvidenceIndex(dict[str, dict[str, Any]]):
    """id -> {tier, source, fields, text, observed_at?}."""


@dataclass
class ValidationOutcome:
    verdict: str
    checks: list[dict] = field(default_factory=list)
    risk_classes: list[dict] = field(default_factory=list)
    step_details: list[dict] = field(default_factory=list)
    c5_category: str | None = None


def validate_plan(
    steps: list[dict],
    index: EvidenceIndex,
    *,
    registry: c24mod.PolicyRegistry,
    pattern_filter: c3mod.PatternFilter | None = None,
    failed_invariants: list[str] | None = None,
    prior_c5_categories: list[str | None] | None = None,
    now_ts: float | None = None,
) -> ValidationOutcome:
    pf = pattern_filter or c3mod.PatternFilter()
    failed_invariants = failed_invariants or []
    prior_c5_categories = prior_c5_categories or []

    checks: list[CheckRow] = []
    step_checks: list[StepChecks] = []
    current_c5_category: str | None = None

    # ---- Plan-level composition (VAL-002): recorded under C2/C5 -----------
    composition = c24mod.check_plan_composition(registry, steps)
    for a, b in composition["combination_blocks"]:
        checks.append(CheckRow("C2", -1, "fail",
                               f"policy_forbidden_combination:{a}+{b}"))
    for first, then in composition["order_conflicts"]:
        checks.append(CheckRow("C5", -1, "flag",
                               f"ordering_conflict:{then}_before_{first}"))
        if current_c5_category is None:
            current_c5_category = "ordering_conflict"

    # ---- Per-step checks ----------------------------------------------------
    ordered = sorted(steps, key=lambda s: s.get("step_no", 0))
    for idx, step in enumerate(ordered):
        no = int(step.get("step_no", 0))
        action = str(step.get("action", ""))

        ok, detail = c24mod.check_allowlist(registry, step)
        # Combination blocks attach to the LAST occurrence of the offending pair.
        combo_fail = any(a == action and not any(
            s.get("action") == a for s in ordered[idx + 1:])
            for a, _ in composition["combination_blocks"])
        if combo_fail:
            ok = False
            detail = f"plan_forbidden_combination:{action}"
        checks.append(CheckRow("C2", no, "pass" if ok else "fail", detail))
        risk = c24mod.risk_class_of(registry, action)
        checks.append(CheckRow("C4", no, risk, f"risk={risk}"))

        prov = c1mod.check_provenance(step, index)
        whitelisted_read = (
            (spec := registry.get(action)) is not None
            and spec.citation_free_read and risk == "read")
        if whitelisted_read and prov.status == "flag_missing_citations":
            # Whitelisted read actions are explicitly permitted without
            # citations (VAL-001: whitelist is a check INPUT, not ordering).
            from pipeline.validator.provenance import ProvenanceResult

            prov = ProvenanceResult("pass", [], "whitelisted_read_no_citations")
        checks.append(CheckRow("C1", no, prov.status, prov.detail))

        rendered = " ".join([
            action, str(step.get("target", "")),
            str(sorted((step.get("params") or {}).items())),
            " ".join(str(c) for c in (step.get("citations") or [])),
        ])
        clean, marker = pf.scan(rendered)
        c3_status = "pass" if clean else ("hard" if risk in ("write", "control") else "flag")
        checks.append(CheckRow("C3", no, c3_status,
                               f"marker={marker}" if marker else "clean"))

        cons = c5mod.check_consistency(step, index, failed_invariants)
        stale = False
        if registry.evidence_freshness_s and now_ts is not None:
            for cid in step.get("citations") or []:
                ev = index.get(cid)
                obs = ev.get("observed_at") if ev else None
                if ev and ev.get("tier") == "trusted" and obs and \
                        now_ts - float(obs) > registry.evidence_freshness_s:
                    stale = True
                    cons = c5mod.ConsistencyResult(
                        "flag", "stale_evidence",
                        f"stale_evidence:{cid}", cons.mismatches)
                    break
        category = cons.category or ("stale_evidence" if stale else None)
        if category and current_c5_category is None:
            current_c5_category = category
        persistent = c5mod.is_persistent(category, prior_c5_categories)
        checks.append(CheckRow(
            "C5", no,
            "pass" if (cons.status == "pass" and not stale)
            else ("escalate" if persistent else "flag"),
            ";".join(filter(None, [cons.detail, "stale" if stale else ""]))))

        step_checks.append(StepChecks(
            step_no=no, action=action, c1=prov.status,
            c2="pass" if ok else "fail", c3=c3_status, risk_class=risk,
            c5=("escalate" if persistent else
                ("flag" if (cons.status != "pass" or stale) else "pass")),
            citations=list(step.get("citations") or []),
            citation_free_read=whitelisted_read,
        ))

    verdict, details = plan_verdict(step_checks,
                                    persistent_c5=bool(prior_c5_categories))
    return ValidationOutcome(
        verdict=verdict,
        checks=[c.__dict__ for c in checks],
        risk_classes=[{"step_no": sc.step_no, "risk": sc.risk_class}
                      for sc in step_checks],
        step_details=details,
        c5_category=current_c5_category,
    )


@dataclass
class CheckRow:
    check: str          # C1..C5
    step_no: int
    status: str         # pass | fail | flag | hard | <risk>
    detail: str = ""
    deterministic: bool = True
