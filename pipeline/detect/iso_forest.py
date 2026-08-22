"""Isolation Forest baseline on the FROZEN feature manifest (DET-02, R-ML-05)."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from pipeline.preprocess.windower import per_window_stats


class IsoForestDetector:
    family = "iso_forest"

    def __init__(self, stats: list[str], seed: int = 0):
        self.stats = stats
        self.seed = seed
        self.model: IsolationForest | None = None

    def fit(self, train_windows: np.ndarray) -> None:
        X = per_window_stats(train_windows, self.stats)
        self.model = IsolationForest(n_estimators=100, random_state=self.seed)
        self.model.fit(X)

    def score(self, windows: np.ndarray) -> np.ndarray:
        X = per_window_stats(windows, self.stats)
        raw = -self.model.score_samples(X)  # higher = more anomalous
        return _normalize(raw)

    def save_bytes(self) -> bytes:
        import io
        import pickle

        buf = io.BytesIO()
        pickle.dump({"stats": self.stats, "seed": self.seed, "model": self.model}, buf)
        return buf.getvalue()

    @classmethod
    def load_bytes(cls, data: bytes) -> "IsoForestDetector":
        import io
        import pickle

        obj = pickle.load(io.BytesIO(data))
        det = cls(stats=obj["stats"], seed=obj["seed"])
        det.model = obj["model"]
        return det


def _normalize(scores: np.ndarray) -> np.ndarray:
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-12:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)
