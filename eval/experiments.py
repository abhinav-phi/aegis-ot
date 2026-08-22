"""Experiment runner (EXP-01..09, EVAL-02, ROB-01/02).

EXP-08/09 execute against the service layer; detector experiments require the
licensed dataset (or synthetic fixture) and are executed via the same entry
point once data is pinned. No fabricated results: every metric written to
`metrics` comes from charter functions over measured outputs.
"""
from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.db.models import EvaluationRun, MetricRow
from eval.attack_suite.runner import run_attack_suite
from eval.bypass_battery import run_bypass_battery
from eval.metrics.charter import fpr, pa_k, pr_auc, precision_recall_f1


def run_exp08(db: Session, created_by=None) -> dict:
    return run_attack_suite(db, created_by=created_by)


def run_exp09(db: Session, seed: dict, created_by=None) -> dict:
    """Gate-bypass battery. `seed` ids come from a prepared scenario."""
    from app.core.canonical import content_hash

    run = EvaluationRun(experiment_id="EXP-09",
                        config_hash=content_hash({"battery": "v1"}),
                        status="running", created_by=created_by,
                        notes="approval/gate bypass battery")
    db.add(run)
    db.flush()
    rows = run_bypass_battery(db, seed)
    rejected = sum(1 for r in rows if r["rejected"])
    db.add(MetricRow(evaluation_run_id=run.id, source="safety",
                     metric_name="bypass_attempts_rejected",
                     value=1.0 if rejected == len(rows) else 0.0,
                     extra={"rejected": rejected, "total": len(rows)}))
    run.status = "completed" if rejected == len(rows) else "failed"
    db.flush()
    return {"evaluation_run_id": str(run.id), "attempts": rows,
            "all_rejected": rejected == len(rows)}


def run_exp01(db: Session, dataset_run_id, created_by=None) -> dict:
    """Baseline detector metrics on the synthetic fixture (or pinned dataset)."""
    from app.services.pipeline_service import run_detection, train_detector
    import numpy as np
    from app.db.models import Detection

    mv = train_detector(db, validation_run_id=dataset_run_id, family="iso_forest",
                        actor_id=created_by)
    run_detection(db, dataset_run_id=dataset_run_id, model_version_id=mv.id,
                  actor_id=created_by)
    rows = db.query(Detection).filter(Detection.model_version_id == mv.id).all()
    y = np.array([bool(r.ground_truth) for r in rows])
    s = np.array([r.score for r in rows])
    pred = np.array([bool(r.is_anomaly) for r in rows])
    tp = int((pred & y).sum()); fp = int((pred & ~y).sum())
    fn = int((~pred & y).sum()); tn = int((~pred & ~y).sum())
    prf = precision_recall_f1(tp, fp, fn)
    metrics = {**prf, "fpr": fpr(fp, tn), "pr_auc": pr_auc(s, y),
               "pa_k_50": pa_k(y, pred, 50.0)}
    run = EvaluationRun(experiment_id="EXP-01",
                        config_hash=mv.config_hash, status="completed",
                        model_version_ids=[str(mv.id)],
                        dataset_run_ids=[str(dataset_run_id)],
                        created_by=created_by, completed_at=mv.created_at)
    db.add(run)
    db.flush()
    for k, v in metrics.items():
        db.add(MetricRow(evaluation_run_id=run.id, source="detector",
                         metric_name=k, value=float(v)))
    return {"evaluation_run_id": str(run.id), **metrics}


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="EXP-08")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        if args.exp == "EXP-08" or args.all:
            print(run_exp08(db))
        db.commit()


if __name__ == "__main__":
    main()
