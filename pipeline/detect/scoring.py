"""Scoring + threshold protocol (R-ML-04) and attribution (R-ML-07)."""
from __future__ import annotations

import math

import numpy as np


def threshold_from_validation(scores: np.ndarray, gt_normal: np.ndarray,
                              quantile: float = 0.99) -> float:
    """τ = quantile over VALIDATION GT-NORMAL windows only."""
    normal = scores[gt_normal.astype(bool)]
    if len(normal) == 0:
        raise ValueError("no_gt_normal_validation_windows")
    return float(np.quantile(normal, quantile))


def classify(scores: np.ndarray, tau: float) -> np.ndarray:
    return scores > tau


def contributions(residuals: np.ndarray, sensors: list[str],
                  epsilon: float = 1e-12,
                  low_confidence_floor: float = 1e-9) -> list[dict]:
    """share_i = r_i / (Σ r_j + ε); uniform + low_confidence when Σ≈0.

    residuals: [n_windows, n_sensors] — returns top-3 per window.
    """
    out: list[dict] = []
    for row in residuals:
        if not all(math.isfinite(float(v)) for v in row):
            raise ValueError("non_finite_residual")  # never silently score
        total = float(row.sum())
        if total < low_confidence_floor:
            shares = np.full(len(row), 1.0 / max(1, len(row)))
            low_confidence = True
        else:
            shares = row / (total + epsilon)
            low_confidence = False
        ranked = sorted(zip(sensors, shares), key=lambda kv: (-kv[1], kv[0]))  # deterministic ties
        out.append({
            "top_sensors": [{"sensor": s, "contribution_pct": round(float(v) * 100, 2)}
                            for s, v in ranked[:3]],
            "low_confidence": low_confidence,
        })
    return out
