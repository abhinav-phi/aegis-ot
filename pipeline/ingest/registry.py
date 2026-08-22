"""Dataset ingestion + registry (DATA-01/02/05/06, R17, R21).

Licensed sources are interface-only: the operator supplies a local file path
(license-gated download is a documented manual step — DEC-016). Hash-pinned,
idempotent-by-hash; conflicting hash for a pinned key ⇒ conflict.
"""
from __future__ import annotations

import csv
import io
import uuid

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationFailed
from app.db.models import Dataset, DatasetRun
from pipeline.storage import get_store, sha256_bytes, validate_key

DATASET_KEYS = ("swat", "wustl_iiot2021", "wadi", "synthetic")


def ingest_dataset(db: Session, *, key: str, source_path: str,
                   display_name: str | None = None, actor_id=None) -> Dataset:
    if key not in DATASET_KEYS:
        raise ValidationFailed(f"unknown_dataset_key:{key}")
    try:
        raw = open(source_path, "rb").read()
    except OSError as e:
        raise ValidationFailed(f"source_unreadable:{e}") from e

    sha = sha256_bytes(raw)
    existing = db.execute(select(Dataset).where(Dataset.key == key)).scalar_one_or_none()
    if existing is not None:
        if existing.sha256 == sha:
            return existing  # idempotent by hash (CONC-003)
        raise ConflictError(f"dataset_hash_conflict:{key}")

    df = _read_table(raw, source_path)
    if "label" not in df.columns:
        raise ValidationFailed("label_column_missing")
    sensors = [c for c in df.columns if c not in ("timestamp", "label")]
    if not sensors:
        raise ValidationFailed("no_sensor_columns")

    run_name = f"{key}-raw"
    obj_key = validate_key(f"{key}/{run_name}.csv")
    store = get_store()
    store.put(obj_key, raw)

    ds = Dataset(
        key=key, display_name=display_name or key, source_url=str(source_path),
        sha256=sha, record_count=len(df), sensor_columns=sensors,
        primary=(key == "swat"), created_by=actor_id,
    )
    db.add(ds)
    db.flush()

    from app.services.audit import audit

    audit(db, actor_id=actor_id, action="dataset.ingested", entity_type="datasets",
          entity_id=ds.id, after={"sha256": sha, "rows": len(df)})
    return ds


def _read_table(raw: bytes, name: str) -> pd.DataFrame:
    if name.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(raw))
    return pd.read_csv(io.BytesIO(raw))


def create_preprocess_run(db: Session, *, dataset: Dataset, split_role: str,
                          config_hash: str) -> DatasetRun:
    run = DatasetRun(
        dataset_id=dataset.id,
        run_name=f"{dataset.key}-{split_role}",
        config_hash=config_hash,
        split_role=split_role,
        minio_root=f"aegis-raw/{dataset.key}/features/{split_role}/",
        status="pending",
    )
    db.add(run)
    db.flush()
    return run


def new_run_id() -> uuid.UUID:
    return uuid.uuid4()


def read_registered_csv(store, ds: Dataset) -> pd.DataFrame:
    from sqlalchemy import text as _sqltext  # noqa: F401

    key = f"{ds.key}/{ds.key}-raw.csv"
    from pipeline.storage import verify_hash

    verify_hash(store, key, ds.sha256)  # INV-016 at job start
    return _read_table(store.get(key), key)


def fixture_csv_bytes(n_rows: int = 720) -> bytes:
    from pipeline.ingest.synthetic import to_csv_bytes

    return to_csv_bytes(n_rows)


__all__ = [
    "DATASET_KEYS", "create_preprocess_run", "fixture_csv_bytes", "ingest_dataset",
    "new_run_id", "read_registered_csv",
]

csv.field_size_limit(1_000_000)
