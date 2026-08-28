"""Detection pipeline tables: model_versions, detections, anomalies, explanations.

CHG-DB-03 (artifact hash), CHG-DB-04 (detection uniqueness), CHG-DB-05
(anomaly→incident link), CHG-DB-20 (explanation uniqueness).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col
from app.db.models.enums import SEVERITIES, check_in


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint(
            "family IN ('lstm_ae','tcn_ae','iso_forest','xgboost','transformer_ae','anfis')",
            name="ck_model_family_enum",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    family: Mapped[str] = mapped_column(String(24), nullable=False)
    dataset_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_runs.id"), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_path: Mapped[str] = mapped_column(String(300), nullable=False)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64))  # CHG-DB-03
    threshold: Mapped[float | None] = mapped_column(Double)
    metrics_summary: Mapped[dict | None] = mapped_column(json_col())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


Index("ix_model_dataset", ModelVersion.dataset_run_id)
Index("ix_model_family", ModelVersion.family)


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (
        # CHG-DB-04: reruns upsert instead of duplicating.
        UniqueConstraint("dataset_run_id", "model_version_id", "window_start",
                         name="uq_detections_run_model_window"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_runs.id"), nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    window_start: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[float] = mapped_column(Double, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(nullable=False)
    threshold: Mapped[float] = mapped_column(Double, nullable=False)
    ground_truth: Mapped[bool | None] = mapped_column()
    latency_ms: Mapped[int | None] = mapped_column(Integer)  # DET-05
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )


Index("ix_det_window", Detection.dataset_run_id, Detection.model_version_id,
      Detection.window_start)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    detection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("detections.id"), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"))  # CHG-DB-05
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium",
    )
    top_sensors: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    low_confidence: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )

Anomaly.__table__.append_constraint(
    CheckConstraint(check_in("severity", SEVERITIES), name="ck_anomaly_severity_enum")
)


class AnomalyExplanation(Base):
    __tablename__ = "anomaly_explanations"
    __table_args__ = (UniqueConstraint("anomaly_id", name="uq_expl_anomaly"),)  # CHG-DB-20

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    anomaly_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("anomalies.id"), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    invariant_checks: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    consistency_score: Mapped[float | None] = mapped_column(Double)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )
