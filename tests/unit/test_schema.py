import pytest
import sqlite3
from churnexp.schema.db import create_database

@pytest.fixture(scope="module")
def conn():
    return create_database()

def test_tables_exist(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}
    expected = {
        "customer",
        "subscription",
        "usage_snapshot",
        "billing_event",
        "support_case",
        "offer",
        "eligibility_rule",
        "offer_eligibility_rule",
        "campaign_contact",
        "churn_outcome",
        "retention_outcome",
        "state_event",
        "risk_score",
        "feature_snapshot",
        "rule_evaluation",
    }
    assert expected.issubset(tables)

def test_foreign_keys_enforced(conn):
    cur = conn.cursor()
    # Insert a customer
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000001','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    # subscription with invalid customer_id should fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) VALUES ('SUB-CUS-000001-01','CUS-999999',1,'BASIC',1000,0.5,'2025-01-01');")

def test_unique_constraints(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000002','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    cur.execute("INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) VALUES ('SUB-CUS-000002-01','CUS-000002',1,'BASIC',1000,0.5,'2025-01-01');")
    # duplicate PK
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) VALUES ('SUB-CUS-000002-01','CUS-000002',2,'STANDARD',2000,0.6,'2025-02-01');")
    # duplicate UNIQUE(customer_id, sequence_no)
    cur.execute("INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) VALUES ('SUB-CUS-000002-02','CUS-000002',2,'STANDARD',2000,0.6,'2025-02-01');")
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO subscription (subscription_id, customer_id, sequence_no, plan_tier, monthly_price_cents, gross_margin_pct, start_date) VALUES ('SUB-CUS-000002-03','CUS-000002',2,'PREMIUM',3000,0.7,'2025-03-01');")

def test_enum_and_check_constraints(conn):
    cur = conn.cursor()
    # invalid segment enum
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000003','2025-01-01','UNKNOWN','ORGANIC','NA','STEADY',1);")
    # invalid offer_type combo (both fields null)
    cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000001','Test Offer','PERCENT_DISCOUNT',0.1,6,0.3,'2025-01-01','2025-06-30');")
    # valid percent discount offer (needs discount_pct)
    cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000003','Valid Percent','PERCENT_DISCOUNT',0.15,6,0.3,'2025-01-01','2025-06-30');")
    with pytest.raises(sqlite3.IntegrityError):
        # percent offer without discount_pct (NULL)
        cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, free_months, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000002','Bad','PERCENT_DISCOUNT',NULL,NULL,6,0.3,'2025-01-01','2025-06-30');")
    with pytest.raises(sqlite3.IntegrityError):
        # free-month offer with discount_pct (should be NULL)
        cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, free_months, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000004','BadFree','FREE_MONTH',0.1,1,6,0.3,'2025-01-01','2025-06-30');")
    with pytest.raises(sqlite3.IntegrityError):
        # percent offer with free_months not NULL
        cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, free_months, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000005','BadBoth','PERCENT_DISCOUNT',0.1,1,6,0.3,'2025-01-01','2025-06-30');")

def test_state_event_append_only(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO state_event (event_id, entity_type, entity_id, from_state, to_state, event_ts) VALUES ('EVT-000000001','CUSTOMER','CUS-000001','INIT','ACTIVE','2025-01-01T00:00:00');")
    # UPDATE should abort
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("UPDATE state_event SET to_state='INACTIVE' WHERE event_id='EVT-000000001';")
    # DELETE should abort
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("DELETE FROM state_event WHERE event_id='EVT-000000001';")

def test_anomaly_shapes_accepted(conn):
    cur = conn.cursor()
    # A) churn_outcome with churn_date earlier than prediction_date (allowed by DB)
    cur.execute("INSERT INTO customer (customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in) VALUES ('CUS-000010','2025-01-01','CONSUMER','ORGANIC','NA','STEADY',1);")
    cur.execute("INSERT INTO churn_outcome (churn_id, customer_id, cycle_year, prediction_date, horizon_end, churned, churn_date, churn_type) VALUES ('CHURN-CUS-000010-2025','CUS-000010',2025,'2025-07-01','2025-12-28',1,'2025-06-30','VOLUNTARY');")
    # B) SENT campaign_contact for a customer with open failed payment (no DB rule prevents)
    cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000010','Offer','PERCENT_DISCOUNT',0.1,6,0.5,'2025-01-01','2025-12-31');")
    cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000010-2025-W01','CUS-000010','OFF-2025-000010','TREATMENT','SENT','2025-01-02T00:00:00','2025-01-02T01:00:00','stratum1',0,0);")
    # C) same customer with TREATMENT and CONTROL contacts (allowed)
    cur.execute("INSERT INTO campaign_contact (contact_id, customer_id, offer_id, experiment_group, contact_status, assigned_at, sent_at, stratum, responded, redeemed) VALUES ('CMP-CUS-000010-2025-W02','CUS-000010','OFF-2025-000010','CONTROL','WITHHELD','2025-01-03T00:00:00',NULL,'stratum1',0,0);")
    # D) two retention_outcome rows for same customer with different attributed_offer_id (allowed)
    cur.execute("INSERT INTO retention_outcome (retention_id, contact_id, customer_id, attributed_offer_id, window_start, window_end, retained) VALUES ('RET-CMP-CUS-000010-2025-W01','CMP-CUS-000010-2025-W01','CUS-000010','OFF-2025-000010','2025-01-01','2025-01-31',1);")
    # Insert second offer to satisfy FK
    cur.execute("INSERT INTO offer (offer_id, offer_name, offer_type, discount_pct, duration_months, max_cost_share_of_margin, valid_from, valid_to) VALUES ('OFF-2025-000011','Second Offer','PERCENT_DISCOUNT',0.2,6,0.5,'2025-01-01','2025-12-31');")
    cur.execute("INSERT INTO retention_outcome (retention_id, contact_id, customer_id, attributed_offer_id, window_start, window_end, retained) VALUES ('RET-CMP-CUS-000010-2025-W02','CMP-CUS-000010-2025-W02','CUS-000010','OFF-2025-000011','2025-02-01','2025-02-28',0);")

