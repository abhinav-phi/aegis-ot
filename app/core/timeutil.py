"""Timezone-normalization helpers (Step 8 fix).

SQLite stores/returns naive datetimes; PostgreSQL returns aware ones. All
in-process comparisons must use aware UTC values.
"""
from __future__ import annotations

import datetime as dt


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def aware(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value
