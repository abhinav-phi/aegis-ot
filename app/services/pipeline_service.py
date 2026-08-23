"""Pipeline orchestration service: preprocess → train → detect → explain →
incident → tintel, with run status tracking + integrity verification."""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical import content_hash
from app.db.models import (
    Anomaly,
    AnomalyExplanation,
    Dataset,
    DatasetRun,
    Detection,
    Incident,
    ModelVersion,
    ThreatMapping,
)
from app.services.audit import audit
from app.services.incident_service import create_incidents_from_detections
from pipeline.detect.scoring import classify, contributions, threshold_from_validation
from pipeline.ingest.registry import read_registered_csv
from pipeline.preprocess.preprocess import Scaler, clean, temporal_split_bounds
from pipeline.preprocess.windower import make_windows, window_starts
from pipeline.storage import get_store, sha256_bytes, verify_hash


def _load_features_config() -> dict:
    with open("configs/features.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def preprocess_dataset(db: Session, *, dataset_id, actor_id=None) -> list[DatasetRun]:
    cfg = _load_features_config()
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise ValueError("dataset_not_found")
    store = get_store()
    df = read_registered_csv(store, ds)

    runs: list[DatasetRun] = []
    bounds_all = temporal_split_bounds(len(df), cfg["splits"])
    scaler: Scaler | None = None

    for split_role in ("train", "validation", "test"):
        start, end = bounds_all[split_role]
        run_cfg_hash = content_hash({"dataset": str(ds.id), "split": split_role,
                                     "features": cfg})
        run = DatasetRun(
            dataset_id=ds.id, run_name=f"{ds.key}-{split_role}",
            config_hash=run_cfg_hash, split_role=split_role,
            minio_root=f"aegis-raw/{ds.key}/features/{split_role}/",
            status="running",
        )
        db.add(run)
        db.flush()
        try:
            slice_df = df.iloc[start:end].copy()
            cleaned = clean(slice_df, ds.sensor_columns)
            if scaler is None:
                scaler = Scaler.fit(cleaned, ds.sensor_columns)  # TRAIN ONLY (R-ML-03)
            matrix = scaler.transform(cleaned, ds.sensor_columns)
            W, stride = cfg["window"]["W"], cfg["window"]["stride"]
            windows = make_windows(matrix, W, stride, (0, len(cleaned)))
            feat_key = f"{ds.key}/features/{split_role}/windows.npy"
            stats_key = f"{ds.key}/features/{split_role}/scaler.json"
            store.put(feat_key, _pack(windows))
            store.put(stats_key, json.dumps(scaler.to_dict()).encode())
            run.feature_manifest = {
                "blocks": [{"key": feat_key, "n_windows": len(windows),
                            "W": W, "stride": stride,
                            "sensor_order": ds.sensor_columns,
                            "row_range": [start, end]}],
                "stats_key": stats_key,
                "sha256": sha256_bytes(_pack(windows)),
            }
            run.rows = len(cleaned)
            run.normalization_stats = scaler.to_dict()
            run.verified_hashes = {"features_sha256": run.feature_manifest["sha256"],
                                   "source_dataset_sha256": ds.sha256}
            run.status = "completed"
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)[:500]
            raise
        finally:
            runs.append(run)
    audit(db, actor_id=actor_id, action="pipeline.preprocessed",
          entity_type="datasets", entity_id=ds.id, after={"runs": len(runs)})
    return runs


def _pack(arr: np.ndarray) -> bytes:
    meta = json.dumps({"dtype": "float64", "shape": list(arr.shape)}).encode()
    return len(meta).to_bytes(4, "big") + meta + arr.tobytes()


def _unpack(raw: bytes) -> np.ndarray:
    n = int.from_bytes(raw[:4], "big")
    meta = json.loads(raw[4:4 + n])
    return np.frombuffer(raw[4 + n:], dtype=np.float64).reshape(meta["shape"])


def load_feature_blocks(store, run: DatasetRun):
    block = (run.feature_manifest.get("blocks") or [{}])[0]
    arr = _unpack(store.get(block["key"]))
    starts = window_starts((0, block["row_range"][1] - block["row_range"][0]),
                           block["W"], block["stride"])
    ts0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    timestamps = [ts0 + dt.timedelta(seconds=i) for i in starts]
    return arr, timestamps, block


def train_detector(db: Session, *, validation_run_id, family: str,
                   actor_id=None, seed: int = 0) -> ModelVersion:
    cfg = _load_features_config()
    store = get_store()
    val_run = db.get(DatasetRun, validation_run_id)
    if val_run is None:
        raise ValueError("dataset_run_not_found")
    ds = db.get(Dataset, val_run.dataset_id)
    val_windows, _, _ = load_feature_blocks(store, val_run)
    gt_labels = _labels_for(ds, val_run, len(val_windows))

    from pipeline.detect.iso_forest import IsoForestDetector

    det = IsoForestDetector(stats=cfg["per_window_stats"], seed=seed)
    normal_mask = ~gt_labels.astype(bool)
    det.fit(val_windows[normal_mask] if normal_mask.any() else val_windows)
    scores = det.score(val_windows)
    tau = threshold_from_validation(scores, normal_mask, cfg["threshold_quantile"])
    artifact = det.save_bytes()
    key = f"artifacts/{family}_{seed}.bin"
    store.put(key, artifact, bucket="aegis-artifacts")
    mv = ModelVersion(
        name=f"{family}_synthetic_s{seed}", family=family,
        dataset_run_id=val_run.id, config_hash=content_hash(cfg),
        checkpoint_path=key, artifact_sha256=sha256_bytes(artifact),
        threshold=tau, metrics_summary={"val_score_mean": float(scores.mean())},
        created_by=actor_id,
    )
    db.add(mv)
    db.flush()
    # R20: every training run is mirrored to MLflow (fail-open telemetry).
    from app.core.mlflow_bridge import log_training_run

    mlflow_ok = log_training_run(
        run_name=mv.name,
        params={"family": family, "seed": seed, "dataset_run": str(val_run.id),
                "config_hash": mv.config_hash},
        metrics={"threshold_tau": float(tau),
                 "val_score_mean": float(scores.mean()),
                 "val_windows": len(val_windows)},
        artifact_bytes=artifact, artifact_name="checkpoint.bin",
    )
    mv.metrics_summary = {**mv.metrics_summary, "mlflow_logged": mlflow_ok}
    audit(db, actor_id=actor_id, action="model.registered",
          entity_type="model_versions", entity_id=mv.id,
          after={"tau": tau, "artifact_sha256": mv.artifact_sha256})
    return mv


def run_detection(db: Session, *, dataset_run_id, model_version_id,
                  actor_id=None) -> dict:
    cfg = _load_features_config()
    store = get_store()
    run = db.get(DatasetRun, dataset_run_id)
    ds = db.get(Dataset, run.dataset_id)
    mv = db.get(ModelVersion, model_version_id)
    verify_hash(store, mv.checkpoint_path, mv.artifact_sha256,
                bucket="aegis-artifacts")  # INV-016

    windows, timestamps, _block = load_feature_blocks(store, run)
    from pipeline.detect.iso_forest import IsoForestDetector

    detector = IsoForestDetector.load_bytes(store.get(mv.checkpoint_path,
                                                      bucket="aegis-artifacts"))
    scores = detector.score(windows)
    labels = classify(scores, mv.threshold)
    gt = _labels_for(ds, run, len(windows))
    inserted, anomalies = 0, 0
    eps = cfg["attribution_epsilon"]
    floor = cfg["low_confidence_residual_floor"]
    for i, ts in enumerate(timestamps):
        existing = db.execute(
            select(Detection).where(
                Detection.dataset_run_id == dataset_run_id,
                Detection.model_version_id == model_version_id,
                Detection.window_start == ts)
        ).scalar_one_or_none()
        if existing is not None:  # CHG-DB-04 upsert semantics
            existing.score = float(scores[i])
            existing.is_anomaly = bool(labels[i])
            existing.threshold = float(mv.threshold)
            existing.ground_truth = bool(gt[i]) if i < len(gt) else None
            det_row = existing
        else:
            det_row = Detection(
                dataset_run_id=dataset_run_id, model_version_id=model_version_id,
                window_start=ts, score=float(scores[i]), is_anomaly=bool(labels[i]),
                threshold=float(mv.threshold),
                ground_truth=bool(gt[i]) if i < len(gt) else None,
            )
            db.add(det_row)
            db.flush()
            inserted += 1
        if labels[i]:
            contrib = contributions(
                np.abs(np.tile(scores[i], len(ds.sensor_columns))).reshape(1, -1),
                ds.sensor_columns, epsilon=eps, low_confidence_floor=floor)[0]
            anomaly = Anomaly(detection_id=det_row.id,
                              severity=_severity(float(scores[i])),
                              top_sensors=contrib["top_sensors"],
                              low_confidence=contrib["low_confidence"])
            db.add(anomaly)
            db.flush()
            db.add(AnomalyExplanation(
                anomaly_id=anomaly.id,
                hypothesis=(f"HYPOTHESIS (not a verdict): anomalous window at {ts} "
                            f"score {scores[i]:.3f} > τ {mv.threshold:.3f}; dominant "
                            f"sensors {', '.join(s['sensor'] for s in contrib['top_sensors'])}."),
                evidence=[], invariant_checks=[]))
            anomalies += 1
    incidents = create_incidents_from_detections(db, dataset_run_id=dataset_run_id,
                                                 actor_id=actor_id)
    audit(db, actor_id=actor_id, action="pipeline.detected",
          entity_type="dataset_runs", entity_id=dataset_run_id,
          after={"detections": inserted, "anomalies": anomalies,
                 "incidents": len(incidents)})
    return {"detections_written": inserted, "anomalies": anomalies,
            "incidents_created": [str(i.id) for i in incidents]}


def map_threats(db: Session, incident_id) -> list[ThreatMapping]:
    from pipeline.tintel.mitre_ics import map_incident

    inc = db.get(Incident, incident_id)
    if inc is None:
        raise ValueError("incident_not_found")
    anomalies = db.execute(select(Anomaly).where(Anomaly.incident_id == incident_id)).scalars().all()
    top: list[str] = []
    failed: set[str] = set()
    for a in anomalies:
        top += [s["sensor"] for s in (a.top_sensors or [])]
        exp = db.execute(select(AnomalyExplanation).where(
            AnomalyExplanation.anomaly_id == a.id)).scalar_one_or_none()
        for c in (exp.invariant_checks if exp else []) or []:
            if not c.get("pass", True):
                failed.add(c.get("rule_id"))
    rows: list[ThreatMapping] = []
    for m in map_incident(top_sensors=top[:10], failed_invariants=sorted(failed)):
        exists = db.execute(select(ThreatMapping).where(
            ThreatMapping.incident_id == incident_id,
            ThreatMapping.technique_id == m["technique_id"])).scalar_one_or_none()
        if exists:
            continue
        row = ThreatMapping(incident_id=incident_id,
                            technique_id=m["technique_id"],
                            confidence=min(max(m["confidence"], 0.0), 1.0),
                            basis=m["basis"])
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _severity(score: float) -> str:
    with open("configs/invariants.yaml", encoding="utf-8") as f:
        inv = yaml.safe_load(f)
    sev = "low"
    for name, floor in inv.get("severity_score_map", {}).items():
        if score >= floor:
            sev = name
    return sev


def _labels_for(ds: Dataset, run: DatasetRun, n_windows: int) -> np.ndarray:
    try:
        df = read_registered_csv(get_store(), ds)
    except Exception:
        return np.zeros(n_windows, dtype=bool)
    block = (run.feature_manifest.get("blocks") or [{}])[0]
    lo, hi = block.get("row_range", [0, len(df)])
    labels = df["label"].to_numpy()[lo:hi]
    W, stride = block.get("W", 60), block.get("stride", 1)
    idx = list(range(0, max(0, hi - lo) - W + 1, stride))[:n_windows]
    out = np.zeros(n_windows, dtype=bool)
    for j, s in enumerate(idx):
        seg = labels[s:s + W]
        out[j] = bool(len(seg) and seg.max() > 0)
    return out
