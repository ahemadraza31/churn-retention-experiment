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


def test_empty_arm_subgroups_and_markdown_formatting():
    """Verify empty-arm subgroups return null lift/CI/p-val/incremental and markdown renders 'n/a (arm empty)'."""
    from churnexp.evaluation.report import format_evaluation_markdown

    # Treatment arm empty
    res_t0 = compute_two_proportion_stats(
        n_treatment=0,
        retained_treatment=0,
        n_control=2,
        retained_control=2,
    )
    assert res_t0["absolute_lift"] is None
    assert res_t0["absolute_lift_pp"] is None
    assert res_t0["ci_95_low"] is None
    assert res_t0["ci_95_high"] is None
    assert res_t0["p_value"] is None
    assert res_t0["incremental_retained"] is None

    # Control arm empty
    res_c0 = compute_two_proportion_stats(
        n_treatment=4,
        retained_treatment=3,
        n_control=0,
        retained_control=0,
    )
    assert res_c0["absolute_lift"] is None
    assert res_c0["absolute_lift_pp"] is None
    assert res_c0["ci_95_low"] is None
    assert res_c0["ci_95_high"] is None
    assert res_c0["p_value"] is None
    assert res_c0["incremental_retained"] is None

    # Test markdown formatting for empty arm
    mock_results = {
        "scale": "starter",
        "exclusions": {"total_unique_excluded_customers": 0, "counts_by_detector": {}},
        "model_metrics": {
            "label_180d": {"n": 100, "positives": 10, "base_rate": 0.1, "roc_auc": 0.75, "brier_score": 0.08, "high_band_decision_rule": {"precision": 0.5, "recall": 0.5, "f1": 0.5, "precision_lift": 2.0}},
            "label_90d": {"n": 100, "positives": 5, "base_rate": 0.05, "roc_auc": 0.70, "brier_score": 0.04, "high_band_decision_rule": {"precision": 0.4, "recall": 0.4, "f1": 0.4, "precision_lift": 2.0}},
        },
        "experiment": {
            "primary_90d": {
                "n_treatment": 92, "retained_treatment": 80, "rate_treatment": 0.869565,
                "n_control": 111, "retained_control": 95, "rate_control": 0.855856,
                "absolute_lift": 0.013709, "absolute_lift_pp": 1.37,
                "ci_95_low_pp": -8.0, "ci_95_high_pp": 10.7,
                "p_value": 0.78, "relative_lift": 0.016, "incremental_retained": 1.26,
                "incremental_retained_ci_low": -7.36, "incremental_retained_ci_high": 9.88,
                "nnt": None,
            },
            "secondary_180d": {
                "n_treatment": 92, "retained_treatment": 75, "rate_treatment": 0.815217,
                "n_control": 111, "retained_control": 90, "rate_control": 0.810811,
                "absolute_lift": 0.004406, "absolute_lift_pp": 0.44,
                "ci_95_low_pp": -9.9, "ci_95_high_pp": 10.8,
                "p_value": 0.94, "relative_lift": 0.005, "incremental_retained": 0.41,
                "incremental_retained_ci_low": -9.1, "incremental_retained_ci_high": 9.9,
                "nnt": None,
            },
            "subgroups": {
                "by_offer": {
                    "OFF-2026-000003": {
                        "primary_90d": res_t0,
                        "secondary_180d": res_t0,
                    }
                },
                "by_stratum": {},
            },
            "randomization_check": {
                "any_flagged": True,
                "covariate_balance": {
                    "tenure_days": {
                        "mean_treatment": 631.77,
                        "mean_control": 596.90,
                        "smd": 0.135239,
                        "flagged": True,
                    }
                }
            },
            "correlation_vs_incremental": {
                "a_treatment_all_retention_rate_90d": 0.8696,
                "a_treatment_all_retention_rate_180d": 0.8152,
                "b_redeemers_retention_rate_90d": 0.95,
                "b_redeemers_retention_rate_180d": 0.90,
                "c_control_retention_rate_90d": 0.8559,
                "c_control_retention_rate_180d": 0.8108,
                "d_attributed_retained_customers": 40,
                "e_incremental_retained_customers_90d": 1.26,
                "e_incremental_retained_customers_180d": 0.41,
                "n_redeemers": 42,
                "why_not_causal": "Redeemers self-select.",
            }
        },
        "financial": {
            "expected_margin_months": 6,
            "avg_expected_margin_cents": 75000,
            "realized_cost_cents": 120000,
            "redeemed_retained_90d_count": 40,
            "headline_180d": {
                "incremental_retained_customers": 0.41,
                "incremental_retained_ci_low": -9.1,
                "incremental_retained_ci_high": 9.9,
                "benefit_cents": 30750,
                "benefit_ci_low_cents": -682500,
                "benefit_ci_high_cents": 742500,
                "realized_cost_cents": 120000,
                "net_impact_cents": -89250,
                "net_impact_ci_low_cents": -802500,
                "net_impact_ci_high_cents": 622500,
                "cost_per_incremental_retained_cents": 292683,
                "plain_statement": "Point estimate net impact is negative and 95% CI includes zero.",
            },
            "primary_90d": {
                "incremental_retained_customers": 1.26,
                "incremental_retained_ci_low": -7.36,
                "incremental_retained_ci_high": 9.88,
                "benefit_cents": 94500,
                "benefit_ci_low_cents": -552000,
                "benefit_ci_high_cents": 741000,
                "realized_cost_cents": 120000,
                "net_impact_cents": -25500,
                "net_impact_ci_low_cents": -672000,
                "net_impact_ci_high_cents": 621000,
                "cost_per_incremental_retained_cents": 95238,
                "plain_statement": "Point estimate net impact is negative and 95% CI includes zero.",
            }
        }
    }

    md = format_evaluation_markdown(mock_results)
    assert "n/a (arm empty)" in md
    assert "-100.00" not in md
    assert "small sample" in md
    assert "Realized cost counts every redeemer who stayed, including customers who would have stayed anyway." in md
    assert "## 5. Business reading" in md
    assert "These conclusions hold only under the stated simulation parameters." in md

