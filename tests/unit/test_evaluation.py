"""Unit tests for evaluation metrics, causal lift, and financial impact (Run 2B)."""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from churnexp.evaluation.financial import (
    _compute_horizon_financials,
    evaluate_financial_impact,
)
from churnexp.evaluation.lift import compute_two_proportion_stats, normal_cdf
from churnexp.evaluation.metrics import _compute_band_classification_metrics


def test_lift_matches_manual_contingency_math():
    """Verify compute_two_proportion_stats matches exact two-proportion z-test formulas."""
    # Treatment: 80 retained out of 100
    # Control: 60 retained out of 100
    res = compute_two_proportion_stats(
        n_treatment=100,
        retained_treatment=80,
        n_control=100,
        retained_control=60,
    )
    assert res["rate_treatment"] == 0.80
    assert res["rate_control"] == 0.60
    assert res["absolute_lift"] == pytest.approx(0.20, abs=1e-6)
    assert res["absolute_lift_pp"] == pytest.approx(20.0, abs=1e-4)
    assert res["relative_lift"] * 100 == pytest.approx(33.3333, abs=1e-3)
    assert res["incremental_retained"] == pytest.approx(20.0, abs=1e-6)

    # Standard error: sqrt(p_t*(1-p_t)/n_t + p_c*(1-p_c)/n_c)
    # se = sqrt(0.8*0.2/100 + 0.6*0.4/100) = sqrt(0.0016 + 0.0024) = sqrt(0.004) ~= 0.06324555
    se_expected = math.sqrt((0.8 * 0.2 / 100) + (0.6 * 0.4 / 100))
    assert res["se_unpooled"] == pytest.approx(se_expected, abs=1e-6)
    assert res["ci_95_low"] == pytest.approx(0.20 - 1.959964 * se_expected, abs=1e-5)
    assert res["ci_95_high"] == pytest.approx(0.20 + 1.959964 * se_expected, abs=1e-5)

    # Two-sided p-value using pooled standard error
    p_pool = 140 / 200.0
    se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (2.0 / 100.0))
    z_expected = 0.20 / se_pool
    p_expected = 2.0 * (1.0 - normal_cdf(abs(z_expected)))
    assert res["p_value"] == pytest.approx(p_expected, abs=1e-5)


def test_financial_calculations_integer_cents():
    """Verify financial formulas adhere to exact integer-cents arithmetic."""
    lift_stats = {
        "n_treatment": 100,
        "absolute_lift": 0.05,
        "ci_95_low": 0.01,
        "ci_95_high": 0.09,
    }
    realized_cost_cents = 150000  # $1,500.00
    avg_expected_margin_cents = 50000  # $500.00

    # Incremental retained: 0.05 * 100 = 5.0 customers
    # Benefit cents: 5.0 * 50,000 = 250,000 cents ($2,500.00)
    # Net cents: 250,000 - 150,000 = 100,000 cents ($1,000.00)
    fin = _compute_horizon_financials(
        horizon_label="180d",
        lift_stats=lift_stats,
        realized_cost_cents=realized_cost_cents,
        avg_expected_margin_cents=avg_expected_margin_cents,
    )

    assert fin["incremental_retained_customers"] == 5.0
    assert fin["benefit_cents"] == 250000
    assert fin["net_impact_cents"] == 100000
    assert fin["cost_per_incremental_retained_cents"] == 30000  # 150000 / 5 = 30000 cents
    assert fin["is_negative"] is False
    assert "positive" in fin["plain_statement"]


def test_binary_metrics_roc_auc():
    """Verify _compute_band_classification_metrics produces valid ROC-AUC and precision."""
    y_true = np.array([0, 0, 1, 1], dtype=np.int64)
    y_score = np.array([0.1, 0.4, 0.35, 0.8], dtype=np.float64)
    is_high = np.array([0, 0, 0, 1], dtype=np.int64)
    res = _compute_band_classification_metrics(y_true, y_score, is_high, include_brier=True)
    assert 0.0 <= res["roc_auc"] <= 1.0
    assert 0.0 <= res["brier_score"] <= 1.0
    assert "high_band_decision_rule" in res
    assert res["high_band_decision_rule"]["precision"] == 1.0
