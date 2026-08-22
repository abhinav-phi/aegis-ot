"""Split-aligned windower (W=60, S=1). Windows NEVER cross split boundaries."""
from __future__ import annotations

import numpy as np


def make_windows(matrix: np.ndarray, W: int, stride: int,
                 bounds: tuple[int, int]) -> np.ndarray:
    """Return windows fully inside [start, end). Raises on misconfiguration."""
    start, end = bounds
    if end - start < W:
        raise ValueError(f"split_too_short_for_window: {end - start} < {W}")
    out = [matrix[i:i + W] for i in range(start, end - W + 1, stride)]
    return np.stack(out)


def window_starts(bounds: tuple[int, int], W: int, stride: int) -> list[int]:
    start, end = bounds
    return list(range(start, end - W + 1, stride))


def per_window_stats(windows: np.ndarray, stats: list[str]) -> np.ndarray:
    """Frozen feature manifest layout (R-ML-05): [mean,std,min,max] per sensor."""
    parts = []
    for s in stats:
        fn = {"mean": np.mean, "std": np.std, "min": np.min, "max": np.max}[s]
        parts.append(fn(windows, axis=1))
    return np.concatenate(parts, axis=1)
