"""Synthetic SWaT-style mini-fixture (development/tests only — NOT real SWaT).

Deterministic (seeded). 1 Hz telemetry: normal operation, one attack segment
with LIT101 zeroing + P101 speed manipulation, GT labels.
"""
from __future__ import annotations

import datetime as dt
import io
import math

import numpy as np

SENSORS = ["FIT101", "LIT101", "P101_STATE", "AIT502"]


def generate_arrays(n_rows: int = 720, attack_start: int = 500,
                    attack_end: int = 560, seed: int = 7) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    t = np.arange(n_rows)
    fit = 2.4 + 0.05 * np.sin(2 * math.pi * t / 120) + rng.normal(0, 0.01, n_rows)
    lit = 50 + 6 * np.sin(2 * math.pi * t / 240) + rng.normal(0, 0.05, n_rows)
    pstate = (np.sin(2 * math.pi * t / 240) > -0.3).astype(float)
    ait = 7.1 + rng.normal(0, 0.02, n_rows)
    label = np.zeros(n_rows, dtype=int)

    # Attack F7-style: zero LIT101 while pump keeps running (numeric-only).
    seg = slice(attack_start, attack_end)
    lit[seg] = 0.02 + rng.normal(0, 0.005, attack_end - attack_start)
    pstate[seg] = 1.0
    label[seg] = 1

    return {"FIT101": fit, "LIT101": lit, "P101_STATE": pstate,
            "AIT502": ait, "label": label}


def timestamps(n_rows: int, start: str = "2026-01-01T00:00:00Z") -> list[str]:
    base = dt.datetime.fromisoformat(start)  # py311+ parses the Z suffix
    return [(base + dt.timedelta(seconds=i)).isoformat() for i in range(n_rows)]


def to_csv_bytes(n_rows: int = 720) -> bytes:
    arrays = generate_arrays(n_rows)
    ts = timestamps(len(arrays["label"]))
    buf = io.StringIO()
    header = ["timestamp", *SENSORS, "label"]
    buf.write(",".join(header) + "\n")
    for i in range(len(ts)):
        row = [ts[i]] + [f"{arrays[s][i]:.6f}" if s != "P101_STATE" else f"{int(arrays[s][i])}"
                         for s in SENSORS] + [str(int(arrays['label'][i]))]
        buf.write(",".join(row) + "\n")
    return buf.getvalue().encode("utf-8")


if __name__ == "__main__":  # pragma: no cover
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/fixtures/swat_mini.csv")
    ap.add_argument("--rows", type=int, default=720)
    a = ap.parse_args()
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(to_csv_bytes(a.rows))
    print(f"wrote {p} rows={a.rows}")
