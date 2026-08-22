"""Dataset registry tables (CHG-DB-01/-02)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, json_col
from app.db.models.enums import DATASET_RUN_STATUSES, check_in


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        # CHG-DB-01: at most one row may be flagged primary.
        Index("uq_datasets_single_primary", "primary", unique=True,
              postgresql_where=text('"primary"'),
              sqlite_where=text('"primary"')),
        CheckConstraint("key IN ('swat','wustl_iiot2021','wadi','synthetic')",
                        name="ck_datasets_key_enum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sensor_columns: Mapped[list] = mapped_column(json_col(), nullable=False, default=list)
    primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )


class DatasetRun(Base):
    """Immutable preprocessing lineage. CHG-DB-02: lifecycle status + integrity."""

    __tablename__ = "dataset_runs"
    __table_args__ = (
        CheckConstraint(check_in("status", DATASET_RUN_STATUSES), name="ck_drun_status_enum"),
        CheckConstraint(check_in("split_role", ("train", "validation", "test")),
                        name="ck_drun_split_enum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    run_name: Mapped[str] = mapped_column(String(120), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    split_role: Mapped[str] = mapped_column(String(16), nullable=False)
    minio_root: Mapped[str] = mapped_column(String(300), nullable=False)
    feature_manifest: Mapped[dict] = mapped_column(json_col(), nullable=False, default=dict)
    rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    normalization_stats: Mapped[dict | None] = mapped_column(json_col())
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    verified_hashes: Mapped[dict] = mapped_column(json_col(), nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )


Index("ix_dataset_runs_dataset", DatasetRun.dataset_id, DatasetRun.created_at)
