"""Declarative base + portable column types."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, MetaData, types
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class CoercedUuid(types.TypeDecorator):
    """Accepts str|UUID on bind (Step-8 fix): API/JWT paths carry string ids."""

    impl = types.Uuid
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def process_result_value(self, value, dialect):
        return value


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def json_col():
    """JSONB on PostgreSQL, JSON elsewhere (tests run on SQLite)."""
    return JSON().with_variant(JSONB(), "postgresql")


def coerce_uuid_columns() -> None:
    """Swap every Uuid column for the coercing variant (call once post-imports)."""
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, types.Uuid) and not isinstance(col.type, CoercedUuid):
                col.type = CoercedUuid()


def now_col():
    return DateTime(timezone=True), {"default": lambda: dt.datetime.now(dt.UTC)}
