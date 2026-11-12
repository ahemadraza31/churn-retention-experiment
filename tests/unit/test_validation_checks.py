"""Unit tests for validate_tables: zero findings on valid world and negative corruption tests."""

import pandas as pd
import pytest

from churnexp.config import load_config
from churnexp.generation.world import generate_world
from churnexp.validation.checks import validate_tables


@pytest.fixture(scope="module")
def valid_tables() -> dict[str, pd.DataFrame]:
    cfg = load_config("starter")
    world = generate_world(cfg)
    return world.tables


def _copy_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {k: df.copy(deep=True) for k, df in tables.items()}


def _fired_rules(report) -> set[str]:
    return {f.rule_id for f in report.findings}


def test_valid_starter_world_zero_findings(valid_tables):
    """A valid starter world gives zero findings across all validation rules."""
    report = validate_tables(valid_tables)
    assert report.findings == []
    assert report.passed is True
    assert report.has_critical_or_high is False
    for rs in report.rule_summaries:
        assert rs.status == "PASS"
        assert rs.finding_count == 0


def test_negative_duplicate_pk_row(valid_tables):
    """Corrupting a table with a duplicate PK row fires only STRUCT-PK-UNIQUE."""
    corrupted = _copy_tables(valid_tables)
    cust_df = corrupted["customer"]
    corrupted["customer"] = pd.concat([cust_df, cust_df.iloc[[0]]], ignore_index=True)

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"STRUCT-PK-UNIQUE"}
    assert report.has_critical_or_high is True


def test_negative_orphan_fk(valid_tables):
    """Corrupting a foreign key to a non-existent parent ID fires only STRUCT-FK."""
    corrupted = _copy_tables(valid_tables)
    # Point a support_case customer_id to a valid-format but non-existent customer
    corrupted["support_case"].loc[0, "customer_id"] = "CUS-999999"

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"STRUCT-FK"}
    assert report.has_critical_or_high is True


def test_negative_invalid_enum(valid_tables):
    """Corrupting an enum column with an unknown value fires only STRUCT-ENUM."""
    corrupted = _copy_tables(valid_tables)
    corrupted["customer"].loc[0, "segment"] = "ENTERPRISE"

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"STRUCT-ENUM"}
    assert report.has_critical_or_high is True


def test_negative_invalid_id_format(valid_tables):
    """Corrupting a PK with a malformed ID string fires only STRUCT-ID-FORMAT."""
    corrupted = _copy_tables(valid_tables)
    corrupted["state_event"].loc[0, "event_id"] = "EVT-BAD-1"

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"STRUCT-ID-FORMAT"}


def test_negative_end_date_before_start_date(valid_tables):
    """Corrupting a subscription so end_date < start_date fires only TEMP-SUB-DATES."""
    corrupted = _copy_tables(valid_tables)
    sub_df = corrupted["subscription"]
    # Pick a customer whose single active subscription has end_date=None and set end_date < start_date
    # Wait: if we set end_date on a last subscription, TEMP-CHURN-VS-SUB would treat it as churned!
    # Instead, set start_date > end_date on a single-subscription churned customer whose last usage/billing/support is before end_date.
    # Or set start_date of a subscription after its end_date while keeping end_date unchanged (and no usage/billing in between):
    # Find a subscription with end_date not null and set start_date = end_date + 1 day, and filter out its usage/billing so only TEMP-SUB-DATES fires.
    ended_subs = sub_df[sub_df["end_date"].notna()]
    target_idx = ended_subs.index[0]
    target_sid = str(sub_df.loc[target_idx, "subscription_id"])
    end_str = str(sub_df.loc[target_idx, "end_date"])
    # Remove usage and billing for this subscription so snapshot/billing window rules don't also fire
    corrupted["usage_snapshot"] = corrupted["usage_snapshot"][
        corrupted["usage_snapshot"]["subscription_id"] != target_sid
    ].reset_index(drop=True)
    corrupted["billing_event"] = corrupted["billing_event"][
        corrupted["billing_event"]["subscription_id"] != target_sid
    ].reset_index(drop=True)
    # Ensure sequence_no == 1 so TEMP-SUB-CHAIN doesn't compare start_date to prev_end + 1
    seq1_ended = sub_df[(sub_df["end_date"].notna()) & (sub_df["sequence_no"] == 1)]
    target_idx = seq1_ended.index[0]
    target_sid = str(sub_df.loc[target_idx, "subscription_id"])
    end_str = str(sub_df.loc[target_idx, "end_date"])
    corrupted["usage_snapshot"] = valid_tables["usage_snapshot"][
        valid_tables["usage_snapshot"]["subscription_id"] != target_sid
    ].reset_index(drop=True)
    corrupted["billing_event"] = valid_tables["billing_event"][
        valid_tables["billing_event"]["subscription_id"] != target_sid
    ].reset_index(drop=True)
    corrupted["subscription"].loc[target_idx, "start_date"] = "2026-12-31"
    assert "2026-12-31" > end_str

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"TEMP-SUB-DATES"}


def test_negative_sub_chain_gap(valid_tables):
    """Corrupting a follow-up subscription start_date to leave a gap fires only TEMP-SUB-CHAIN."""
    corrupted = _copy_tables(valid_tables)
    sub_df = corrupted["subscription"]
    seq2 = sub_df[sub_df["sequence_no"] == 2]
    target_idx = seq2.index[0]
    orig_start = str(sub_df.loc[target_idx, "start_date"])
    # Shift start_date 1 day earlier (overlapping previous subscription end_date, still within same YYYY-MM)
    from datetime import date, timedelta

    new_start = (date.fromisoformat(orig_start) - timedelta(days=1)).isoformat()
    corrupted["subscription"].loc[target_idx, "start_date"] = new_start

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"TEMP-SUB-CHAIN"}


def test_negative_snapshot_outside_subscription(valid_tables):
    """Moving a usage_snapshot to a month before its subscription starts fires only TEMP-SNAPSHOT-IN-SUB."""
    corrupted = _copy_tables(valid_tables)
    corrupted["usage_snapshot"].loc[0, "snapshot_month"] = "2020-01"

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"TEMP-SNAPSHOT-IN-SUB"}


def test_negative_event_after_churn(valid_tables):
    """Moving a support case opened_at after its customer's churn_date fires only TEMP-CHURN-VS-SUB."""
    corrupted = _copy_tables(valid_tables)
    churn_df = corrupted["churn_outcome"]
    churned_rows = churn_df[churn_df["churned"] == 1]
    target_cid = str(churned_rows.iloc[0]["customer_id"])
    churn_dt = str(churned_rows.iloc[0]["churn_date"])

    # Add or modify a support case for target_cid so opened_at is after churn_dt
    sup_df = corrupted["support_case"]
    cust_cases = sup_df[sup_df["customer_id"] == target_cid]
    if not cust_cases.empty:
        c_idx = cust_cases.index[0]
        corrupted["support_case"].loc[c_idx, "opened_at"] = "2026-12-15T10:00:00"
        corrupted["support_case"].loc[c_idx, "resolved_at"] = "2026-12-16T10:00:00"
    else:
        corrupted["support_case"].loc[0, "customer_id"] = target_cid
        corrupted["support_case"].loc[0, "opened_at"] = "2026-12-15T10:00:00"
        corrupted["support_case"].loc[0, "resolved_at"] = "2026-12-16T10:00:00"
    assert "2026-12-15" > churn_dt

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"TEMP-CHURN-VS-SUB"}


def test_negative_payment_amount_different_from_invoice(valid_tables):
    """Changing a PAYMENT amount_cents without changing its INVOICE fires REC-PAYMENT-AMOUNT (if balance also adjusted)."""
    corrupted = _copy_tables(valid_tables)
    bill_df = corrupted["billing_event"]
    # Pick a failed RETRY or PAYMENT_FAILED so v_subscription_balance is unaffected, or provide matching v_subscription_balance
    failed_idx = bill_df[bill_df["event_type"] == "PAYMENT_FAILED"].index[0]
    corrupted["billing_event"].loc[failed_idx, "amount_cents"] = 123456

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"REC-PAYMENT-AMOUNT"}


def test_negative_wrong_balance(valid_tables):
    """Providing a corrupted v_subscription_balance fires only REC-BALANCE."""
    corrupted = _copy_tables(valid_tables)
    bill_df = corrupted["billing_event"]
    invs = bill_df[bill_df["event_type"] == "INVOICE"].groupby("subscription_id")["amount_cents"].sum()
    pays = bill_df[bill_df["event_type"] == "PAYMENT"].groupby("subscription_id")["amount_cents"].sum()
    bal_series = invs.subtract(pays, fill_value=0).astype(int)
    bal_df = bal_series.reset_index()
    bal_df.columns = ["subscription_id", "balance_cents"]
    bal_df.loc[0, "balance_cents"] += 500
    corrupted["v_subscription_balance"] = bal_df

    report = validate_tables(corrupted)
    assert _fired_rules(report) == {"REC-BALANCE"}


def test_negative_missing_key_in_csv_copy(valid_tables):
    """Dropping a row from the CSV copy of customer fires only XFILE-ROWCOUNT-KEYS."""
    csv_copy = _copy_tables(valid_tables)
    csv_copy["customer"] = csv_copy["customer"].iloc[1:].reset_index(drop=True)

    report = validate_tables(valid_tables, csv_tables=csv_copy)
    assert _fired_rules(report) == {"XFILE-ROWCOUNT-KEYS"}

