-- Views for churn-retention-experiment

-- Latest state for each entity (subscription, campaign_contact, customer)
CREATE VIEW v_entity_current_state AS
SELECT se.entity_type, se.entity_id,
       MAX(se.event_ts) AS latest_ts,
       MAX(se.event_id) FILTER (WHERE se.event_ts = MAX(se.event_ts)) AS latest_event_id
FROM state_event se
GROUP BY se.entity_type, se.entity_id;

-- Subscription balance: invoiced minus settled (assume amount_cents positive for invoice, negative for payment etc.)
CREATE VIEW v_subscription_balance AS
SELECT be.subscription_id,
       SUM(CASE WHEN be.event_type = 'INVOICE' THEN be.amount_cents
                WHEN be.event_type = 'PAYMENT' THEN -be.amount_cents
                ELSE 0 END) AS balance_cents
FROM billing_event be
GROUP BY be.subscription_id;

-- Latest risk score per customer
CREATE VIEW v_latest_risk_score AS
SELECT rs.customer_id,
       rs.as_of_date,
       rs.score,
       rs.band,
       rs.rank
FROM risk_score rs
JOIN (
    SELECT customer_id, MAX(as_of_date) AS max_as_of
    FROM risk_score
    GROUP BY customer_id
) latest ON rs.customer_id = latest.customer_id AND rs.as_of_date = latest.max_as_of;

