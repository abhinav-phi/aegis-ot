"""Stress protocol (EVAL-02 / R-ML-08): committed augmentations on TEST only."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from eval.metrics.charter import fpr, pa_k, pr_auc, precision_recall_f1


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


def _pointwise_metrics(scores: np.ndarray, labels: np.ndarray,
                       tau: float) -> dict[str, float]:
    preds = scores > tau
    tp = int((preds & labels).sum())
    fp = int((preds & ~labels).sum())
    fn = int((~preds & labels).sum())
    tn = int((~preds & ~labels).sum())
    out = precision_recall_f1(tp, fp, fn)
    out["fpr"] = fpr(fp, tn)
    out["pr_auc"] = pr_auc(scores, labels.astype(float))
    out["pa_k_50"] = pa_k(labels, preds, 50.0)
    return {k: round(float(v), 6) for k, v in out.items()}


def evaluate_robustness(score_fn, clean_windows: np.ndarray, grid: dict | None = None,
                        *, labels: np.ndarray | None = None,
                        threshold_quantile: float = 0.99) -> list[dict]:
    """Identical-arms stress sweep: both detector arms are scored under the
    SAME seeded augmentations; per-stressor point-wise metrics are computed
    against τ fixed on the CLEAN scores of GT-normal windows only (no test-time
    calibration — R23/EVAL-02)."""
    grid = grid or load_grid()
    rows = []
    if labels is None or len(labels) != len(clean_windows):
        raise ValueError("labels_required_for_pointwise_metrics")
    base_scores = score_fn(clean_windows)
    gt_normal = ~labels.astype(bool)
    if gt_normal.any():
        tau = float(np.quantile(base_scores[gt_normal], threshold_quantile))
    else:
        tau = float(np.quantile(base_scores, threshold_quantile))
    rows.append({"stressor": "clean", "seed": None, **_pointwise_metrics(
        base_scores, labels, tau)})
    for seed in grid.get("seeds", [1]):
        rng = np.random.default_rng(seed)
        for sigma in grid["noise_sigmas"]:
            s = score_fn(apply_noise(clean_windows, sigma, rng))
            rows.append({"stressor": f"noise_{sigma}", "seed": seed,
                         **_pointwise_metrics(s, labels, tau)})
        for frac in grid["zero_fractions"]:
            s = score_fn(apply_zeroing(clean_windows, frac, rng))
            rows.append({"stressor": f"zero_{frac}", "seed": seed,
                         **_pointwise_metrics(s, labels, tau)})
        for slope in grid["drift_slopes"]:
            s = score_fn(apply_drift(clean_windows, slope))
            rows.append({"stressor": f"drift_{slope}", "seed": seed,
                         **_pointwise_metrics(s, labels, tau)})
    return rows
