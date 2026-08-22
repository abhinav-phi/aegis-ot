"""Stress protocol (EVAL-02 / R-ML-08): committed augmentations on TEST only."""
from __future__ import annotations

import numpy as np
import yaml
from pathlib import Path


def load_grid(path: Path = Path("configs/stress.yaml")) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def apply_noise(windows: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    return windows + rng.normal(0.0, sigma, windows.shape)


def apply_zeroing(windows: np.ndarray, fraction: float,
                  rng: np.random.Generator) -> np.ndarray:
    out = windows.copy()
    n_time = out.shape[-1]
    k = max(1, int(n_time * fraction))
    idx = rng.choice(n_time, size=k, replace=False)
    out[:, :, idx] = 0.0
    return out


def apply_drift(windows: np.ndarray, slope: float) -> np.ndarray:
    t = np.arange(windows.shape[-1], dtype=float)
    return windows + slope * t[None, None, :]


def evaluate_robustness(score_fn, clean_windows: np.ndarray, grid: dict | None = None):
    """Returns per-stressor point-wise F1 deltas; identical arms guaranteed by
    construction because both call this with their own score_fn."""
    grid = grid or load_grid()
    rows = []
    labels = None
    for seed in grid.get("seeds", [1]):
        rng = np.random.default_rng(seed)
        base_scores = score_fn(clean_windows)
        if labels is None:
            raise ValueError("labels_required_via_score_fn_context")
        for sigma in grid["noise_sigmas"]:
            s = score_fn(apply_noise(clean_windows, sigma, rng))
            rows.append({"stressor": f"noise_{sigma}", "seed": seed,
                         "scores": s, "base_scores": base_scores})
        for frac in grid["zero_fractions"]:
            s = score_fn(apply_zeroing(clean_windows, frac, rng))
            rows.append({"stressor": f"zero_{frac}", "seed": seed,
                         "scores": s, "base_scores": base_scores})
        for slope in grid["drift_slopes"]:
            s = score_fn(apply_drift(clean_windows, slope))
            rows.append({"stressor": f"drift_{slope}", "seed": seed,
                         "scores": s, "base_scores": base_scores})
    return rows
