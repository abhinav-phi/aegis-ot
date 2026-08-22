"""Canonical serialization + SHA-256 content hashing (DEC-001, INV-005, HASH-001).

Canonical form = RFC 8785 (JCS) *subset*, fixed for this project:
  - object keys sorted by Unicode code point (BMP subset of the JCS UTF-16
    rule — documented limitation for non-BMP keys)
  - no whitespace; separators "," and ":"
  - strings: minimal JSON escaping, ensure_ascii=False, NFC-normalized, UTF-8
  - numbers: integers plain; integer-valued floats collapse (1.0 -> 1);
    float exponents lose leading zeros ("1e-07" -> "1e-7"); NaN/Inf REJECTED
  - duplicate keys rejected at parse time via `loads_strict`

The same rules are mirrored for JavaScript in
`frontend/scripts/canonical_check.mjs`; golden vectors:
`eval/golden/canonical_vectors.json` — digests MUST be identical across
Python and Node (verified in CI and Step 8).

Execution-time verification (HASH-002) recomputes the digest ONLY from the
stored `canonical_bytes` column and additionally asserts
`json.loads(canonical_bytes) == steps` so mutation of either the bytes or the
decoded column is detected.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from typing import Any

_EXP_ZEROS = re.compile(r"([eE][+-]?)0+(\d)")


def _fmt_float(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        raise ValueError("non_finite_number_in_canonical_payload")
    if value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    text = repr(value)
    # repr(1e-07) -> '1e-07' ; JS -> '1e-7'. Keep explicit '+' (JS: 1e+21).
    text = _EXP_ZEROS.sub(r"\1\2", text)
    return text


def _enc(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, float):
        out.append(_fmt_float(value))
    elif isinstance(value, str):
        out.append(json.dumps(unicodedata.normalize("NFC", value), ensure_ascii=False))
    elif isinstance(value, dict):
        out.append("{")
        for i, (k, v) in enumerate(sorted(value.items())):
            if i:
                out.append(",")
            if not isinstance(k, str):
                raise TypeError("non_string_object_key")
            out.append(json.dumps(unicodedata.normalize("NFC", k), ensure_ascii=False))
            out.append(":")
            _enc(v, out)
        out.append("}")
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for i, v in enumerate(value):
            if i:
                out.append(",")
            _enc(v, out)
        out.append("]")
    else:
        raise TypeError(f"unserializable_type:{type(value)!r}")


def canonical_bytes(payload: Any) -> bytes:
    out: list[str] = []
    _enc(payload, out)
    return "".join(out).encode("utf-8")


def content_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def steps_hash(steps: list[dict]) -> str:
    return content_hash(steps)


def loads_strict(text: str | bytes) -> Any:
    """JSON parse that REJECTS duplicate object keys (HB-01 parser differential)."""
    def _hook(pairs: list[tuple[str, Any]]) -> dict:
        seen: set[str] = set()
        for k, _ in pairs:
            if k in seen:
                raise ValueError(f"duplicate_json_key:{k}")
            seen.add(k)
        return dict(pairs)

    return json.loads(text, object_pairs_hook=_hook)


def short_hash(h: str) -> str:
    return h[-6:]
