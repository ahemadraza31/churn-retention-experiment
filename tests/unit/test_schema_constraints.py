import pytest
import sqlite3
from churnexp.schema.db import create_database
from churnexp import ids as ids_mod

@pytest.fixture(scope="module")
def conn():
    return create_database()

def test_orphan_foreign_keys(conn):
    cur = conn.cursor()
    # subscription with nonexistent customer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) VALUES ('SUB-CUS-999999-01','CUS-999999',1,'BASIC',1000,0.5,'2025-01-01');"
        )
    # billing_event with nonexistent subscription (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO billing_event (billing_event_id, subscription_id, event_type, event_date, amount_cents, status) VALUES ('BILL-SUB-CUS-999999-01-202501-01','SUB-CUS-999999-01','INVOICE','2025-01-01',1000,'PAID');"
        )
    # support_case with nonexistent customer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO support_case (case_id, customer_id, subscription_id, opened_at, category, severity, escalated) VALUES ('CASE-CUS-999999-0001','CUS-999999','SUB-CUS-999999-01','2025-01-01','BILLING','LOW',0);"
        )
    # offer_eligibility_rule with nonexistent offer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO offer_eligibility_rule (offer_id, rule_id) VALUES ('OFF-9999-999999','ER-001');"
        )
    # campaign_contact with nonexistent offer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-999999-9999-W01','CUS-999999','OFF-9999-999999','TREATMENT','SENT','2025-01-01','2025-01-01','STRAT',0,0);"
        )
    # churn_outcome with nonexistent customer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO churn_outcome (churn_id, customer_id, cycle_year, prediction_date, horizon_end, churned) VALUES ('CHURN-CUS-999999-2025','CUS-999999',2025,'2025-01-01','2025-12-31',0);"
        )
    # retention_outcome with nonexistent campaign_contact (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO retention_outcome (retention_id, contact_id, customer_id, window_start, window_end, retained) VALUES ('RET-CMP-CUS-999999-9999-W01','CMP-CUS-999999-9999-W01','CUS-999999','2025-01-01','2025-01-31',1);"
        )
    # risk_score with nonexistent customer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO risk_score (score_id, customer_id, as_of_date, model_version, score, band, rank) VALUES ('RS-CUS-999999-2025-01-01','CUS-999999','2025-01-01','v1',0.5,'LOW',1);"
        )
    # feature_snapshot with nonexistent customer (valid ID format)
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO feature_snapshot (customer_id, as_of_date, window_start, window_end, usage_minutes_3m, usage_minutes_prev3m, usage_ratio_3m_vs_prev3m, last_month_active_days, usage_slope_6m, sessions_6m, failed_payments_6m, days_since_last_failed_payment, outstanding_balance_cents, support_cases_6m, high_severity_cases_6m, cancellation_inquiries_6m, tenure_days, plan_tier, monthly_price_cents, plan_downgrade_6m, segment, channel, is_seasonal) VALUES ('CUS-999999','2025-01-01','2025-01-01','2025-01-31',0,0,0,0,0,0,0,0,0,0,0,0,0,'BASIC',1000,0,'CONSUMER','ORGANIC',0);"
        )

def test_enum_bad_values(conn):
    cur = conn.cursor()
    # segment enum bad value
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000001','2025-01-01','UNKNOWN','ORGANIC','NA','STEADY',1);")
    # channel enum bad value
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000002','2025-01-01','CONSUMER','UNKNOWN','NA','STEADY',1);")
    # usage_pattern enum bad value
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000003','2025-01-01','CONSUMER','ORGANIC','NA','UNKNOWN',1);")
    # offer_type enum bad value
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2026-000001','Bad Offer','UNKNOWN',6,0.3,'2025-01-01','2025-06-30');")
    # campaign_contact experiment_group bad value — contact_id/offer_id format also invalid so error fires on PK CHECK
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000004','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2026-000004','Dummy','PERCENT_DISCOUNT',0.1,6,0.3,'2025-01-01','2025-06-30');")
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000004-2026-W01','CUS-000004','OFF-2026-000004','UNKNOWN','SENT','2025-01-01','2025-01-01','STRAT',0,0);")

def test_subscription_end_date_check(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000005','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    # end_date before start_date should fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date, end_date) VALUES ('SUB-CUS-000005-01','CUS-000005',1,'BASIC',1000,0.5,'2025-02-01','2025-01-01');")

def test_churn_outcome_checks(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000006','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    # churned=1 but missing churn_date/type should fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO churn_outcome (churn_id, customer_id, cycle_year, prediction_date, horizon_end, churned) VALUES ('CHURN-CUS-000006-2025','CUS-000006',2025,'2025-07-01','2025-12-31',1);")
    # churned=0 but churn_date provided should fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO churn_outcome (churn_id, customer_id, cycle_year, prediction_date, horizon_end, churned, churn_date, churn_type) VALUES ('CHURN-CUS-000006-2025-FAIL','CUS-000006',2025,'2025-07-01','2025-12-31',0,'2025-06-30','VOLUNTARY');")

def test_campaign_contact_checks(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000007','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2026-000007','Demo','PERCENT_DISCOUNT',0.1,6,0.3,'2025-01-01','2025-12-31');")

    # (a) CONTROL iff WITHHELD: WITHHELD + TREATMENT must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W01','CUS-000007','OFF-2026-000007','TREATMENT','WITHHELD','2025-01-01',NULL,'STRAT',0,0);")
    # (a) CONTROL iff WITHHELD: SENT + CONTROL must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W02','CUS-000007','OFF-2026-000007','CONTROL','SENT','2025-01-01','2025-01-01','STRAT',0,0);")
    # (a) DELIVERY_FAILED + CONTROL must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W03','CUS-000007','OFF-2026-000007','CONTROL','DELIVERY_FAILED','2025-01-01','2025-01-01','STRAT',0,0);")
    # (b) WITHHELD with sent_at IS NOT NULL must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W04','CUS-000007','OFF-2026-000007','CONTROL','WITHHELD','2025-01-01','2025-01-01','STRAT',0,0);")
    # (c) SENT with sent_at IS NULL must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W05','CUS-000007','OFF-2026-000007','TREATMENT','SENT','2025-01-01',NULL,'STRAT',0,0);")
    # (c) DELIVERY_FAILED with sent_at IS NULL must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W06','CUS-000007','OFF-2026-000007','TREATMENT','DELIVERY_FAILED','2025-01-01',NULL,'STRAT',0,0);")

    # Valid TREATMENT/SENT row must succeed
    cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W07','CUS-000007','OFF-2026-000007','TREATMENT','SENT','2025-01-01','2025-01-01','STRAT',0,0);")
    # Valid CONTROL/WITHHELD row must succeed
    cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000007-2026-W08','CUS-000007','OFF-2026-000007','CONTROL','WITHHELD','2025-01-01',NULL,'STRAT',0,0);")

def test_column_name_prohibited_substrings(conn):
    cur = conn.cursor()
    prohibited = ["issue_type", "ground_truth", "latent", "potential", "anomaly"]
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    for tbl in tables:
        cur.execute(f"PRAGMA table_info({tbl});")
        cols = [row[1] for row in cur.fetchall()]
        for col in cols:
            for bad in prohibited:
                assert bad not in col, f"Prohibited substring '{bad}' found in column '{col}' of table '{tbl}'"

def test_id_format_pk_check(conn):
    """Every ID built by churnexp.ids passes its table PK CHECK; a malformed ID fails."""
    cur = conn.cursor()

    # --- customer ---
    good_cust = ids_mod.customer_id(10)
    cur.execute(
        "INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) "
        f"VALUES ('{good_cust}','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-10','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")

    # --- subscription ---
    good_sub = ids_mod.subscription_id(good_cust, 1)
    cur.execute(
        "INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) "
        f"VALUES ('{good_sub}','{good_cust}',1,'BASIC',1000,0.5,'2025-01-01');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) "
            f"VALUES ('SUB-{good_cust}-1','{good_cust}',2,'BASIC',1000,0.5,'2025-01-01');"
        )

    # --- usage_snapshot ---
    good_snap = ids_mod.snapshot_id(good_sub, 2025, 6)
    cur.execute(
        "INSERT INTO usage_snapshot (snapshot_id, subscription_id, snapshot_month, period_end, active_days, sessions, usage_minutes) "
        f"VALUES ('{good_snap}','{good_sub}','2025-06','2025-06-30',20,100,500.0);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO usage_snapshot (snapshot_id, subscription_id, snapshot_month, period_end, active_days, sessions, usage_minutes) "
            f"VALUES ('SNAP-BAD','{good_sub}','2025-07','2025-07-31',20,100,500.0);"
        )

    # --- offer ---
    good_off = ids_mod.offer_id(2026, 10)
    cur.execute(
        "INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) "
        f"VALUES ('{good_off}','Good Offer','PERCENT_DISCOUNT',0.1,6,0.3,'2025-01-01','2025-12-31');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) "
            "VALUES ('OFF-26-000010','Bad','PERCENT_DISCOUNT',0.1,6,0.3,'2025-01-01','2025-12-31');"
        )

    # --- billing_event ---
    good_bill = ids_mod.billing_event_id(good_sub, 2025, 1, 1)
    cur.execute(
        "INSERT INTO billing_event (billing_event_id, subscription_id, event_type, event_date, amount_cents, status) "
        f"VALUES ('{good_bill}','{good_sub}','INVOICE','2025-01-15',1000,'PAID');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO billing_event (billing_event_id, subscription_id, event_type, event_date, amount_cents, status) "
            f"VALUES ('BILL-BAD','{good_sub}','INVOICE','2025-01-15',1000,'PAID');"
        )

    # --- support_case ---
    good_case = ids_mod.support_case_id(good_cust, 1)
    cur.execute(
        "INSERT INTO support_case (case_id, customer_id, subscription_id, opened_at, category, severity, escalated) "
        f"VALUES ('{good_case}','{good_cust}','{good_sub}','2025-01-01','BILLING','LOW',0);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO support_case (case_id, customer_id, subscription_id, opened_at, category, severity, escalated) "
            f"VALUES ('CASE-BAD','{good_cust}','{good_sub}','2025-01-01','BILLING','LOW',0);"
        )

    # --- churn_outcome ---
    good_churn = ids_mod.churn_outcome_id(good_cust, 2025)
    cur.execute(
        "INSERT INTO churn_outcome (churn_id, customer_id, cycle_year, prediction_date, horizon_end, churned) "
        f"VALUES ('{good_churn}','{good_cust}',2025,'2025-07-01','2025-12-31',0);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO churn_outcome (churn_id, customer_id, cycle_year, prediction_date, horizon_end, churned) "
            f"VALUES ('CHURN-BAD','{good_cust}',2025,'2025-07-01','2025-12-31',0);"
        )

    # --- campaign_contact ---
    good_cmp = ids_mod.campaign_contact_id(good_cust, 2026, 1)
    cur.execute(
        "INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) "
        f"VALUES ('{good_cmp}','{good_cust}','{good_off}','TREATMENT','SENT','2026-01-01','2026-01-02','HIGH',0,0);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) "
            f"VALUES ('CMP-BAD','{good_cust}','{good_off}','TREATMENT','SENT','2026-01-01','2026-01-02','HIGH',0,0);"
        )

    # --- retention_outcome ---
    good_ret = ids_mod.retention_outcome_id(good_cmp)
    cur.execute(
        "INSERT INTO retention_outcome (retention_id, contact_id, customer_id, window_start, window_end, retained) "
        f"VALUES ('{good_ret}','{good_cmp}','{good_cust}','2026-01-01','2026-06-30',1);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO retention_outcome (retention_id, contact_id, customer_id, window_start, window_end, retained) "
            f"VALUES ('RET-BAD','{good_cmp}','{good_cust}','2026-01-01','2026-06-30',1);"
        )

    # --- state_event ---
    good_evt = ids_mod.state_event_id(1)
    cur.execute(
        "INSERT INTO state_event (event_id, entity_type, entity_id, from_state, to_state, event_ts) "
        f"VALUES ('{good_evt}','CUSTOMER','{good_cust}','INIT','ACTIVE','2025-01-01T00:00:00');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            f"INSERT INTO state_event (event_id, entity_type, entity_id, from_state, to_state, event_ts) "
            f"VALUES ('EVT-1','CUSTOMER','{good_cust}','INIT','ACTIVE','2025-01-01T00:00:00');"
        )

    # --- eligibility_rule ---
    good_er = ids_mod.eligibility_rule_id(1)
    param_json = '{"min_days": 90}'
    cur.execute(
        "INSERT INTO eligibility_rule (rule_id, rule_code, rule_type, parameter_json, version, effective_from, effective_to) "
        f"VALUES ('{good_er}','TENURE','THRESHOLD','{param_json}','1.0','2025-01-01','2029-12-31');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO eligibility_rule (rule_id, rule_code, rule_type, parameter_json, version, effective_from, effective_to) "
            f"VALUES ('ER-1','TENURE','THRESHOLD','{param_json}','1.0','2025-01-01','2029-12-31');"
        )

