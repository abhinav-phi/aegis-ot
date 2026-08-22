"""The single authoritative, PURE verdict function (VAL-001 / §17 contract).

Not an ordering-sensitive procedure: every rule below is evaluated
unconditionally against the step's check outcomes; the final verdict is the
maximum-severity triggered outcome (lattice: block > escalate >
require_approval > allow). Reasons from ALL rules at the winning severity are
reported. Every API/service path must use THIS implementation.

Rule table (each row: condition -> severity):
  R1  exception flag                      -> require_approval ("check_exception")
  R2  risk_class == forbidden             -> block
  R3  c2 == fail                          -> block        (grammar/policy violation)
  R4  c3 == hard and risk in {write,control} -> block
  R5  c1 == block_hostile_only            -> block
  R6  c5 == escalate or (persistent and c5==flag) -> escalate
  R7  flags: c1 in {flag_missing_citations, flag_public_only, flag_hostile},
         c3 == flag, c5 == flag            -> require_approval
  R8  risk in {write, control}            -> require_approval   (INV-004)
  R9  no citations AND not whitelisted    -> require_approval   (RAG-001 floor)
  R10 otherwise                           -> allow

`citation_free_read` is an INPUT to this function (whether the action is on
the whitelisted read set) — never a sequencing exception.
"""
from __future__ import annotations

from dataclasses import dataclass

SEVERITY = {"allow": 0, "require_approval": 1, "escalate": 2, "block": 3}


@dataclass(frozen=True)
class StepChecks:
    step_no: int
    action: str
    c1: str          # pass | flag_missing_citations | flag_public_only | flag_hostile | block_hostile_only
    c2: str          # pass | fail
    c3: str          # pass | flag | hard
    risk_class: str  # read | write | control | forbidden
    c5: str          # pass | flag | escalate
    citations: list[str]
    exception: bool = False
    citation_free_read: bool = False


@dataclass(frozen=True)
class StepVerdict:
    verdict: str
    reasons: tuple[str, ...]


def _rules(sc: StepChecks, persistent_c5: bool) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if sc.exception:
        out.append(("require_approval", "check_exception_fail_closed"))
    if sc.risk_class == "forbidden":
        out.append(("block", "risk_class_forbidden"))
    if sc.c2 == "fail":
        out.append(("block", "allowlist_violation"))
    if sc.c3 == "hard" and sc.risk_class in ("write", "control"):
        out.append(("block", "injection_marker_write_control"))
    if sc.c1 == "block_hostile_only":
        out.append(("block", "hostile_sole_support"))
    if sc.c5 == "escalate" or (persistent_c5 and sc.c5 == "flag"):
        out.append(("escalate", "persistent_c5_inconsistency"))

    # Flag family (RAG-001: public-only on gated classes gets its own reason).
    if sc.c1 in ("flag_missing_citations", "flag_public_only", "flag_hostile"):
        if sc.risk_class in ("write", "control") and sc.c1 == "flag_public_only":
            out.append(("require_approval", "untrusted_provenance_public_only"))
        else:
            out.append(("require_approval", f"c1:{sc.c1}"))
    if sc.c3 == "flag":
        out.append(("require_approval", "c3:suspicious_pattern"))
    if sc.c5 == "flag" and not persistent_c5:
        out.append(("require_approval", "c5:inconsistency"))

    if sc.risk_class in ("write", "control"):
        out.append(("require_approval", f"approval_required:{sc.risk_class}"))
    if not sc.citations and not sc.citation_free_read:
        out.append(("require_approval", "no_trusted_citation"))
    return out


def step_verdict(sc: StepChecks, *, persistent_c5: bool = False) -> StepVerdict:
    triggered = _rules(sc, persistent_c5)
    if not triggered:
        return StepVerdict("allow", ())
    top = max(SEVERITY[v] for v, _ in triggered)
    winning = [v for v in triggered if SEVERITY[v[0]] == top]
    verdict = winning[0][0]
    reasons = tuple(dict.fromkeys(r for _, r in winning))
    return StepVerdict(verdict, reasons)


def plan_verdict(
    steps: list[StepChecks],
    *,
    exceptions: bool = False,
    persistent_c5: bool = False,
) -> tuple[str, list[dict]]:
    """Plan verdict = lattice-max over steps. Deterministic, golden-testable."""
    details: list[dict] = []
    worst = "allow"
    for sc0 in steps:
        sc = sc0
        if exceptions and not sc.exception:
            sc = StepChecks(**{**sc.__dict__, "exception": True})
        v = step_verdict(sc, persistent_c5=persistent_c5 and sc.c5 in ("flag", "escalate"))
        details.append({"step_no": sc.step_no, "action": sc.action,
                        "verdict": v.verdict, "reasons": list(v.reasons)})
        if SEVERITY[v.verdict] > SEVERITY[worst]:
            worst = v.verdict
    if not steps:
        worst = "escalate"  # empty plan is never safe to auto-execute
    return worst, details
