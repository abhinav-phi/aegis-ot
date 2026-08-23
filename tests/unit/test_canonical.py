"""Canonical hashing + verdict function golden tests."""
from __future__ import annotations

import pytest

from app.core.canonical import canonical_bytes, content_hash, steps_hash


def test_canonical_is_stable_across_key_order():
    a = [{"action": "x", "params": {"b": 1, "a": 2}}]
    b = [{"params": {"a": 2, "b": 1}, "action": "x"}]
    assert steps_hash(a) == steps_hash(b)


def test_hash_changes_with_content():
    a = [{"action": "x"}]
    b = [{"action": "y"}]
    assert steps_hash(a) != steps_hash(b)


def test_nan_rejected_in_canonical():

    with pytest.raises(ValueError):
        canonical_bytes({"v": float("nan")})


def test_content_hash_hex64():
    h = content_hash("x")
    assert len(h) == 64 and int(h, 16) >= 0


def test_verdict_severity_ordering():
    from pipeline.validator.verdict import SEVERITY

    assert SEVERITY["block"] > SEVERITY["escalate"] > \
        SEVERITY["require_approval"] > SEVERITY["allow"]
