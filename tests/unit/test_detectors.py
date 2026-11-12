"""Unit tests for blind business-rule detectors (Run 2B)."""

from __future__ import annotations

import pandas as pd
import pytest

from churnexp.config import load_config
from churnexp.generation.world import generate_world
from churnexp.validation.detectors import (
    DETECTOR_DEFINITIONS,
    run_detectors,
    summarize_detector_findings,
)


def test_clean_untreated_world_has_zero_detector_findings():
    """An untreated world with no campaigns has zero detector findings."""
    cfg = load_config("starter")
    world = generate_world(cfg)
    findings = run_detectors(world.tables)
    assert len(findings) == 0


def test_detector_a_triggers_on_leakage():
    """DET-A triggers when churn_date < prediction_date on churned=1."""
    tables = {
        "churn_outcome": pd.DataFrame(
            [
                {
                    "churn_id": "CHURN-CUS-000001-2026",
                    "customer_id": "CUS-000001",
                    "cycle_year": 2026,
                    "prediction_date": "2026-01-01",
                    "horizon_end": "2026-06-30",
                    "churned": 1,
                    "churn_date": "2025-11-15",
                    "churn_type": "VOLUNTARY",
                },
                {
                    "churn_id": "CHURN-CUS-000002-2026",
                    "customer_id": "CUS-000002",
                    "cycle_year": 2026,
                    "prediction_date": "2026-01-01",
                    "horizon_end": "2026-06-30",
                    "churned": 1,
                    "churn_date": "2026-02-15",
                    "churn_type": "VOLUNTARY",
                },
            ]
        )
    }
    findings = run_detectors(tables)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "DET-A-LABEL-BEFORE-PREDICTION"
    assert f.severity == "CRITICAL"
    assert f.entity_id == "CHURN-CUS-000001-2026"
    assert f.evidence["customer_id"] == "CUS-000001"
    assert f.evidence["churn_date"] == "2025-11-15"


def test_detector_b_triggers_on_ineligible_offer():
    """DET-B triggers when contact is assigned to an ineligible customer."""
    tables = {
        "customer": pd.DataFrame(
            [
                {
                    "customer_id": "CUS-000001",
                    "signup_date": "2025-12-15",  # tenure < 90 days
                    "marketing_opt_in": 1,
                    "payment_method": "CREDIT_CARD",
                    "channel": "ORGANIC",
                }
            ]
        ),
        "subscription": pd.DataFrame(
            [
                {
                    "subscription_id": "SUB-000001-01",
                    "customer_id": "CUS-000001",
                    "plan_tier": "BASIC",
                    "billing_interval": "MONTHLY",
                    "start_date": "2025-12-15",
                    "end_date": None,
                    "end_reason": None,
                    "status": "ACTIVE",
                    "monthly_price_cents": 1500,
                    "gross_margin_pct": 0.80,
                    "plan_version": 1,
                    "sequence_no": 1,
                    "previous_subscription_id": None,
                }
            ]
        ),
        "billing_event": pd.DataFrame(),
        "support_case": pd.DataFrame(),
        "offer": pd.DataFrame(
            [
                {
                    "offer_id": "OFF-2026-000001",
                    "offer_name": "10% off for 6 months",
                    "offer_type": "PERCENT_DISCOUNT",
                    "discount_pct": 0.10,
                    "free_months": None,
                    "duration_months": 6,
                    "max_cost_share_of_margin": 0.20,
                    "is_active": 1,
                    "valid_from": "2026-01-01",
                    "valid_to": "2026-12-31",
                }
            ]
        ),
        "risk_score": pd.DataFrame(
            [
                {
                    "score_id": "RS-CUS-000001-2026",
                    "customer_id": "CUS-000001",
                    "score": 0.85,
                    "band": "HIGH",
                    "percentile": 0.90,
                    "model_version": "logreg-v1",
                    "scored_date": "2026-01-01",
                }
            ]
        ),
        "campaign_contact": pd.DataFrame(
            [
                {
                    "contact_id": "CMP-CUS-000001-2026-W01",
                    "customer_id": "CUS-000001",
                    "offer_id": "OFF-2026-000001",
                    "experiment_group": "TREATMENT",
                    "contact_status": "SENT",
                    "assigned_at": "2026-01-05T08:00:00",
                    "sent_at": "2026-01-05T10:00:00",
                    "stratum": "HIGH",
                    "responded": 0,
                    "redeemed": 0,
                }
            ]
        ),
    }
    findings = run_detectors(tables)
    b_findings = [f for f in findings if f.rule_id == "DET-B-INELIGIBLE-OFFER"]
    assert len(b_findings) == 1
    fb = b_findings[0]
    assert fb.entity_id == "CMP-CUS-000001-2026-W01"
    assert fb.evidence["customer_id"] == "CUS-000001"
    assert any(fr["rule_id"] == "ER-002" for fr in fb.evidence["failed_rules"])


def test_detector_c_triggers_on_group_leakage():
    """DET-C triggers when a customer is assigned to both TREATMENT and CONTROL."""
    tables = {
        "campaign_contact": pd.DataFrame(
            [
                {
                    "contact_id": "CMP-CUS-000001-2026-W01",
                    "customer_id": "CUS-000001",
                    "offer_id": "OFF-2026-000001",
                    "experiment_group": "TREATMENT",
                    "contact_status": "SENT",
                    "assigned_at": "2026-01-05T08:00:00",
                    "sent_at": "2026-01-05T10:00:00",
                    "stratum": "HIGH",
                    "responded": 0,
                    "redeemed": 0,
                },
                {
                    "contact_id": "CMP-CUS-000001-2026-W02",
                    "customer_id": "CUS-000001",
                    "offer_id": "OFF-2026-000001",
                    "experiment_group": "CONTROL",
                    "contact_status": "WITHHELD",
                    "assigned_at": "2026-01-05T09:00:00",
                    "sent_at": None,
                    "stratum": "HIGH",
                    "responded": 0,
                    "redeemed": 0,
                },
            ]
        )
    }
    findings = run_detectors(tables)
    c_findings = [f for f in findings if f.rule_id == "DET-C-GROUP-LEAKAGE"]
    assert len(c_findings) == 1
    fc = c_findings[0]
    assert fc.evidence["customer_id"] == "CUS-000001"
    assert fc.severity == "CRITICAL"


def test_detector_d_triggers_on_multi_attribution():
    """DET-D triggers when a customer is attributed to multiple distinct offers."""
    tables = {
        "retention_outcome": pd.DataFrame(
            [
                {
                    "retention_id": "RET-CMP-CUS-000001-2026-W01",
                    "contact_id": "CMP-CUS-000001-2026-W01",
                    "customer_id": "CUS-000001",
                    "window_start": "2026-01-05",
                    "window_end": "2026-04-05",
                    "retained": 1,
                    "churned_at": None,
                    "attributed_offer_id": "OFF-2026-000001",
                },
                {
                    "retention_id": "RET-CMP-CUS-000001-2026-W02",
                    "contact_id": "CMP-CUS-000001-2026-W02",
                    "customer_id": "CUS-000001",
                    "window_start": "2026-01-05",
                    "window_end": "2026-04-05",
                    "retained": 1,
                    "churned_at": None,
                    "attributed_offer_id": "OFF-2026-000002",
                },
            ]
        )
    }
    findings = run_detectors(tables)
    d_findings = [f for f in findings if f.rule_id == "DET-D-MULTI-ATTRIBUTION"]
    assert len(d_findings) == 1
    fd = d_findings[0]
    assert fd.severity == "HIGH"
    assert fd.evidence["customer_id"] == "CUS-000001"
    assert set(fd.evidence["offers"]) == {"OFF-2026-000001", "OFF-2026-000002"}
