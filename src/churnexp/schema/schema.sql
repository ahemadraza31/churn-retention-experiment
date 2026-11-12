/* SQLite schema for churn-retention-experiment */
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

-- Customer
CREATE TABLE customer (
    customer_id TEXT PRIMARY KEY CHECK (customer_id GLOB 'CUS-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    signup_date TEXT NOT NULL,               -- DATE 'YYYY-MM-DD'
    segment TEXT NOT NULL CHECK (segment IN ('CONSUMER','SMB')),
    channel TEXT NOT NULL CHECK (channel IN ('ORGANIC','PAID','PARTNER','REFERRAL')),
    region TEXT NOT NULL,
    usage_pattern TEXT NOT NULL CHECK (usage_pattern IN ('STEADY','SEASONAL')),
    marketing_opt_in INTEGER NOT NULL CHECK (marketing_opt_in IN (0,1))
);

-- Subscription
CREATE TABLE subscription (
    subscription_id TEXT PRIMARY KEY CHECK (subscription_id GLOB 'SUB-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    customer_id TEXT NOT NULL,
    previous_subscription_id TEXT,
    sequence_no INTEGER NOT NULL,
    plan_tier TEXT NOT NULL CHECK (plan_tier IN ('BASIC','STANDARD','PREMIUM')),
    monthly_price_cents INTEGER NOT NULL,
    gross_margin_pct REAL NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    end_reason TEXT CHECK (end_reason IN ('PLAN_CHANGE','VOLUNTARY_CANCEL','INVOLUNTARY_CANCEL')),
    UNIQUE(customer_id, sequence_no),
    CHECK (end_date IS NULL OR end_date >= start_date),
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY(previous_subscription_id) REFERENCES subscription(subscription_id)
);

-- Usage Snapshot
CREATE TABLE usage_snapshot (
    snapshot_id TEXT PRIMARY KEY CHECK (snapshot_id GLOB 'SNAP-SUB-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    subscription_id TEXT NOT NULL,
    snapshot_month TEXT NOT NULL,               -- 'YYYY-MM'
    period_end TEXT NOT NULL,
    active_days INTEGER NOT NULL,
    sessions INTEGER NOT NULL,
    usage_minutes REAL NOT NULL,
    features_used INTEGER NOT NULL CHECK (features_used BETWEEN 0 AND 8),
    usage_pct_of_limit REAL NOT NULL CHECK (usage_pct_of_limit BETWEEN 0 AND 1),
    UNIQUE(subscription_id, snapshot_month),
    FOREIGN KEY(subscription_id) REFERENCES subscription(subscription_id)
);

-- Billing Event
CREATE TABLE billing_event (
    billing_event_id TEXT PRIMARY KEY CHECK (billing_event_id GLOB 'BILL-SUB-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    subscription_id TEXT NOT NULL,
    related_event_id TEXT,
    event_type TEXT NOT NULL CHECK (event_type IN ('INVOICE','PAYMENT','PAYMENT_FAILED','RETRY','REFUND','CREDIT')),
    event_date TEXT NOT NULL,
    due_date TEXT,
    amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL,
    failure_reason TEXT,
    FOREIGN KEY(subscription_id) REFERENCES subscription(subscription_id),
    FOREIGN KEY(related_event_id) REFERENCES billing_event(billing_event_id)
);

-- Support Case
CREATE TABLE support_case (
    case_id TEXT PRIMARY KEY CHECK (case_id GLOB 'CASE-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
    customer_id TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    resolved_at TEXT,
    category TEXT NOT NULL CHECK (category IN ('BILLING','TECHNICAL','CANCELLATION_INQUIRY','GENERAL')),
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    escalated INTEGER NOT NULL CHECK (escalated IN (0,1)),
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY(subscription_id) REFERENCES subscription(subscription_id)
);

-- Offer
CREATE TABLE offer (
    offer_id TEXT PRIMARY KEY CHECK (offer_id GLOB 'OFF-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    offer_name TEXT NOT NULL,
    offer_type TEXT NOT NULL CHECK (offer_type IN ('PERCENT_DISCOUNT','FREE_MONTH')),
    discount_pct REAL,
    free_months INTEGER,
    duration_months INTEGER NOT NULL,
    max_cost_share_of_margin REAL NOT NULL CHECK (max_cost_share_of_margin >= 0 AND max_cost_share_of_margin <= 1),
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL,
    CHECK (
        (offer_type = 'PERCENT_DISCOUNT' AND discount_pct NOT NULL AND discount_pct > 0 AND discount_pct <= 1 AND free_months IS NULL) OR
        (offer_type = 'FREE_MONTH' AND free_months NOT NULL AND free_months > 0 AND discount_pct IS NULL)
    )
);

-- Eligibility Rule
CREATE TABLE eligibility_rule (
    rule_id TEXT PRIMARY KEY CHECK (rule_id GLOB 'ER-[0-9][0-9][0-9]'),
    rule_code TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    parameter_json TEXT NOT NULL CHECK (json_valid(parameter_json)),
    version TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT NOT NULL
);

-- Offer Eligibility Rule (junction)
CREATE TABLE offer_eligibility_rule (
    offer_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    PRIMARY KEY (offer_id, rule_id),
    FOREIGN KEY (offer_id) REFERENCES offer(offer_id),
    FOREIGN KEY (rule_id) REFERENCES eligibility_rule(rule_id)
);

-- Campaign Contact
CREATE TABLE campaign_contact (
    contact_id TEXT PRIMARY KEY CHECK (contact_id GLOB 'CMP-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-W[0-9][0-9]'),
    customer_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    experiment_group TEXT NOT NULL CHECK (experiment_group IN ('TREATMENT','CONTROL')),
    contact_status TEXT NOT NULL CHECK (contact_status IN ('SENT','WITHHELD','DELIVERY_FAILED')),
    assigned_at TEXT NOT NULL,
    sent_at TEXT,
    stratum TEXT NOT NULL,
    responded INTEGER NOT NULL CHECK (responded IN (0,1)),
    redeemed INTEGER NOT NULL CHECK (redeemed IN (0,1)),
    -- (a) CONTROL iff WITHHELD
    CHECK (
        (experiment_group = 'CONTROL' AND contact_status = 'WITHHELD') OR
        (experiment_group = 'TREATMENT' AND contact_status != 'WITHHELD')
    ),
    -- (b) WITHHELD requires sent_at IS NULL
    CHECK (contact_status != 'WITHHELD' OR sent_at IS NULL),
    -- (c) SENT or DELIVERY_FAILED requires TREATMENT and sent_at IS NOT NULL
    CHECK (
        contact_status NOT IN ('SENT','DELIVERY_FAILED') OR
        (experiment_group = 'TREATMENT' AND sent_at IS NOT NULL)
    ),
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY(offer_id) REFERENCES offer(offer_id)
);

-- Churn Outcome
CREATE TABLE churn_outcome (
    churn_id TEXT PRIMARY KEY CHECK (churn_id GLOB 'CHURN-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
    customer_id TEXT NOT NULL,
    cycle_year INTEGER NOT NULL,
    prediction_date TEXT NOT NULL,
    horizon_end TEXT NOT NULL,
    churned INTEGER NOT NULL CHECK (churned IN (0,1)),
    churn_date TEXT,
    churn_type TEXT CHECK (churn_type IN ('VOLUNTARY','INVOLUNTARY')),
    UNIQUE(customer_id, cycle_year),
    CHECK (churned = 1 AND churn_date IS NOT NULL AND churn_type IS NOT NULL OR churned = 0 AND churn_date IS NULL AND churn_type IS NULL),
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id)
);

-- Retention Outcome
CREATE TABLE retention_outcome (
    retention_id TEXT PRIMARY KEY CHECK (retention_id GLOB 'RET-CMP-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-W[0-9][0-9]'),
    contact_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    attributed_offer_id TEXT,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    retained INTEGER NOT NULL CHECK (retained IN (0,1)),
    churned_at TEXT,
    UNIQUE(contact_id),
    FOREIGN KEY(contact_id) REFERENCES campaign_contact(contact_id),
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY(attributed_offer_id) REFERENCES offer(offer_id)
);

-- State Event (append‑only)
CREATE TABLE state_event (
    event_id TEXT PRIMARY KEY CHECK (event_id GLOB 'EVT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('SUBSCRIPTION','CAMPAIGN_CONTACT','CUSTOMER')),
    entity_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    event_ts TEXT NOT NULL,
    reason_code TEXT,
    source TEXT
);

-- Prevent UPDATE/DELETE on state_event (append‑only)
CREATE TRIGGER state_event_no_update BEFORE UPDATE ON state_event BEGIN SELECT RAISE(ABORT, 'state_event is append‑only'); END;
CREATE TRIGGER state_event_no_delete BEFORE DELETE ON state_event BEGIN SELECT RAISE(ABORT, 'state_event is append‑only'); END;

-- Risk Score
CREATE TABLE risk_score (
    score_id TEXT PRIMARY KEY CHECK (score_id GLOB 'RS-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
    customer_id TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    model_version TEXT NOT NULL,
    score REAL NOT NULL,
    band TEXT NOT NULL CHECK (band IN ('HIGH','MEDIUM','LOW')),
    rank INTEGER NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id)
);

-- Feature Snapshot
CREATE TABLE feature_snapshot (
    customer_id TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    usage_minutes_3m REAL NOT NULL,
    usage_minutes_prev3m REAL NOT NULL,
    usage_ratio_3m_vs_prev3m REAL NOT NULL,
    last_month_active_days INTEGER NOT NULL,
    usage_slope_6m REAL NOT NULL,
    sessions_6m INTEGER NOT NULL,
    failed_payments_6m INTEGER NOT NULL,
    days_since_last_failed_payment INTEGER,
    outstanding_balance_cents INTEGER NOT NULL,
    support_cases_6m INTEGER NOT NULL,
    high_severity_cases_6m INTEGER NOT NULL,
    cancellation_inquiries_6m INTEGER NOT NULL,
    tenure_days INTEGER NOT NULL,
    plan_tier TEXT NOT NULL CHECK (plan_tier IN ('BASIC','STANDARD','PREMIUM')),
    monthly_price_cents INTEGER NOT NULL,
    plan_downgrade_6m INTEGER NOT NULL CHECK (plan_downgrade_6m IN (0,1)),
    segment TEXT NOT NULL CHECK (segment IN ('CONSUMER','SMB')),
    channel TEXT NOT NULL CHECK (channel IN ('ORGANIC','PAID','PARTNER','REFERRAL')),
    is_seasonal INTEGER NOT NULL CHECK (is_seasonal IN (0,1)),
    PRIMARY KEY (customer_id, as_of_date),
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id)
);

-- Rule Evaluation
CREATE TABLE rule_evaluation (
    evaluation_id TEXT PRIMARY KEY CHECK (evaluation_id GLOB 'RE-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    customer_id TEXT NOT NULL,
    offer_id TEXT,
    rule_id TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK (passed IN (0,1)),
    observed_value TEXT NOT NULL,
    threshold_value TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY(offer_id) REFERENCES offer(offer_id),
    FOREIGN KEY(rule_id) REFERENCES eligibility_rule(rule_id)
);

-- Indexes on FK columns
CREATE INDEX idx_subscription_customer_id ON subscription(customer_id);
CREATE INDEX idx_subscription_previous_id ON subscription(previous_subscription_id);
CREATE INDEX idx_usage_snapshot_subscription_id ON usage_snapshot(subscription_id);
CREATE INDEX idx_billing_event_subscription_id ON billing_event(subscription_id);
CREATE INDEX idx_billing_event_related_id ON billing_event(related_event_id);
CREATE INDEX idx_support_case_customer_id ON support_case(customer_id);
CREATE INDEX idx_support_case_subscription_id ON support_case(subscription_id);
CREATE INDEX idx_offer_eligibility_rule_offer_id ON offer_eligibility_rule(offer_id);
CREATE INDEX idx_offer_eligibility_rule_rule_id ON offer_eligibility_rule(rule_id);
CREATE INDEX idx_campaign_contact_customer_id ON campaign_contact(customer_id);
CREATE INDEX idx_campaign_contact_offer_id ON campaign_contact(offer_id);
CREATE INDEX idx_churn_outcome_customer_id ON churn_outcome(customer_id);
CREATE INDEX idx_retention_outcome_contact_id ON retention_outcome(contact_id);
CREATE INDEX idx_retention_outcome_customer_id ON retention_outcome(customer_id);
CREATE INDEX idx_retention_outcome_attributed_offer_id ON retention_outcome(attributed_offer_id);
CREATE INDEX idx_risk_score_customer_id ON risk_score(customer_id);
CREATE INDEX idx_risk_score_customer_asof ON risk_score(customer_id, as_of_date);
CREATE INDEX idx_rule_evaluation_customer_id ON rule_evaluation(customer_id);
CREATE INDEX idx_rule_evaluation_offer_id ON rule_evaluation(offer_id);
CREATE INDEX idx_rule_evaluation_rule_id ON rule_evaluation(rule_id);
CREATE INDEX idx_rule_evaluation_asof ON rule_evaluation(customer_id, as_of_date);

