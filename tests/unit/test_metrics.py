"""Metric charter unit tests."""
from __future__ import annotations

import numpy as np

from eval.metrics.charter import (
    attribution_consistency,
    block_rate,
    citation_correctness,
    execution_unsafe_rate,
    f7_mrr3,
    false_block_rate,
    fpr,
    hallucination_rate,
    pa_k,
    precision_recall_f1,
    unsafe_action_rate,
)


def test_prf_perfect_and_empty():
    assert precision_recall_f1(10, 0, 0)["f1"] == 1.0
    assert precision_recall_f1(0, 0, 0)["f1"] == 0.0


def test_fpr():
    assert fpr(1, 9) == pytest_approx(0.1)


def pytest_approx(x):
    return round(x, 6)


def test_pa_k_crediting():
    labels = np.array([0] * 10 + [1] * 10 + [0] * 10)
    full = np.array([0] * 10 + [1] * 10 + [0] * 10)
    half = np.array([0] * 10 + [1] * 5 + [0] * 15)
    none = np.array([0] * 30)
    assert pa_k(labels, full, 50) == 1.0
    assert pa_k(labels, half, 50) == 1.0
    assert pa_k(labels, half, 80) == 0.0
    assert pa_k(labels, none, 50) == 0.0


def test_unsafe_action_rate_and_block_rate():
    proposed = [
        {"action": "set_pump_speed", "target": "P-101", "blocked": False},
        {"action": "set_pump_speed", "target": "P-101", "blocked": True},
        {"action": "query_tank_level", "target": "T-101", "blocked": False},
    ]
    gt = [{"action": "set_pump_speed", "target": "P-101"}]
    rate = unsafe_action_rate(proposed, gt)
    assert abs(rate - (1 / 3)) < 1e-9
    # GT-unsafe proposed steps: the two pump steps; one blocked ⇒ 0.5.
    gt_unsafe_rows = [p for p in proposed
                      if any(p["action"] == g["action"] and p["target"] == g["target"]
                             for g in gt)]
    assert block_rate(gt_unsafe_rows) == pytest_approx(0.5)


def test_execution_layer_must_be_zero():
    assert execution_unsafe_rate([], []) == 0.0
    assert execution_unsafe_rate(
        [{"action": "set_pump_speed", "target": "P-101"}],
        [{"action": "set_pump_speed", "target": "P-101"}]) > 0


def test_false_block_and_hallucination_and_citation():
    assert false_block_rate([{"blocked": True}, {"blocked": False}]) == 0.5
    assert hallucination_rate([{"supported_by_citations": False}] ) == 1.0
    assert citation_correctness([{"relevant": True, "supporting": True}]) == 1.0


def test_f7_mrr3():
    assert f7_mrr3(["FIT101", "LIT101"], "LIT101") == 0.5
    assert f7_mrr3(["A", "B", "C"], "Z") == 0.0


def test_attribution_consistency():
    same = [["LIT101", "FIT101"], ["LIT101", "FIT101"]]
    diff = [["LIT101", "FIT101"], ["AIT502"]]
    assert attribution_consistency(same) == 1.0
    assert attribution_consistency(diff) < 1.0
