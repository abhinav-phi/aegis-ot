"""Datasets, pipeline, telemetry, eval, audit, demo routers."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import audit_context, ok
from app.core.exceptions import ConflictError, ValidationFailed
from app.core.security import Principal, current_principal, require_admin, require_analyst
from app.db.models import (
    Dataset,
    DatasetRun,
    EvaluationRun,
    MetricRow,
    ModelVersion,
)
from app.db.session import get_db
from app.services import audit as audit_svc
from app.services.pipeline_service import (
    map_threats,
    preprocess_dataset,
    run_detection,
    train_detector,
)

router = APIRouter(tags=["data"])


# ---------------------------------------------------------------- datasets
@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db),
                  _a: Principal = Depends(require_admin)):
    rows = db.execute(select(Dataset)).scalars().all()
    return ok([{"id": str(d.id), "key": d.key, "sha256": d.sha256[:16],
                "rows": d.record_count, "primary": bool(d.primary),
                "sensors": len(d.sensor_columns)} for d in rows])


class IngestIn(BaseModel):
    source_path: str


@router.post("/datasets/ingest/{key}", status_code=202)
def ingest(key: str, payload: IngestIn | None = None, file: UploadFile | None = File(None),
           db: Session = Depends(get_db), request: Request = None,  # type: ignore[assignment]
           a: Principal = Depends(require_admin)):
    from pipeline.ingest.registry import ingest_dataset

    tmp: str
    if file is not None:
        tmp_dir = Path(".uploads")
        tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / f"{key}-{dt.datetime.now().timestamp():.0f}"
        tmp_path.write_bytes(file.file.read())
        tmp = str(tmp_path)
    elif payload is not None:
        tmp = payload.source_path
    else:
        raise ValidationFailed("source_required")
    ds = ingest_dataset(db, key=key, source_path=tmp, actor_id=a.user_id)
    return ok({"dataset_id": str(ds.id), "sha256": ds.sha256})


@router.post("/datasets/{dataset_id}/preprocess", status_code=202)
def preprocess(dataset_id: str, db: Session = Depends(get_db),
               request: Request = None,  # type: ignore[assignment]
               a: Principal = Depends(require_admin)):
    runs = preprocess_dataset(db, dataset_id=dataset_id, actor_id=a.user_id)
    return ok([{"run_id": str(r.id), "split": r.split_role, "status": r.status}
               for r in runs])


@router.post("/pipeline/train")
def train(payload: dict, db: Session = Depends(get_db),
          request: Request = None,  # type: ignore[assignment]
          a: Principal = Depends(require_admin)):
    validation_run_id = payload.get("validation_run_id") or payload.get("dataset_run_id")
    if not validation_run_id:
        raise ValidationFailed("validation_run_id_required")
    mv = train_detector(db, validation_run_id=validation_run_id,
                        family=payload.get("family", "iso_forest"),
                        actor_id=a.user_id, seed=int(payload.get("seed", 0)))
    return ok({"model_version_id": str(mv.id), "threshold": mv.threshold})


class DetectIn(BaseModel):
    dataset_run_id: str
    model_version_id: str


@router.post("/pipeline/run_detection", status_code=202)
def pipeline_run_detection(payload: DetectIn, db: Session = Depends(get_db),
                           request: Request = None,  # type: ignore[assignment]
                           a: Principal = Depends(require_admin)):
    result = run_detection(db, dataset_run_id=payload.dataset_run_id,
                           model_version_id=payload.model_version_id,
                           actor_id=a.user_id)
    return ok(result)


@router.post("/incidents/{incident_id}/threat_map")
def threat_map(incident_id: str, db: Session = Depends(get_db),
               p: Principal = Depends(require_analyst)):
    rows = map_threats(db, incident_id)
    return ok([{"technique_id": r.technique_id, "confidence": r.confidence}
               for r in rows])


@router.get("/telemetry/latest")
def telemetry_latest(db: Session = Depends(get_db),
                     _p: Principal = Depends(current_principal)):
    """Latest detections feed for the dashboard (1 s polling)."""
    rows = db.execute(select(Detection).order_by(Detection.window_start.desc())
                      .limit(50)).scalars().all()
    return ok([{"window_start": str(d.window_start), "score": round(d.score, 4),
                "is_anomaly": bool(d.is_anomaly)} for d in rows])


# ---------------------------------------------------------------- eval
eval_router = APIRouter(prefix="/eval", tags=["eval"])


class EvalRunIn(BaseModel):
    experiment_id: str
    config: dict = {}


@eval_router.post("/run", status_code=202)
def eval_run(payload: EvalRunIn, db: Session = Depends(get_db),
             a: Principal = Depends(require_admin)):
    from eval.experiments import run_exp08

    if payload.experiment_id != "EXP-08":
        raise ValidationFailed("experiment_not_available_via_api_use_cli")
    result = run_exp08(db, created_by=a.user_id)
    return ok(result)


@eval_router.get("/runs")
def eval_runs(db: Session = Depends(get_db), _a: Principal = Depends(require_admin)):
    rows = db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
                      .limit(100)).scalars().all()
    return ok([{"id": str(r.id), "experiment": r.experiment_id, "status": r.status,
                "created_at": str(r.created_at)} for r in rows])


@eval_router.get("/metrics")
def eval_metrics(exp: str | None = None, db: Session = Depends(get_db),
                 _a: Principal = Depends(require_admin)):
    q = select(MetricRow).order_by(MetricRow.created_at.desc()).limit(500)
    if exp:
        runs = db.execute(select(EvaluationRun).where(
            EvaluationRun.experiment_id == exp)).scalars().all()
        ids = [r.id for r in runs]
        if not ids:
            return ok([])
        q = q.where(MetricRow.evaluation_run_id.in_(ids))
    rows = db.execute(q).scalars().all()
    return ok([{"metric": m.metric_name, "value": m.value, "source": m.source,
                "run": str(m.evaluation_run_id or "")} for m in rows])


# ---------------------------------------------------------------- audit
audit_router = APIRouter(prefix="/audit", tags=["audit"])


@audit_router.get("")
def query_audit(actor: str | None = None, action: str | None = None,
                db: Session = Depends(get_db), _a: Principal = Depends(require_admin)):
    from app.db.models import AuditLog

    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(300)
    if action:
        q = q.where(AuditLog.action == action)
    rows = db.execute(q).scalars().all()
    if actor:
        rows = [r for r in rows if str(r.actor_id or "") == actor]
    return ok([{"action": r.action, "entity": f"{r.entity_type}:{r.entity_id}",
                "actor": str(r.actor_id or ""), "at": str(r.created_at)}
               for r in rows])


@audit_router.get("/export.csv")
def export_csv(db: Session = Depends(get_db), _a: Principal = Depends(require_admin)):
    from fastapi.responses import Response

    from app.services.audit import export_csv

    csv_text = export_csv(db)
    audit_svc.audit(db, actor_id=None, action="audit.exported",
                    entity_type="audit_logs")
    return Response(content=csv_text, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=audit.csv"})


# ---------------------------------------------------------------- demo
demo_router = APIRouter(prefix="/demo", tags=["demo"])


@demo_router.post("/attack", status_code=202)
def demo_attack(db: Session = Depends(get_db), request: Request = None,  # type: ignore[assignment]
                a: Principal = Depends(require_admin)):
    from app.services.demo_service import run_demo

    result = run_demo(db, created_by=a.user_id,
                      ip=audit_context(request)["ip"] if request else None)
    return ok(result)


@demo_router.get("/attack/latest")
def demo_latest(db: Session = Depends(get_db),
                _p: Principal = Depends(current_principal)):
    row = db.execute(select(EvaluationRun)
                     .where(EvaluationRun.experiment_id == "DEMO-ATTACK")
                     .order_by(EvaluationRun.created_at.desc())
                     .limit(1)).scalar_one_or_none()
    if row is None:
        raise ConflictError("fixture_not_provisioned")
    metrics = db.execute(select(MetricRow)
                         .where(MetricRow.evaluation_run_id == row.id)).scalars().all()
    return ok({m.metric_name: m.value for m in metrics})
