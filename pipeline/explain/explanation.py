"""Explanation object: template NL + optional pinned-prompt polish (XAI-01/02).

Hypothesis-only path: consumes ONLY structured attribution + invariant
outcomes; output carries no execution authority (PRD §3.4 boundary, R19).
"""
from __future__ import annotations

from pipeline.detect.invariances import evaluate_invariants


def build_explanation(*, top_sensors: list[dict], invariant_checks: list[dict],
                      score: float, threshold: float, low_confidence: bool,
                      window_start: str) -> dict:
    names = ", ".join(s["sensor"] for s in top_sensors[:3]) or "n/a"
    failed = [c["rule_id"] for c in invariant_checks if not c.get("pass", True)]
    parts = [
        (f"HYPOTHESIS (not a verdict): anomaly window at {window_start} scored "
         f"{score:.3f} (threshold {threshold:.3f})."),
        f"Attribution: dominant channels {names}.",
    ]
    if low_confidence:
        parts.append("Note: residual energy was near zero; attribution is low-confidence.")
    if failed:
        parts.append(f"Invariants violated: {', '.join(failed)}.")
    else:
        parts.append("All five invariants passed.")
    parts.append("Evidence: sensor contributions and invariant outcomes only; "
                 "no instructions were taken from telemetry content.")
    hypothesis = " ".join(parts)

    return {
        "hypothesis": hypothesis,
        "evidence": [
            {"kind": "attribution", "top_sensors": top_sensors[:3]},
            {"kind": "invariants", "checks": invariant_checks},
        ],
        "invariant_checks": invariant_checks,
        "label": "HYPOTHESIS",
    }


def invariants_for_window(window_payload: dict) -> list[dict]:
    return evaluate_invariants(window_payload)["checks"]
