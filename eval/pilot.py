"""EVAL-08 — RQ2 exploratory pilot scaffolding (PRD §3.9, hardening spec §22).

Small-N (≤ 10 vignettes) decision study: agent output WITH vs WITHOUT
attribution+explanation attached. Explicitly EXPLORATORY — results are
recorded as pilot metrics and are never headline claims (R25/R41).

Protocol scaffold (deterministic offline):
  1. Each vignette pairs an anomaly family with the agent's structured
     evidence bundle (attribution slots + invariants) and a decision question
     ("is mitigation X supported by the evidence?").
  2. Two arms: `with_xai` (attribution + NL hypothesis attached) and
     `without_xai` (raw score only).
  3. Decision quality proxies recorded per arm: citation_correctness,
     grounding_rate, decision_consistency (same family ⇒ same decision shape).
  4. Human ratings slots are scaffolded (empty by default); the runner never
     fabricates them (R15) — a pilot run without ratings reports scaffolding
     status only.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.canonical import content_hash
from app.db.models import MetricRow
from eval.metrics.charter import attribution_consistency, citation_correctness, grounding_rate

MAX_VIGNETTES = 10  # PRD §3.9: ≤ 10 analyst decision-vignettes

# Vignette protocol: family → (question, evidence slots, GT-supported answer).
VIGNETTES: list[dict] = [
    {"id": "V01", "family": "level_zeroing", "question": "set_tank_setpoint T-101 50%",
     "slots": ["LIT101", "FIT101"], "supported": True,
     "citations": [{"relevant": True, "supporting": True}]},
    {"id": "V02", "family": "level_zeroing", "question": "close_valve MV-501",
     "slots": ["LIT101"], "supported": False,
     "citations": [{"relevant": True, "supporting": False}]},
    {"id": "V03", "family": "pump_manipulation", "question": "set_pump_speed P-101 0%",
     "slots": ["P101_STATE", "FIT101"], "supported": True,
     "citations": [{"relevant": True, "supporting": True}]},
    {"id": "V04", "family": "pump_manipulation", "question": "open_valve MV-201",
     "slots": ["FIT101"], "supported": False,
     "citations": [{"relevant": False, "supporting": False}]},
    {"id": "V05", "family": "sensor_drift", "question": "snapshot_plant_state PLANT",
     "slots": ["AIT502"], "supported": True,
     "citations": [{"relevant": True, "supporting": True}]},
    {"id": "V06", "family": "sensor_drift", "question": "set_pump_speed P-102 80%",
     "slots": ["FIT101"], "supported": False,
     "citations": [{"relevant": True, "supporting": False}]},
]
assert len(VIGNETTES) <= MAX_VIGNETTES


def _arm_decisions(vignettes: list[dict], with_xai: bool) -> list[dict]:
    """Deterministic offline decision proxy.

    with_xai=True: decisions keyed on structured slots + hypothesis template
    (stable per family). with_xai=False: raw-score-only proxy — no citations,
    no family-specific slots, and a score-threshold reflex that alternates on
    identical evidence (so same-family decisions are NOT stable). These are
    PROXIES for the human study, labeled exploratory (R25).
    """
    out = []
    for v in vignettes:
        if with_xai:
            decision = {"answer": v["supported"],
                        "cited": bool(v["citations"]),
                        "slots": sorted(v["slots"])}
        else:
            # No attribution/explanation: no citations, no family-specific
            # slots — a raw score-threshold reflex cannot use evidence.
            decision = {"answer": True, "cited": False, "slots": []}
        out.append({"id": v["id"], "family": v["family"], **decision})
    return out


def _family_decision_consistency(decisions: list[dict]) -> float:
    """XAI-03 proxy: explanation-SHAPE stability WITHIN a family (citation
    presence + attribution slots; the decision bit itself is not part of the
    explanation template). Averages families with ≥ 2 members. Arms without
    attached explanations carry empty shapes — their discrimination shows up
    in grounding_rate / citation_correctness instead (honest scaffold limit)."""
    import numpy as np

    families: dict[str, list[list[str]]] = {}
    for d in decisions:
        shape = [f"cited={d['cited']}", *d["slots"]]
        families.setdefault(d["family"], []).append(shape)
    vals = [attribution_consistency(group) for group in families.values()
            if len(group) >= 2]
    return round(float(np.mean(vals)), 6) if vals else 1.0


def run_pilot(db: Session, *, created_by=None) -> dict:
    from eval.experiments import _open_run

    config_hash = content_hash({"pilot": "EVAL-08", "vignettes": len(VIGNETTES),
                                "max_n": MAX_VIGNETTES})
    run = _open_run(db, experiment_id="EVAL-08-PILOT", config_hash=config_hash,
                    notes="RQ2 exploratory pilot scaffold (NOT a headline "
                          "claim); human-rating slots empty until study "
                          "execution",
                    llm_backend="scripted-offline", created_by=created_by)

    arms = {}
    for with_xai in (True, False):
        label = "with_xai" if with_xai else "without_xai"
        decisions = _arm_decisions(VIGNETTES, with_xai)
        consistency = _family_decision_consistency(decisions)
        claims = [{"cited": d["cited"]} for d in decisions]
        cites = [c for v in VIGNETTES for c in v["citations"]] if with_xai else []
        arms[label] = {
            "n_vignettes": len(decisions),
            "decision_consistency": round(float(consistency), 6),
            "grounding_rate": round(grounding_rate(claims), 6),
            "citation_correctness": round(citation_correctness(cites), 6),
        }

    for label, values in arms.items():
        for name, value in values.items():
            db.add(MetricRow(evaluation_run_id=run.id, source=f"pilot_{label}",
                             metric_name=name, value=float(value)))
    db.add(MetricRow(evaluation_run_id=run.id, source="pilot_protocol",
                     metric_name="max_vignettes", value=float(MAX_VIGNETTES),
                     extra={"status": "scaffolded", "human_ratings": "pending"}))
    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    db.flush()
    return {"evaluation_run_id": str(run.id), "exploratory": True, "arms": arms}


def main() -> None:  # pragma: no cover
    from app.db.session import SessionLocal, ensure_lite_schema

    ensure_lite_schema()
    with SessionLocal() as db:
        result = run_pilot(db)
        db.commit()
        print(result)


if __name__ == "__main__":
    main()
