"""Unit tests for generator configuration loading and validation rules."""

from dataclasses import replace
from datetime import date
import pytest

from churnexp.config import (
    load_config,
    validate_config,
)


def test_generator_config_loaded_values():
    """Verify generator config fields load from default.yaml."""
    cfg = load_config("starter")
    g = cfg.generator
    assert g.customers.early_signup_share == 0.85
    assert g.customers.seasonal_prob == 0.12
    assert g.customers.marketing_opt_in_prob == 0.82
    assert g.subscriptions.tier_price_cents == {"BASIC": 999, "STANDARD": 1999, "PREMIUM": 3999}
    assert g.subscriptions.monthly_plan_change_prob == 0.012
    assert g.churn.monthly_hazard_cap == 0.08
    assert g.churn.involuntary_prob == 0.30
    assert g.usage.base_minutes == {"BASIC": 600.0, "STANDARD": 1200.0, "PREMIUM": 2000.0}
    assert g.billing.failure_prob_consumer == 0.025
    assert g.billing.failure_prob_smb == 0.015
    assert g.support.loud_churn_rate_multiplier == 4.0


def test_generator_config_invalid_segment_probs():
    """Segment probabilities not summing to 1.0 must fail validation."""
    cfg = load_config("starter")
    bad_cust = replace(cfg.generator.customers, segment_probs={"CONSUMER": 0.60, "SMB": 0.25})
    bad_cfg = replace(cfg, generator=replace(cfg.generator, customers=bad_cust))
    with pytest.raises(ValueError, match="segment_probs must sum to 1.0"):
        validate_config(bad_cfg)


def test_generator_config_invalid_signup_dates():
    """Inverted customer signup date windows must fail validation."""
    cfg = load_config("starter")
    bad_cust = replace(
        cfg.generator.customers,
        early_signup_start=date(2025, 1, 1),
        early_signup_end=date(2024, 1, 1),
    )
    bad_cfg = replace(cfg, generator=replace(cfg.generator, customers=bad_cust))
    with pytest.raises(ValueError, match="signup date ranges"):
        validate_config(bad_cfg)


def test_generator_config_invalid_tier_prices():
    """Non-positive subscription price cents must fail validation."""
    cfg = load_config("starter")
    bad_sub = replace(
        cfg.generator.subscriptions,
        tier_price_cents={"BASIC": 0, "STANDARD": 1999, "PREMIUM": 3999},
    )
    bad_cfg = replace(cfg, generator=replace(cfg.generator, subscriptions=bad_sub))
    with pytest.raises(ValueError, match="tier_price_cents"):
        validate_config(bad_cfg)


def test_generator_config_invalid_hidden_segment_probs():
    """Missing key in hidden_segment_probs must fail validation."""
    cfg = load_config("starter")
    bad_churn = replace(
        cfg.generator.churn,
        hidden_segment_probs={"PERSUADABLE": 0.5, "SURE_THING": 0.5},
    )
    bad_cfg = replace(cfg, generator=replace(cfg.generator, churn=bad_churn))
    with pytest.raises(ValueError, match="hidden_segment_probs keys mismatch"):
        validate_config(bad_cfg)


def test_generator_config_invalid_plan_limits():
    """Plan limit minutes smaller than base minutes must fail validation."""
    cfg = load_config("starter")
    bad_usage = replace(
        cfg.generator.usage,
        plan_limit_minutes={"BASIC": 400.0, "STANDARD": 3000.0, "PREMIUM": 6000.0},
    )
    bad_cfg = replace(cfg, generator=replace(cfg.generator, usage=bad_usage))
    with pytest.raises(ValueError, match="plan_limit_minutes"):
        validate_config(bad_cfg)


def test_generator_config_invalid_billing_reasons():
    """Empty failure_reasons list must fail validation."""
    cfg = load_config("starter")
    bad_bill = replace(cfg.generator.billing, failure_reasons=[])
    bad_cfg = replace(cfg, generator=replace(cfg.generator, billing=bad_bill))
    with pytest.raises(ValueError, match="failure_reasons"):
        validate_config(bad_cfg)


def test_generator_config_invalid_support_escalation_prob():
    """Escalation probability > 1.0 must fail validation."""
    cfg = load_config("starter")
    bad_sup = replace(cfg.generator.support, escalation_prob=1.5)
    bad_cfg = replace(cfg, generator=replace(cfg.generator, support=bad_sup))
    with pytest.raises(ValueError, match="escalation_prob"):
        validate_config(bad_cfg)

