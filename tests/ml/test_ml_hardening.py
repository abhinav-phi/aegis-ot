"""ML hardening tests: leakage, attribution, threshold, windower."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def test_windower_refuses_split_crossing():
    from pipeline.preprocess.windower import make_windows

    matrix = np.zeros((100, 3))
    with pytest.raises(ValueError):
        make_windows(matrix, W=60, stride=1, bounds=(50, 90))  # 40 < 60
    w = make_windows(matrix, W=60, stride=1, bounds=(0, 100))
    assert w.shape == (41, 60, 3)


def test_temporal_split_bounds_contiguous():
    from pipeline.preprocess.preprocess import temporal_split_bounds

    b = temporal_split_bounds(1000, {"train": 0.6, "validation": 0.2, "test": 0.2})
    assert b["train"][1] == b["validation"][0]
    assert b["validation"][1] == b["test"][0]


def test_clean_is_causal_forward_fill_only():
    from pipeline.preprocess.preprocess import clean

    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=5, freq="s"),
        "FIT101": [1.0, np.nan, np.nan, 2.0, 3.0],
        "LIT101": [5.0] * 5,
    })
    out = clean(df, ["FIT101", "LIT101"], max_gap_s=3)
    assert list(out["FIT101"]) == [1.0, 1.0, 1.0, 2.0, 3.0]  # forward-filled


def test_clean_drops_leading_nan():
    from pipeline.preprocess.preprocess import clean

    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=4, freq="s"),
        "FIT101": [np.nan, 1.0, 2.0, 3.0],
        "LIT101": [1.0] * 4,
    })
    out = clean(df, ["FIT101", "LIT101"])
    assert len(out) == 3 and out["FIT101"].iloc[0] == 1.0


def test_threshold_uses_gt_normal_only():
    from pipeline.detect.scoring import threshold_from_validation

    scores = np.array([0.1, 0.2, 0.3, 100.0])       # last is an attack window
    gt_normal = np.array([True, True, True, False])
    tau = threshold_from_validation(scores, gt_normal, quantile=0.99)
    assert tau < 1.0  # attack window excluded from τ derivation


def test_attribution_epsilon_and_low_confidence():
    from pipeline.detect.scoring import contributions

    sensors = ["A", "B", "C"]
    res = contributions(np.array([[0.0, 0.0, 0.0]]), sensors)
    assert res[0]["low_confidence"] is True
    assert abs(res[0]["top_sensors"][0]["contribution_pct"] - 33.33) < 0.1

    res2 = contributions(np.array([[8.0, 2.0, 0.0]]), sensors)
    top = res2[0]["top_sensors"]
    assert top[0]["sensor"] == "A" and abs(top[0]["contribution_pct"] - 80.0) < 0.01


def test_attribution_ties_deterministic():
    from pipeline.detect.scoring import contributions

    r = contributions(np.array([[1.0, 1.0, 1.0]]), ["C", "A", "B"])[0]["top_sensors"]
    assert [t["sensor"] for t in r] == ["A", "B", "C"]


def test_non_finite_residual_raises():
    from pipeline.detect.scoring import contributions

    with pytest.raises(ValueError):
        contributions(np.array([[np.inf, 1.0, 1.0]]), ["A", "B", "C"])


def test_scaler_train_fit_semantics():
    from pipeline.preprocess.preprocess import Scaler

    train = pd.DataFrame({"x": [0.0] * 10 + [10.0]})
    sc = Scaler.fit(train, ["x"])
    assert sc.to_dict()["std"]["x"] > 0
