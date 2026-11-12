# Data Dictionary for churn-retention-experiment

This document describes every column of the 15 database tables defined in `src/churnexp/schema/schema.sql`.
Each table has a markdown table with the following columns:

- **Column** – exact column name as created in SQLite.
- **Type** – SQLite storage class (`INTEGER`, `REAL`, `TEXT`).
- **Required** – `Yes` if `NOT NULL` (or primary key), otherwise `No`.
- **Values** – allowed enum values or range, or `Any`.
- **Units** – for monetary or percentage fields.
- **Unique** – `Yes` if a `UNIQUE` constraint applies (including composite PKs).
- **Validation** – any `CHECK` clause description.
- **Relation** – foreign‑key reference if any.

---

## customer
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| customer_id | TEXT | Yes | `CUS-######` (GLOB) | – | Yes (PK) | `customer_id GLOB 'CUS-[0-9][0-9][0-9][0-9][0-9][0-9]'` | – |
| signup_date | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| segment | TEXT | Yes | `CONSUMER`, `SMB` | – | No | `segment IN ('CONSUMER','SMB')` | – |
| channel | TEXT | Yes | `ORGANIC`,`PAID`,`PARTNER`,`REFERRAL` | – | No | `channel IN ('ORGANIC','PAID','PARTNER','REFERRAL')` | – |
| region | TEXT | Yes | Any | – | No | – | – |
| usage_pattern | TEXT | Yes | `STEADY`,`SEASONAL` | – | No | `usage_pattern IN ('STEADY','SEASONAL')` | – |
| marketing_opt_in | INTEGER | Yes | 0,1 | – | No | `marketing_opt_in IN (0,1)` | – |

---

## subscription
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| subscription_id | TEXT | Yes | `SUB-CUS-######-##` | – | Yes (PK) | `subscription_id GLOB 'SUB-CUS-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9]'` | – |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| previous_subscription_id | TEXT | No | – | – | No | – | `subscription(subscription_id)` |
| sequence_no | INTEGER | Yes | – | – | No | – | – |
| plan_tier | TEXT | Yes | `BASIC`,`STANDARD`,`PREMIUM` | – | No | `plan_tier IN ('BASIC','STANDARD','PREMIUM')` | – |
| monthly_price_cents | INTEGER | Yes | – | cents | No | – | – |
| gross_margin_pct | REAL | Yes | 0‑1 | – | No | – | – |
| start_date | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| end_date | TEXT | No | YYYY‑MM‑DD | – | No | `end_date IS NULL OR end_date >= start_date` | – |
| end_reason | TEXT | No | `PLAN_CHANGE`,`VOLUNTARY_CANCEL`,`INVOLUNTARY_CANCEL` | – | No | – | – |

---

## usage_snapshot
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| snapshot_id | TEXT | Yes | `SNAP-SUB-CUS-######-##-YYYYMM` | – | Yes (PK) | GLOB pattern | – |
| subscription_id | TEXT | Yes | – | – | No | – | `subscription(subscription_id)` |
| snapshot_month | TEXT | Yes | `YYYY‑MM` | – | No | – | – |
| period_end | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| active_days | INTEGER | Yes | – | days | No | – | – |
| sessions | INTEGER | Yes | – | – | No | – | – |
| usage_minutes | REAL | Yes | – | minutes | No | – | – |
| features_used | INTEGER | Yes | 0‑8 | – | No | `features_used BETWEEN 0 AND 8` | – |
| usage_pct_of_limit | REAL | Yes | 0‑1 | – | No | `usage_pct_of_limit BETWEEN 0 AND 1` | – |

---

## billing_event
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| billing_event_id | TEXT | Yes | `BILL-SUB-######-YYYYMM-NN` | – | Yes (PK) | GLOB pattern | – |
| subscription_id | TEXT | Yes | – | – | No | – | `subscription(subscription_id)` |
| related_event_id | TEXT | No | – | – | No | – | `billing_event(billing_event_id)` |
| event_type | TEXT | Yes | `INVOICE`,`PAYMENT`,`PAYMENT_FAILED`,`RETRY`,`REFUND`,`CREDIT` | – | No | `event_type IN (...)` | – |
| event_date | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| due_date | TEXT | No | YYYY‑MM‑DD | – | No | – | – |
| amount_cents | INTEGER | Yes | – | cents | No | – | – |
| status | TEXT | Yes | Any | – | No | – | – |
| failure_reason | TEXT | No | Any | – | No | – | – |

---

## support_case
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| case_id | TEXT | Yes | `CASE-CUS-######-####` | – | Yes (PK) | GLOB pattern | – |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| subscription_id | TEXT | Yes | – | – | No | – | `subscription(subscription_id)` |
| opened_at | TEXT | Yes | YYYY‑MM‑DDTHH:MM:SS | – | No | – | – |
| resolved_at | TEXT | No | YYYY‑MM‑DDTHH:MM:SS | – | No | – | – |
| category | TEXT | Yes | `BILLING`,`TECHNICAL`,`CANCELLATION_INQUIRY`,`GENERAL` | – | No | `category IN (...)` | – |
| severity | TEXT | Yes | `LOW`,`MEDIUM`,`HIGH`,`CRITICAL` | – | No | `severity IN (...)` | – |
| escalated | INTEGER | Yes | 0,1 | – | No | `escalated IN (0,1)` | – |

Note: `support_case` lifecycle is stored directly in `opened_at`, `resolved_at`, and `escalated`, not in `state_event` (the `state_event` schema constraint only allows `SUBSCRIPTION`, `CAMPAIGN_CONTACT`, and `CUSTOMER`).

---

## offer
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| offer_id | TEXT | Yes | `OFF-YYYY-######` | – | Yes (PK) | GLOB pattern | – |
| offer_name | TEXT | Yes | Any | – | No | – | – |
| offer_type | TEXT | Yes | `PERCENT_DISCOUNT`,`FREE_MONTH` | – | No | `offer_type IN ('PERCENT_DISCOUNT','FREE_MONTH')` | – |
| discount_pct | REAL | No | 0‑1 | – | No | Set when `offer_type='PERCENT_DISCOUNT'` | – |
| free_months | INTEGER | No | – | months | No | Set when `offer_type='FREE_MONTH'` | – |
| duration_months | INTEGER | Yes | – | months | No | – | – |
| max_cost_share_of_margin | REAL | Yes | 0‑1 | – | No | `0 <= max_cost_share_of_margin <= 1` | – |
| valid_from | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| valid_to | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |

---

## eligibility_rule
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| rule_id | TEXT | Yes | `ER-###` | – | Yes (PK) | GLOB pattern | – |
| rule_code | TEXT | Yes | Any | – | No | – | – |
| rule_type | TEXT | Yes | Any | – | No | – | – |
| parameter_json | TEXT | Yes | JSON string | – | No | `json_valid(parameter_json)` | – |
| version | TEXT | Yes | Any | – | No | – | – |
| effective_from | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| effective_to | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |

---

## offer_eligibility_rule
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| offer_id | TEXT | Yes | – | – | Part of PK | – | `offer(offer_id)` |
| rule_id | TEXT | Yes | – | – | Part of PK | – | `eligibility_rule(rule_id)` |

---

## campaign_contact
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| contact_id | TEXT | Yes | `CMP-CUS-######-YYYY-W##` | – | Yes (PK) | GLOB pattern | – |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| offer_id | TEXT | Yes | – | – | No | – | `offer(offer_id)` |
| experiment_group | TEXT | Yes | `TREATMENT`,`CONTROL` | – | No | `experiment_group IN (...)` | – |
| contact_status | TEXT | Yes | `SENT`,`WITHHELD`,`DELIVERY_FAILED` | – | No | `contact_status IN (...)` | – |
| assigned_at | TEXT | Yes | YYYY‑MM‑DDTHH:MM:SS | – | No | – | – |
| sent_at | TEXT | No | YYYY‑MM‑DDTHH:MM:SS | – | No | – | – |
| stratum | TEXT | Yes | Any | – | No | – | – |
| responded | INTEGER | Yes | 0,1 | – | No | `responded IN (0,1)` | – |
| redeemed | INTEGER | Yes | 0,1 | – | No | `redeemed IN (0,1)` | – |
| **Checks** | – | – | – | – | – | See schema for cross‑column `CHECK` constraints. | – |

---

## churn_outcome
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| churn_id | TEXT | Yes | `CHURN-CUS-######-YYYY` | – | Yes (PK) | GLOB pattern | – |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| cycle_year | INTEGER | Yes | – | year | No | – | – |
| prediction_date | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| horizon_end | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| churned | INTEGER | Yes | 0,1 | – | No | – | – |
| churn_date | TEXT | No | YYYY‑MM‑DD | – | No | Must be NOT NULL when churned=1 | – |
| churn_type | TEXT | No | `VOLUNTARY`,`INVOLUNTARY` | – | No | Must be NOT NULL when churned=1 | – |

---

## retention_outcome
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| retention_id | TEXT | Yes | `RET-CMP-......` | – | Yes (PK) | GLOB pattern | – |
| contact_id | TEXT | Yes | – | – | No | – | `campaign_contact(contact_id)` |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| attributed_offer_id | TEXT | No | – | – | No | – | `offer(offer_id)` |
| window_start | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| window_end | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| retained | INTEGER | Yes | 0,1 | – | No | – | – |
| churned_at | TEXT | No | YYYY‑MM‑DD | – | No | – | – |

---

## state_event
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| event_id | TEXT | Yes | `EVT-##########` | – | Yes (PK) | GLOB pattern | – |
| entity_type | TEXT | Yes | `SUBSCRIPTION`,`CAMPAIGN_CONTACT`,`CUSTOMER` | – | No | `entity_type IN (...)` | – |
| entity_id | TEXT | Yes | – | – | No | – | – |
| from_state | TEXT | Yes | – | – | No | – | – |
| to_state | TEXT | Yes | – | – | No | – | – |
| event_ts | TEXT | Yes | YYYY‑MM‑DDTHH:MM:SS | – | No | – | – |
| reason_code | TEXT | No | Any | – | No | – | – |
| source | TEXT | No | Any | – | No | – | – |

---

## risk_score
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| score_id | TEXT | Yes | `RS-CUS-######-YYYYMM-DDDD` | – | Yes (PK) | GLOB pattern | – |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| as_of_date | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| model_version | TEXT | Yes | Any | – | No | – | – |
| score | REAL | Yes | 0‑1 | – | No | – | – |
| band | TEXT | Yes | `HIGH`,`MEDIUM`,`LOW` | – | No | `band IN (...)` | – |
| rank | INTEGER | Yes | – | – | No | – | – |

---

## feature_snapshot
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| customer_id | TEXT | Yes | – | – | Part of PK | – | `customer(customer_id)` |
| as_of_date | TEXT | Yes | – | – | Part of PK | – | – |
| window_start | TEXT | Yes | – | – | No | – | – |
| window_end | TEXT | Yes | – | – | No | – | – |
| usage_minutes_3m | REAL | Yes | – | minutes | No | – | – |
| usage_minutes_prev3m | REAL | Yes | – | minutes | No | – | – |
| usage_ratio_3m_vs_prev3m | REAL | Yes | – | – | No | – | – |
| last_month_active_days | INTEGER | Yes | – | days | No | – | – |
| usage_slope_6m | REAL | Yes | – | – | No | – | – |
| sessions_6m | INTEGER | Yes | – | – | No | – | – |
| failed_payments_6m | INTEGER | Yes | – | – | No | – | – |
| days_since_last_failed_payment | INTEGER | No | – | days | No | – | – |
| outstanding_balance_cents | INTEGER | Yes | – | cents | No | – | – |
| support_cases_6m | INTEGER | Yes | – | – | No | – | – |
| high_severity_cases_6m | INTEGER | Yes | – | – | No | – | – |
| cancellation_inquiries_6m | INTEGER | Yes | – | – | No | – | – |
| tenure_days | INTEGER | Yes | – | days | No | – | – |
| plan_tier | TEXT | Yes | `BASIC`,`STANDARD`,`PREMIUM` | – | No | – | – |
| monthly_price_cents | INTEGER | Yes | – | cents | No | – | – |
| plan_downgrade_6m | INTEGER | Yes | 0,1 | – | No | – | – |
| segment | TEXT | Yes | `CONSUMER`,`SMB` | – | No | – | – |
| channel | TEXT | Yes | `ORGANIC`,`PAID`,`PARTNER`,`REFERRAL` | – | No | – | – |
| is_seasonal | INTEGER | Yes | 0,1 | – | No | – | – |

---

## rule_evaluation
| Column | Type | Required | Values | Units | Unique | Validation | Relation |
|---|---|---|---|---|---|---|---|
| evaluation_id | TEXT | Yes | `RE-######` | – | Yes (PK) | GLOB pattern | – |
| customer_id | TEXT | Yes | – | – | No | – | `customer(customer_id)` |
| offer_id | TEXT | No | – | – | No | – | `offer(offer_id)` |
| rule_id | TEXT | Yes | – | – | No | – | `eligibility_rule(rule_id)` |
| as_of_date | TEXT | Yes | YYYY‑MM‑DD | – | No | – | – |
| passed | INTEGER | Yes | 0,1 | – | No | – | – |
| observed_value | TEXT | Yes | Any | – | No | – | – |
| threshold_value | TEXT | Yes | Any | – | No | – | – |

---

## Lifecycle States & Transitions

The `state_event` table records immutable state changes for three entity types (`SUBSCRIPTION`, `CAMPAIGN_CONTACT`, `CUSTOMER`).  The allowed transitions are encoded by the **append‑only** triggers defined in `schema.sql` (no `UPDATE` or `DELETE`).  The expected lifecycle for each entity is:

- **CUSTOMER**: `INIT → ACTIVE → (CHURNED | INACTIVE)`
- **SUBSCRIPTION**: `INIT → ACTIVE → (CANCELLED | EXPIRED)`
- **CAMPAIGN_CONTACT**: `INIT → ASSIGNED → (SENT | WITHHELD | DELIVERY_FAILED)`, with `SENT → RESPONDED → REDEEMED` when responded/redeemed.

Note: `support_case` lifecycle is stored in `opened_at`, `resolved_at`, and `escalated`, not in `state_event` (the schema only allows `SUBSCRIPTION`, `CAMPAIGN_CONTACT`, `CUSTOMER`).

These transitions are not enforced by foreign‑key constraints; they are enforced by business‑logic validation and the append‑only triggers.

## Business Rules (not enforced by DB)

| Rule | Description |
|------|-------------|
| **ADR‑007 – Experiment Design** | Eligible customers receive a *planned* offer, then are randomized 50/50 into `TREATMENT` or `CONTROL`.  `CONTROL` contacts have `contact_status = WITHHELD` but retain the planned offer for lift calculations. |
| **ADR‑002 & ADR‑006 – Anomaly Injection** | Four synthetic anomalies (A‑D) are injected into the data generation pipeline; they are **not** represented in the schema and are validated only by downstream audit scripts. |
| **Eligibility Rule Evaluation** | `offer_eligibility_rule` links offers to eligibility rules; the **logic** of each rule lives in `parameter_json` and is evaluated in Python, not in SQLite. |
| **Margin Rule** | Offers must satisfy `max_cost_share_of_margin ≤ margin_share` (computed at runtime). |
| **Hidden Potential Outcomes** | Each customer has hidden segments (`persuadable`, `sure‑thing`, `lost‑cause`) and hidden churn outcomes stored in the ground‑truth files; these are not present in the DB schema. |

## Ground‑Truth File Schemas

The ground‑truth data is emitted as **JSON Lines** files for each cycle.  Each line is a JSON object with the following canonical fields (additional optional fields may appear):

```json
{
  "customer_id": "CUS-000123",
  "segment": "CONSUMER",      // hidden segment
  "ground_truth": {
    "churn_if_untreated": 0,   // 0/1
    "churn_if_treated": 1,      // 0/1
    "potential_outcome": "persuadable"
  },
  "usage_profile": {
    "monthly_minutes": 1234,
    "sessions": 45,
    "failed_payments": 0,
    "latency": 0.12
  }
}
```

*Fields prefixed with `ground_truth` are **not** stored in the SQLite database but are used by the audit module to compute true lift.*

---

## IDs and Forbidden Columns

The following ID formats are enforced by `src/churnexp/ids.py` and the `GLOB` checks above:

- `customer_id`: `CUS-######`
- `subscription_id`: `SUB-CUS-######-##`
- `snapshot_id`: `SNAP-SUB-CUS-######-##-YYYYMM`
- `billing_event_id`: `BILL-SUB-######-YYYYMM-NN`
- `case_id`: `CASE-CUS-######-####`
- `offer_id`: `OFF-YYYY-######`
- `rule_id`: `ER-###`
- `contact_id`: `CMP-CUS-######-YYYY-W##`
- `churn_id`: `CHURN-CUS-######-YYYY`
- `retention_id`: `RET-CMP-......`
- `event_id`: `EVT-##########`
- `score_id`: `RS-CUS-######-YYYY-MMDD`
- `evaluation_id`: `RE-######`

No column name contains any of the prohibited substrings: `issue_type`, `ground_truth`, `latent`, `potential`, `anomaly`.

---

### Feature Snapshot Formulas (Run 2A)

For a given `as_of` date ($P_0 = \text{2025-07-01}$ or $P = \text{2026-01-01}$) with `lookback_months = 6`, `window_start` is the first day of the month 6 months before `as_of` and `window_end = as_of - 1 day`. Only records strictly prior to `as_of` are read:

- `usage_minutes_3m`: Sum of `usage_minutes` over the last 3 full calendar months before `as_of` ($M_{-3}, M_{-2}, M_{-1}$).
- `usage_minutes_prev3m`: Sum of `usage_minutes` over the previous 3 full calendar months ($M_{-6}, M_{-5}, M_{-4}$).
- `usage_ratio_3m_vs_prev3m`: `usage_minutes_3m / usage_minutes_prev3m`, or `1.0` when `usage_minutes_prev3m == 0` or the customer has fewer than 6 full months of usage history before `as_of`.
- `last_month_active_days`: `active_days` in $M_{-1}$ (`0` if no snapshot exists in $M_{-1}$).
- `usage_slope_6m`: Ordinary least-squares slope of monthly `usage_minutes` over the available months in the 6-month window divided by their mean (`0.0` if fewer than 3 months of history or mean is `0`).
- `sessions_6m`: Sum of `sessions` across snapshots in the 6-month window.
- `failed_payments_6m`: Count of `PAYMENT_FAILED` billing events with `window_start <= event_date < as_of`.
- `days_since_last_failed_payment`: `(as_of - max(event_date))` in days across all `PAYMENT_FAILED` events with `event_date < as_of` (`NULL` if none).
- `outstanding_balance_cents`: Sum of `INVOICE` amounts minus sum of `SETTLED` (`PAYMENT` / `RETRY`) amounts with `event_date < as_of`.
- `support_cases_6m`: Count of `support_case` rows with `window_start <= opened_at < as_of`.
- `high_severity_cases_6m`: Count of `support_case` rows with `window_start <= opened_at < as_of` and `severity IN ('HIGH', 'CRITICAL')`.
- `cancellation_inquiries_6m`: Count of `support_case` rows with `window_start <= opened_at < as_of` and `category == 'CANCELLATION_INQUIRY'`.
- `tenure_days`: `(as_of - signup_date)` in days.
- `plan_tier`, `monthly_price_cents`: Taken from the subscription active on `as_of`.
- `plan_downgrade_6m`: `1` if a subscription starting in `[window_start, as_of)` has a lower tier rank (`BASIC < STANDARD < PREMIUM`) than the immediately preceding subscription, else `0`.
- `segment`, `channel`, `is_seasonal`: Taken from `customer`.

### Eligibility & Margin Rule Formulas (Run 2A)

Evaluated at `assignment_date = 2026-01-05` for all customers scored at $P = \text{2026-01-01}$:

- **ER-001 (Active Subscription)**: `passed = 1` iff customer has a subscription with `start_date <= assignment_date` and (`end_date IS NULL` or `end_date >= assignment_date`) and `status == 'ACTIVE'`.
- **ER-002 (Minimum Tenure)**: `passed = 1` iff `(assignment_date - signup_date).days >= 90`.
- **ER-003 (Good Billing Standing)**: `passed = 1` iff no `INVOICE` issued before `assignment_date - 7 days` remains unsettled as of `assignment_date`.
- **ER-004 (No Prior Campaign Contact)**: `passed = 1` iff customer has no prior `campaign_contact` row within 180 days before `assignment_date`.
- **ER-005 (No Open Escalated Ticket)**: `passed = 1` iff customer has no `support_case` with `escalated == 1`, `opened_at < assignment_date`, and (`resolved_at IS NULL` or `resolved_at >= assignment_date`).
- **ER-006 (At-Risk Band)**: `passed = 1` iff `risk_band IN ('HIGH', 'MEDIUM')` at $P = \text{2026-01-01}$.
- **ER-007 (Margin Cap, per offer)**:
  - `expected_6m_margin_cents = round(6 * monthly_price_cents * gross_margin_pct)`
  - `offer_cost_cents = round(discount_pct * monthly_price_cents * duration_months)` for `PERCENT_DISCOUNT`, or `round(free_months * monthly_price_cents)` for `FREE_MONTH`
  - `max_allowed_cents = round(max_cost_share_of_margin * expected_6m_margin_cents)`
  - `passed = 1` iff `offer_cost_cents <= max_allowed_cents`.
- **Simulation Note**: In Run 2A, only `PERSUADABLE` voluntary churners who are `TREATMENT + SENT`, respond, redeem, and pass the offer save draw have their 2026 churn prevented (`saved_by_campaign = 1`); `SLEEPING_DOG` customers do not get induced churn in this run.


