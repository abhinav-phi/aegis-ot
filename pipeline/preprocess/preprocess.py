"""Causal cleaning + train-only normalization (R-ML-01..03)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def clean(df: pd.DataFrame, sensors: list[str], max_gap_s: int = 3) -> pd.DataFrame:
    """Forward-fill only (causal), gaps ≤ max_gap_s at 1 Hz; drop leading NaNs."""
    out = df.sort_values("timestamp").reset_index(drop=True)
    for col in sensors:
        if col not in out.columns:
            raise ValueError(f"missing_sensor_column:{col}")
        is_na = out[col].isna()
        run_id = (is_na != is_na.shift()).cumsum()
        run_len = out.groupby(run_id)[col].transform("size")
        gap_ok = is_na & (run_len <= max_gap_s)
        filled = out[col].ffill()
        out.loc[gap_ok, col] = filled[gap_ok]
    out = out.dropna(subset=sensors)  # remaining NaNs (leading/unfilled) dropped
    return out.reset_index(drop=True)


class Scaler:
    """z-score scaler fit on TRAIN ONLY; persisted as plain stats dict."""

    def __init__(self, mean: dict[str, float] | None = None,
                 std: dict[str, float] | None = None):
        self.mean = mean or {}
        self.std = std or {}

    @classmethod
    def fit(cls, df: pd.DataFrame, sensors: list[str]) -> "Scaler":
        mean = {c: float(df[c].mean()) for c in sensors}
        std = {c: float(df[c].std(ddof=0) or 1.0) for c in sensors}
        std = {c: (s if s > 0 else 1.0) for c, s in std.items()}
        return cls(mean=mean, std=std)

    def transform(self, df: pd.DataFrame, sensors: list[str]) -> np.ndarray:
        cols = [(df[c].to_numpy(dtype=float) - self.mean[c]) / self.std[c]
                for c in sensors]
        return np.column_stack(cols)

    def to_dict(self) -> dict:
        return {"mean": self.mean, "std": self.std}

    @classmethod
    def from_dict(cls, d: dict) -> "Scaler":
        return cls(mean=d.get("mean") or {}, std=d.get("std") or {})


def temporal_split_bounds(n_rows: int, fractions: dict[str, float]) -> dict[str, tuple[int, int]]:
    """Contiguous temporal bounds; windows never straddle boundaries (R-ML-01)."""
    train_end = int(n_rows * fractions["train"])
    val_end = train_end + int(n_rows * fractions["validation"])
    return {"train": (0, train_end), "validation": (train_end, val_end),
            "test": (val_end, n_rows)}
