"""Unit tests for eligibility catalog, rules ER-001..ER-007, boundary cases, margin math, and source isolation (Step 7 item 4)."""

from datetime import date
from pathlib import Path
import pandas as pd
import pytest

from churnexp.config import load_config
from churnexp.eligibility.catalog import build_catalog
from churnexp.eligibility.engine import (
    eligible_offers,
    evaluate_eligibility,
    get_all_eligible_customer_offers,
)
from churnexp.eligibility.rules import (
    compute_offer_cost_and_max_margin_cents,
    eval_er001_active_subscription,
    eval_er002_min_tenure,
    eval_er003_marketing_opt_in,
    eval_er004_no_unsettled_invoice,
    eval_er005_no_open_escalated_case,
    eval_er006_risk_band,
    eval_er007_offer_margin,
)


def test_er001_to_er006_pass_fail_and_boundaries():
    """Verify ER-001..ER-006 pass, fail, and boundary conditions."""
    as_of = date(2026, 1, 5)

    # ER-001: active subscription
    assert eval_er001_active_subscription(True).passed == 1
    assert eval_er001_active_subscription(False).passed == 0

    # ER-002: tenure boundary 89 days (fail) vs 90 days (pass) at 2026-01-05
    # 2026-01-05 minus 90 days = 2025-10-07; minus 89 days = 2025-10-08
    r_89 = eval_er002_min_tenure("2025-10-08", as_of, min_tenure_days=90)
    r_90 = eval_er002_min_tenure("2025-10-07", as_of, min_tenure_days=90)
    assert r_89.passed == 0 and r_89.observed_value == "89"
    assert r_90.passed == 1 and r_90.observed_value == "90"

    # ER-003: marketing_opt_in
    assert eval_er003_marketing_opt_in(1).passed == 1
    assert eval_er003_marketing_opt_in(0).passed == 0

    # ER-004 & ER-005 direct unit checks
    assert eval_er004_no_unsettled_invoice(0).passed == 1
    assert eval_er004_no_unsettled_invoice(1).passed == 0
    assert eval_er005_no_open_escalated_case(0).passed == 1
    assert eval_er005_no_open_escalated_case(2).passed == 0

    # ER-006: risk_band in (HIGH, MEDIUM)
    assert eval_er006_risk_band("HIGH").passed == 1
    assert eval_er006_risk_band("MEDIUM").passed == 1
    assert eval_er006_risk_band("LOW").passed == 0


def test_er004_grace_boundary_and_er005_resolved_day_before_in_engine():
    """Verify invoice exactly at grace boundary passes, 1 day earlier fails; escalated case resolved day before passes."""
    cfg = load_config("starter")
    offer_df, rule_df, _ = build_catalog(cfg)
    # assignment_date = 2026-01-05, grace_days = 7 -> cutoff = 2025-12-29
    # CUS-000001: unsettled invoice on 2025-12-29 (at grace boundary -> PASS ER-004),
    #             escalated case resolved on 2026-01-04 (day before -> PASS ER-005), PREMIUM tier -> PASS all 3 offers
    # CUS-000002: unsettled invoice on 2025-12-28 (1 day before cutoff -> FAIL ER-004),
    #             escalated case resolved on 2026-01-05 (on assignment_date -> FAIL ER-005), BASIC tier -> FAIL offer 3
    customers = pd.DataFrame(
        [
            {
                "customer_id": "CUS-000001",
                "signup_date": "2025-10-07",  # exactly 90 days tenure
                "segment": "SMB",
                "channel": "ORGANIC",
                "region": "NA",
                "usage_pattern": "STEADY",
                "marketing_opt_in": 1,
            },
            {
                "customer_id": "CUS-000002",
                "signup_date": "2025-10-08",  # 89 days tenure -> FAIL ER-002
                "segment": "CONSUMER",
                "channel": "PAID",
                "region": "EU",
                "usage_pattern": "STEADY",
                "marketing_opt_in": 0,  # FAIL ER-003
            },
        ]
    )

    subscriptions = pd.DataFrame(
        [
            {
                "subscription_id": "SUB-CUS-000001-01",
                "customer_id": "CUS-000001",
                "previous_subscription_id": None,
                "sequence_no": 1,
                "plan_tier": "PREMIUM",
                "monthly_price_cents": 3999,
                "gross_margin_pct": 0.70,
                "start_date": "2025-10-07",
                "end_date": None,
                "end_reason": None,
            },
            {
                "subscription_id": "SUB-CUS-000002-01",
                "customer_id": "CUS-000002",
                "previous_subscription_id": None,
                "sequence_no": 1,
                "plan_tier": "BASIC",
                "monthly_price_cents": 999,
                "gross_margin_pct": 0.55,
                "start_date": "2025-10-08",
                "end_date": "2026-01-04",  # ended day before 2026-01-05 -> FAIL ER-001
                "end_reason": "VOLUNTARY_CANCEL",
            },
        ]
    )

    billing_event = pd.DataFrame(
        [
            # Invoice at grace boundary 2025-12-29 (unsettled) -> should PASS ER-004
            {
                "billing_event_id": "BILL-SUB-CUS-000001-01-202512-01",
                "subscription_id": "SUB-CUS-000001-01",
                "related_event_id": None,
                "event_type": "INVOICE",
                "event_date": "2025-12-29",
                "due_date": "2026-01-05",
                "amount_cents": 3999,
                "status": "POSTED",
                "failure_reason": None,
            },
            # Invoice 1 day earlier than grace boundary 2025-12-28 (unsettled) -> should FAIL ER-004
            {
                "billing_event_id": "BILL-SUB-CUS-000002-01-202512-01",
                "subscription_id": "SUB-CUS-000002-01",
                "related_event_id": None,
                "event_type": "INVOICE",
                "event_date": "2025-12-28",
                "due_date": "2026-01-04",
                "amount_cents": 999,
                "status": "POSTED",
                "failure_reason": None,
            },
        ]
    )

    support_case = pd.DataFrame(
        [
            # Escalated case resolved on 2026-01-04 (day before assignment_date) -> PASS ER-005
            {
                "case_id": "CASE-CUS-000001-0001",
                "customer_id": "CUS-000001",
                "subscription_id": "SUB-CUS-000001-01",
                "opened_at": "2025-12-15T10:00:00",
                "resolved_at": "2026-01-04T18:00:00",
                "category": "TECHNICAL",
                "severity": "HIGH",
                "escalated": 1,
            },
            # Escalated case resolved on 2026-01-05 (on assignment_date -> still open strictly before 2026-01-05) -> FAIL ER-005
            {
                "case_id": "CASE-CUS-000002-0001",
                "customer_id": "CUS-000002",
                "subscription_id": "SUB-CUS-000002-01",
                "opened_at": "2025-12-15T10:00:00",
                "resolved_at": "2026-01-05T09:00:00",
                "category": "BILLING",
                "severity": "HIGH",
                "escalated": 1,
            },
        ]
    )

    risk_scores = pd.DataFrame(
        [
            {
                "score_id": "RS-CUS-000001-2026-0101",
                "customer_id": "CUS-000001",
                "as_of_date": "2026-01-01",
                "model_version": "logreg-v1",
                "score": 0.45,
                "band": "HIGH",
                "rank": 1,
            },
            {
                "score_id": "RS-CUS-000002-2026-0101",
                "customer_id": "CUS-000002",
                "as_of_date": "2026-01-01",
                "model_version": "logreg-v1",
                "score": 0.05,
                "band": "LOW",
                "rank": 2,
            },
        ]
    )

    tables = {
        "customer": customers,
        "subscription": subscriptions,
        "billing_event": billing_event,
        "support_case": support_case,
    }

    re_df = evaluate_eligibility(
        tables=tables,
        risk_scores=risk_scores,
        offers=offer_df,
        rules=rule_df,
        as_of=date(2026, 1, 5),
    )
    # 9 rows per customer (6 customer rules + 3 offer ER-007 rows)
    assert len(re_df) == 18

    c1_evals = re_df[re_df["customer_id"] == "CUS-000001"].set_index(["rule_id", "offer_id"])
    for rid in ("ER-001", "ER-002", "ER-003", "ER-004", "ER-005", "ER-006"):
        assert int(c1_evals.loc[(rid, None), "passed"]) == 1

    c2_evals = re_df[re_df["customer_id"] == "CUS-000002"].set_index(["rule_id", "offer_id"])
    for rid in ("ER-001", "ER-002", "ER-003", "ER-004", "ER-005", "ER-006"):
        assert int(c2_evals.loc[(rid, None), "passed"]) == 0

    assert eligible_offers("CUS-000001", re_df) == [
        "OFF-2026-000001",
        "OFF-2026-000002",
        "OFF-2026-000003",
    ]
    assert eligible_offers("CUS-000002", re_df) == []
    all_elig = get_all_eligible_customer_offers(re_df)
    assert list(all_elig.keys()) == ["CUS-000001"]


def test_er007_cost_and_margin_math_exact_integer_cents():
    """Verify exact integer cents cost and margin math: BASIC cannot get offer 3; PREMIUM can."""
    # BASIC: price=999, margin_pct=0.55, expected_margin_months=6 -> expected_margin = round(999 * 0.55 * 6) = 3297 cents
    # Offer 1 (10% off 6m, max_share=0.20): cost = round(0.10 * 999 * 6) = 599, max = round(0.20 * 3296.7) = 659 -> PASS
    c1, m1, max1 = compute_offer_cost_and_max_margin_cents(999, 0.55, 6, "PERCENT_DISCOUNT", 0.10, None, 6, 0.20)
    assert (c1, m1, max1) == (599, 3297, 659)
    assert eval_er007_offer_margin("OFF-2026-000001", 999, 0.55, 6, "PERCENT_DISCOUNT", 0.10, None, 6, 0.20).passed == 1

    # Offer 3 (1 free month, max_share=0.25) on BASIC: cost = 999, max = round(0.25 * 3296.7) = 824 -> FAIL (999 > 824)
    c3_basic, m3_basic, max3_basic = compute_offer_cost_and_max_margin_cents(
        999, 0.55, 6, "FREE_MONTH", None, 1, 1, 0.25
    )
    assert (c3_basic, m3_basic, max3_basic) == (999, 3297, 824)
    res_basic_o3 = eval_er007_offer_margin(
        "OFF-2026-000003", 999, 0.55, 6, "FREE_MONTH", None, 1, 1, 0.25
    )
    assert res_basic_o3.passed == 0
    assert res_basic_o3.observed_value == "999"
    assert res_basic_o3.threshold_value == "824"

    # Offer 3 (1 free month, max_share=0.25) on PREMIUM (3999, 0.70):
    # expected_margin = round(3999 * 0.70 * 6) = 16796, max = round(0.25 * 16795.8) = 4199, cost = 3999 -> PASS
    c3_prem, m3_prem, max3_prem = compute_offer_cost_and_max_margin_cents(
        3999, 0.70, 6, "FREE_MONTH", None, 1, 1, 0.25
    )
    assert (c3_prem, m3_prem, max3_prem) == (3999, 16796, 4199)
    res_prem_o3 = eval_er007_offer_margin(
        "OFF-2026-000003", 3999, 0.70, 6, "FREE_MONTH", None, 1, 1, 0.25
    )
    assert res_prem_o3.passed == 1
    assert res_prem_o3.observed_value == "3999"
    assert res_prem_o3.threshold_value == "4199"


def test_source_files_contain_no_forbidden_ground_truth_strings():
    """Scan features/, modeling/, eligibility/, and experiment/assign.py for forbidden strings."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_root = repo_root / "src" / "churnexp"

    target_files = [
        *sorted((src_root / "features").glob("*.py")),
        *sorted((src_root / "modeling").glob("*.py")),
        *sorted((src_root / "eligibility").glob("*.py")),
        src_root / "experiment" / "assign.py",
    ]
    assert len(target_files) >= 8

    forbidden_tokens = ("latent", "ground_truth", "hidden_segment", "untreated_churn")
    for py_path in target_files:
        content = py_path.read_text(encoding="utf-8")
        for tok in forbidden_tokens:
            assert tok not in content, (
                f"Forbidden ground-truth token {tok!r} found in {py_path.relative_to(repo_root)}"
            )

