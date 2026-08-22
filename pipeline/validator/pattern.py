"""C3 suspicious-pattern filter with hardened normalization (VAL-002).

Normalization: NFKC → casefold → zero-width removal, applied before matching;
base64/%XX payloads are iteratively decoded up to a bounded depth and each
layer is scanned.
"""
from __future__ import annotations

import base64
import re
import unicodedata
from pathlib import Path

import yaml

DEFAULT_MARKERS = [
    "ignore_prior", "ignore previous instructions", "disregard all",
    "<sys>", "</sys>", "system prompt", "developer message",
    "require immediate manual override", "acknowledge:",
    "!cmd", "sh -c", "bash -c", "powershell -c",
    "../../", "/etc/passwd", "rm -rf", "sudo ",
]

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().translate(_ZERO_WIDTH)


def _decode_layer(text: str) -> list[str]:
    layers = [text]
    current = text
    for _ in range(3):  # bounded iterative decoding (VAL-002)
        candidates: list[str] = []
        for token in re.findall(r"[A-Za-z0-9+/=]{16,}", current):
            try:
                padded = token + "=" * (-len(token) % 4)
                candidates.append(base64.b64decode(padded, validate=True).decode("utf-8"))
            except Exception:
                pass
        candidates += [m.group(0) for m in re.finditer(r"%[0-9a-fA-F]{2}(?:%[0-9a-fA-F]{2}){4,}", current)]
        decoded = []
        for c in candidates:
            try:
                from urllib.parse import unquote

                decoded.append(unquote(c))
            except Exception:
                decoded.append(c)
        if not decoded:
            break
        layers.extend(decoded)
        current = " ".join(decoded)
    return layers


def load_markers(path: str | Path = "configs/policy/patterns.yaml") -> list[str]:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return list(raw.get("markers") or []) or DEFAULT_MARKERS
    except OSError:
        return DEFAULT_MARKERS


class PatternFilter:
    def __init__(self, markers: list[str] | None = None):
        self.markers = [normalize(m) for m in (markers if markers is not None else load_markers())]

    def scan(self, text: str) -> tuple[bool, str | None]:
        """Return (clean, matched_marker). Hard markers on write/control ⇒ block."""
        norm = normalize(text)
        for layer in _decode_layer(norm):
            for marker in self.markers:
                if marker in layer:
                    return False, marker
        return True, None
