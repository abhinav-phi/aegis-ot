"""Fuzzy-rough channel reduction (ROB-01/02). Mask fit on TRAIN only.

Compact fuzzy-rough feature evaluation: fuzzy memberships from triangular
partition; dependency degree γ of each sensor via fuzzy lower approximation
against the anomaly-score decision feature. Reduction % is MEASURED (ROB-02).
"""
from __future__ import annotations

import numpy as np


def _triangular_membership(x: np.ndarray, centers: np.ndarray, width: float) -> np.ndarray:
    """Per-sample fuzzy memberships against triangular partition centers.

    Accepts x shaped [N] or [N, F] (F>1 collapses by mean); returns [N, C].
    """
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    vals = x[:, 0] if x.shape[1] == 1 else x.mean(axis=1)  # [N]
    d = np.abs(vals[:, None] - centers[None, :])           # [N, C]
    return np.clip(1.0 - d / width, 0.0, 1.0)


def _fuzzy_lower_approx(mu_B: np.ndarray, decision: np.ndarray) -> np.ndarray:
    """μ_{B}(y)(x_i) for fuzzy equivalence B and fuzzy decision classes."""
    n = mu_B.shape[0]
    lower = np.zeros(n)
    for i in range(n):
        rel = mu_B[i]  # similarity of i to all j under subset B
        lower[i] = float(np.min(np.maximum(1.0 - rel, decision)))
    return lower


def fuzzy_rough_dependency(X: np.ndarray, decision: np.ndarray,
                           n_centers: int = 4) -> np.ndarray:
    """Per-sensor dependency degree γ(sensor, decision). Higher = more relevant."""
    gammas = np.zeros(X.shape[1])
    dec_mu = _triangular_membership(decision.reshape(-1, 1),
                                    np.linspace(decision.min(), decision.max(), n_centers),
                                    width=max(1e-6, float(np.ptp(decision)) / 2))
    dec_membership = dec_mu.max(axis=1)  # crisp-ish fuzzy decision label
    for j in range(X.shape[1]):
        col = X[:, j]
        centers = np.linspace(col.min(), col.max(), n_centers)
        width = max(1e-6, float(np.ptp(col)) / 2)
        sim = _triangular_membership(col, centers, width).max(axis=1)
        lower = _fuzzy_lower_approx(sim.reshape(-1, 1), dec_membership)
        gammas[j] = float(lower.mean())
    return gammas


def select_mask(train_windows: np.ndarray, train_scores: np.ndarray,
                sensors: list[str], keep_threshold: float = 0.5) -> dict:
    """Fit on TRAIN ONLY. Returns ordered mask + measured reduction %."""
    X = train_windows.mean(axis=1)  # collapse time: [N, S] per-window mean signal
    gammas = fuzzy_rough_dependency(X, train_scores)
    top = max(1, int(np.percentile(gammas, 50)))
    mask = [{"sensor": s, "kept": bool(g >= keep_threshold * top)} for s, g in
            zip(sensors, gammas)]
    kept = sum(1 for m in mask if m["kept"])
    reduction_pct = round(100.0 * (len(mask) - kept) / len(mask), 2)  # measured
    return {"mask": mask, "reduction_pct": reduction_pct,
            "gammas": {s: float(g) for s, g in zip(sensors, gammas)}}
