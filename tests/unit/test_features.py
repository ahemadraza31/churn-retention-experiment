"""Unit tests for feature builder (Step 7 items 1 and 2: mutate-the-future leakage defense and hand-built tables)."""

from datetime import date
import pandas as pd
import pytest

from churnexp.config import load_config
from churnexp.features.builder import FEATURE_SNAPSHOT_COLUMNS, build_features
from churnexp.generation.world import generate_world


@pytest.fixture(scope="module")
def starter_cfg():
    return load_config("starter")


@pytest.fixture(scope="module")
def base_world(starter_cfg):
    return generate_world(starter_cfg)


@pytest.mark.parametrize(
    "as_of_date",
    [date(2025, 7, 1), date(2026, 1, 1)],
    ids=["P0_2025-07-01", "P_2026-01-01"],
)
def test_mutate_the_future_leakage_defense(base_world, as_of_date):
    """Mutating or deleting rows >= as_of, shifting end_dates >= as_of, or altering 2026 labels must not change features."""
    as_of_str = as_of_date.isoformat()
    base_tables = base_world.tables
    baseline_feats = build_features(base_tables, as_of=as_of_date, lookback_months=6)
    assert not baseline_feats.empty
    assert list(baseline_feats.columns) == FEATURE_SNAPSHOT_COLUMNS
    assert set(baseline_feats["as_of_date"]) == {as_of_str}

    # (a) Change values of every usage, billing, and support row dated on or after as_of
    tables_a = {k: v.copy() for k, v in base_tables.items()}
    u_mask_a = tables_a["usage_snapshot"]["period_end"].astype(str) >= as_of_str
    tables_a["usage_snapshot"].loc[u_mask_a, "usage_minutes"] = 99999.0
    tables_a["usage_snapshot"].loc[u_mask_a, "active_days"] = 28
    tables_a["usage_snapshot"].loc[u_mask_a, "sessions"] = 999

    b_mask_a = tables_a["billing_event"]["event_date"].astype(str) >= as_of_str
    tables_a["billing_event"].loc[b_mask_a, "amount_cents"] = 888888
    tables_a["billing_event"].loc[b_mask_a, "event_type"] = "PAYMENT_FAILED"
    tables_a["billing_event"].loc[b_mask_a, "status"] = "FAILED"

    s_mask_a = tables_a["support_case"]["opened_at"].astype(str).str.slice(0, 10) >= as_of_str
    tables_a["support_case"].loc[s_mask_a, "category"] = "CANCELLATION_INQUIRY"
    tables_a["support_case"].loc[s_mask_a, "severity"] = "HIGH"
    # Also mutate resolved_at >= as_of on support cases opened before as_of
    s_res_mask = (
        tables_a["support_case"]["resolved_at"].notna()
        & (tables_a["support_case"]["resolved_at"].astype(str).str.slice(0, 10) >= as_of_str)
    )
    tables_a["support_case"].loc[s_res_mask, "resolved_at"] = "2026-06-30T23:59:59"

    feats_a = build_features(tables_a, as_of=as_of_date, lookback_months=6)
    pd.testing.assert_frame_equal(baseline_feats, feats_a, check_exact=True)

    # (b) Delete all usage, billing, and support rows dated on or after as_of
    tables_b = {k: v.copy() for k, v in base_tables.items()}
    tables_b["usage_snapshot"] = tables_b["usage_snapshot"][
        tables_b["usage_snapshot"]["period_end"].astype(str) < as_of_str
    ].reset_index(drop=True)
    tables_b["billing_event"] = tables_b["billing_event"][
        tables_b["billing_event"]["event_date"].astype(str) < as_of_str
    ].reset_index(drop=True)
    tables_b["support_case"] = tables_b["support_case"][
        tables_b["support_case"]["opened_at"].astype(str).str.slice(0, 10) < as_of_str
    ].reset_index(drop=True)

    feats_b = build_features(tables_b, as_of=as_of_date, lookback_months=6)
    pd.testing.assert_frame_equal(baseline_feats, feats_b, check_exact=True)

    # (c) Change subscription end_dates that are >= as_of to other dates still >= as_of (or None)
    tables_c = {k: v.copy() for k, v in base_tables.items()}
    sub_c = tables_c["subscription"]
    end_ge_mask = sub_c["end_date"].notna() & (sub_c["end_date"].astype(str) >= as_of_str)
    assert end_ge_mask.any()
    sub_c.loc[end_ge_mask, "end_date"] = "2026-06-29"
    feats_c = build_features(tables_c, as_of=as_of_date, lookback_months=6)
    pd.testing.assert_frame_equal(baseline_feats, feats_c, check_exact=True)

    # (d) Change or add 2026 churn_outcome rows
    tables_d = {k: v.copy() for k, v in base_tables.items()}
    fake_2026 = tables_d["churn_outcome"].copy()
    fake_2026["churn_id"] = fake_2026["customer_id"].map(lambda c: f"CHURN-{c}-2026")
    fake_2026["cycle_year"] = 2026
    fake_2026["prediction_date"] = "2026-01-01"
    fake_2026["horizon_end"] = "2026-06-30"
    fake_2026["churned"] = 1
    fake_2026["churn_date"] = "2026-02-01"
    fake_2026["churn_type"] = "VOLUNTARY"
    tables_d["churn_outcome"] = pd.concat(
        [tables_d["churn_outcome"], fake_2026], ignore_index=True
    )
    feats_d = build_features(tables_d, as_of=as_of_date, lookback_months=6)
    pd.testing.assert_frame_equal(baseline_feats, feats_d, check_exact=True)


def test_hand_built_tables_known_expected_values():
    """Verify exact ratio, slope, failed payments, balance, downgrade flag, and short history on hand-built tables."""
    # Two customers active at as_of = 2025-07-01:
    # CUS-000001: full 6m history (2025-01..2025-06), downgrade in 2025-04, 1 failed payment, unsettled invoice
    # CUS-000002: short 2m history (signed up 2025-05-01, snapshots in 2025-05 and 2025-06 only)
    customers = pd.DataFrame(
        [
            {
                "customer_id": "CUS-000001",
                "signup_date": "2024-07-01",
                "segment": "SMB",
                "channel": "PAID",
                "region": "NA",
                "usage_pattern": "SEASONAL",
                "marketing_opt_in": 1,
                "billing_day": 10,
            },
            {
                "customer_id": "CUS-000002",
                "signup_date": "2025-05-01",
                "segment": "CONSUMER",
                "channel": "ORGANIC",
                "region": "EU",
                "usage_pattern": "STEADY",
                "marketing_opt_in": 0,
                "billing_day": 15,
            },
        ]
    )

    subscriptions = pd.DataFrame(
        [
            # CUS-000001 downgraded from PREMIUM to STANDARD on 2025-04-10
            {
                "subscription_id": "SUB-CUS-000001-01",
                "customer_id": "CUS-000001",
                "previous_subscription_id": None,
                "sequence_no": 1,
                "plan_tier": "PREMIUM",
                "monthly_price_cents": 3999,
                "gross_margin_pct": 0.70,
                "start_date": "2024-07-01",
                "end_date": "2025-04-09",
                "end_reason": "PLAN_CHANGE",
            },
            {
                "subscription_id": "SUB-CUS-000001-02",
                "customer_id": "CUS-000001",
                "previous_subscription_id": "SUB-CUS-000001-01",
                "sequence_no": 2,
                "plan_tier": "STANDARD",
                "monthly_price_cents": 1999,
                "gross_margin_pct": 0.62,
                "start_date": "2025-04-10",
                "end_date": None,
                "end_reason": None,
            },
            # CUS-000002 single BASIC subscription
            {
                "subscription_id": "SUB-CUS-000002-01",
                "customer_id": "CUS-000002",
                "previous_subscription_id": None,
                "sequence_no": 1,
                "plan_tier": "BASIC",
                "monthly_price_cents": 999,
                "gross_margin_pct": 0.55,
                "start_date": "2025-05-01",
                "end_date": None,
                "end_reason": None,
            },
        ]
    )

    # Monthly usage for CUS-000001 across 2025-01..2025-06: [100, 200, 300, 400, 500, 600]
    # prev3m = 100+200+300 = 600, 3m = 400+500+600 = 1500, ratio = 1500/600 = 2.5
    # slope = +100.0 per month, mean = 350.0 -> normalized slope = 100 / 350 = 0.285714
    usage_rows = [
        ("SNAP-SUB-CUS-000001-01-2025-01", "SUB-CUS-000001-01", "2025-01", "2025-01-31", 10, 15, 100.0),
        ("SNAP-SUB-CUS-000001-01-2025-02", "SUB-CUS-000001-01", "2025-02", "2025-02-28", 12, 18, 200.0),
        ("SNAP-SUB-CUS-000001-01-2025-03", "SUB-CUS-000001-01", "2025-03", "2025-03-31", 14, 20, 300.0),
        ("SNAP-SUB-CUS-000001-02-2025-04", "SUB-CUS-000001-02", "2025-04", "2025-04-30", 16, 22, 400.0),
        ("SNAP-SUB-CUS-000001-02-2025-05", "SUB-CUS-000001-02", "2025-05", "2025-05-31", 18, 25, 500.0),
        ("SNAP-SUB-CUS-000001-02-2025-06", "SUB-CUS-000001-02", "2025-06", "2025-06-30", 21, 30, 600.0),
        # CUS-000002 only 2 months of history (2025-05 and 2025-06): [150, 300]
        # Short history (<6m -> ratio=1.0; <3m -> slope=0.0)
        ("SNAP-SUB-CUS-000002-01-2025-05", "SUB-CUS-000002-01", "2025-05", "2025-05-31", 8, 10, 150.0),
        ("SNAP-SUB-CUS-000002-01-2025-06", "SUB-CUS-000002-01", "2025-06", "2025-06-30", 11, 14, 300.0),
    ]
    usage_snapshot = pd.DataFrame(
        [
            {
                "snapshot_id": r[0],
                "subscription_id": r[1],
                "snapshot_month": r[2],
                "period_end": r[3],
                "active_days": r[4],
                "sessions": r[5],
                "usage_minutes": r[6],
                "features_used": 3,
                "usage_pct_of_limit": 0.2,
            }
            for r in usage_rows
        ]
    )

    billing_event = pd.DataFrame(
        [
            # CUS-000001: 1 settled invoice (3999) + 1 unsettled invoice (1999) with PAYMENT_FAILED on 2025-06-11
            {
                "billing_event_id": "BILL-SUB-CUS-000001-01-202503-01",
                "subscription_id": "SUB-CUS-000001-01",
                "related_event_id": None,
                "event_type": "INVOICE",
                "event_date": "2025-03-10",
                "due_date": "2025-03-17",
                "amount_cents": 3999,
                "status": "POSTED",
                "failure_reason": None,
            },
            {
                "billing_event_id": "BILL-SUB-CUS-000001-01-202503-02",
                "subscription_id": "SUB-CUS-000001-01",
                "related_event_id": "BILL-SUB-CUS-000001-01-202503-01",
                "event_type": "PAYMENT",
                "event_date": "2025-03-11",
                "due_date": None,
                "amount_cents": 3999,
                "status": "SETTLED",
                "failure_reason": None,
            },
            {
                "billing_event_id": "BILL-SUB-CUS-000001-02-202506-01",
                "subscription_id": "SUB-CUS-000001-02",
                "related_event_id": None,
                "event_type": "INVOICE",
                "event_date": "2025-06-10",
                "due_date": "2025-06-17",
                "amount_cents": 1999,
                "status": "POSTED",
                "failure_reason": None,
            },
            {
                "billing_event_id": "BILL-SUB-CUS-000001-02-202506-02",
                "subscription_id": "SUB-CUS-000001-02",
                "related_event_id": "BILL-SUB-CUS-000001-02-202506-01",
                "event_type": "PAYMENT_FAILED",
                "event_date": "2025-06-11",
                "due_date": None,
                "amount_cents": 1999,
                "status": "FAILED",
                "failure_reason": "INSUFFICIENT_FUNDS",
            },
        ]
    )

    support_case = pd.DataFrame(
        [
            {
                "case_id": "CASE-CUS-000001-0001",
                "customer_id": "CUS-000001",
                "subscription_id": "SUB-CUS-000001-02",
                "opened_at": "2025-05-20T10:00:00",
                "resolved_at": "2025-05-22T10:00:00",
                "category": "CANCELLATION_INQUIRY",
                "severity": "HIGH",
                "escalated": 0,
            }
        ]
    )

    tables = {
        "customer": customers,
        "subscription": subscriptions,
        "usage_snapshot": usage_snapshot,
        "billing_event": billing_event,
        "support_case": support_case,
    }

    feats = build_features(tables, as_of=date(2025, 7, 1), lookback_months=6)
    assert len(feats) == 2

    r1 = feats.iloc[0]
    assert r1["customer_id"] == "CUS-000001"
    assert r1["usage_minutes_prev3m"] == 600.0
    assert r1["usage_minutes_3m"] == 1500.0
    assert r1["usage_ratio_3m_vs_prev3m"] == 2.5
    assert r1["last_month_active_days"] == 21
    assert r1["usage_slope_6m"] == round(100.0 / 350.0, 6)
    assert r1["sessions_6m"] == 130
    assert r1["failed_payments_6m"] == 1
    assert r1["days_since_last_failed_payment"] == 20  # 2025-07-01 minus 2025-06-11
    assert r1["outstanding_balance_cents"] == 1999
    assert r1["support_cases_6m"] == 1
    assert r1["high_severity_cases_6m"] == 1
    assert r1["cancellation_inquiries_6m"] == 1
    assert r1["tenure_days"] == 365
    assert r1["plan_tier"] == "STANDARD"
    assert r1["monthly_price_cents"] == 1999
    assert r1["plan_downgrade_6m"] == 1
    assert r1["segment"] == "SMB"
    assert r1["channel"] == "PAID"
    assert r1["is_seasonal"] == 1

    r2 = feats.iloc[1]
    assert r2["customer_id"] == "CUS-000002"
    assert r2["usage_minutes_prev3m"] == 0.0
    assert r2["usage_minutes_3m"] == 450.0
    assert r2["usage_ratio_3m_vs_prev3m"] == 1.0  # short history (< 6m)
    assert r2["last_month_active_days"] == 11
    assert r2["usage_slope_6m"] == 0.0  # < 3 months of history
    assert r2["sessions_6m"] == 24
    assert r2["failed_payments_6m"] == 0
    assert pd.isna(r2["days_since_last_failed_payment"])
    assert r2["outstanding_balance_cents"] == 0
    assert r2["plan_downgrade_6m"] == 0
    assert r2["is_seasonal"] == 0

