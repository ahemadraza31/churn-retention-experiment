# Validation Summary (scale=full)

- **Overall Status**: `PASS`
- **Total Findings**: `0`
- **Critical / High Findings**: `0`

## Rule Results

| Rule ID | Status | Severity | Findings | Description |
| :--- | :--- | :--- | ---: | :--- |
| `STRUCT-PK-UNIQUE` | **PASS** | `CRITICAL` | 0 | Primary key uniqueness and non-nullness across all tables |
| `STRUCT-FK` | **PASS** | `CRITICAL` | 0 | Foreign key referential integrity across all tables (no orphans) |
| `STRUCT-ENUM` | **PASS** | `HIGH` | 0 | Allowed enum values on all constrained columns |
| `STRUCT-ID-FORMAT` | **PASS** | `HIGH` | 0 | Entity primary and foreign key ID regex format validity |
| `TEMP-SUB-DATES` | **PASS** | `HIGH` | 0 | Subscription end_date >= start_date |
| `TEMP-SUB-CHAIN` | **PASS** | `HIGH` | 0 | Subscription chain consecutive sequence_no, previous link, and next-day continuity |
| `TEMP-SNAPSHOT-IN-SUB` | **PASS** | `HIGH` | 0 | Usage snapshot month falls within subscription start/end window |
| `TEMP-BILLING-IN-SUB` | **PASS** | `HIGH` | 0 | Billing events fall within subscription active window |
| `TEMP-SUPPORT-ORDER` | **PASS** | `HIGH` | 0 | Support case resolved_at >= opened_at |
| `TEMP-CHURN-VS-SUB` | **PASS** | `CRITICAL` | 0 | No usage, billing, or support after churn date; churn date equals last subscription end_date |
| `TEMP-STATE-EVENT` | **PASS** | `HIGH` | 0 | State events per entity are time-ordered and follow allowed dictionary transitions |
| `REC-INVOICE-AMOUNT` | **PASS** | `HIGH` | 0 | Invoice amount_cents equals subscription monthly_price_cents |
| `REC-PAYMENT-AMOUNT` | **PASS** | `HIGH` | 0 | Payment/retry amount_cents equals its related invoice amount_cents |
| `REC-BALANCE` | **PASS** | `HIGH` | 0 | v_subscription_balance matches independent recomputation for all subscriptions |
| `REC-USAGE` | **PASS** | `MEDIUM` | 0 | Usage active_days == 0 iff usage_minutes == 0 and usage_pct_of_limit in [0, 1] |
| `DUP-NATURAL-KEYS` | **PASS** | `HIGH` | 0 | Natural keys unique: (subscription_id, snapshot_month), (customer_id, sequence_no), one INVOICE per sub/month |
| `XFILE-ROWCOUNT-KEYS` | **PASS** | `HIGH` | 0 | CSV and DB tables have identical row counts and primary key sets |
| `XFILE-JSON-CSV` | **PASS** | `MEDIUM` | 0 | JSON and CSV exports match in row counts, keys, and values |

No validation findings detected.

## Detected business-rule anomalies

| Detector ID | Status | Severity | Findings | Description |
| :--- | :--- | :--- | ---: | :--- |
| `DET-A-LABEL-BEFORE-PREDICTION` | **FAIL** | `CRITICAL` | 40 | Churn outcome has churned=1 with churn_date strictly before prediction_date |
| `DET-B-INELIGIBLE-OFFER` | **FAIL** | `CRITICAL` | 40 | Campaign contact assigned to customer/offer failing one or more of ER-001..ER-007 |
| `DET-C-GROUP-LEAKAGE` | **FAIL** | `CRITICAL` | 40 | Customer assigned to both TREATMENT and CONTROL campaign contacts |
| `DET-D-MULTI-ATTRIBUTION` | **FAIL** | `HIGH` | 40 | Customer has multiple retained outcomes attributed to distinct non-null offers |

### `DET-A-LABEL-BEFORE-PREDICTION` (First 5 of 40)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `churn_outcome` | `CHURN-CUS-002351-2026` | `CUS-002351` | Churn outcome CHURN-CUS-002351-2026 for customer CUS-002351 has churn_date (2025-07-07) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-002813-2026` | `CUS-002813` | Churn outcome CHURN-CUS-002813-2026 for customer CUS-002813 has churn_date (2025-08-23) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-003132-2026` | `CUS-003132` | Churn outcome CHURN-CUS-003132-2026 for customer CUS-003132 has churn_date (2025-11-10) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-003430-2026` | `CUS-003430` | Churn outcome CHURN-CUS-003430-2026 for customer CUS-003430 has churn_date (2025-10-01) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-003903-2026` | `CUS-003903` | Churn outcome CHURN-CUS-003903-2026 for customer CUS-003903 has churn_date (2025-07-22) < prediction_date (2026-01-01) |

### `DET-B-INELIGIBLE-OFFER` (First 5 of 40)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `campaign_contact` | `CMP-CUS-000108-2026-W01` | `CUS-000108` | Campaign contact CMP-CUS-000108-2026-W01 for customer CUS-000108 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-005 |
| `campaign_contact` | `CMP-CUS-001294-2026-W01` | `CUS-001294` | Campaign contact CMP-CUS-001294-2026-W01 for customer CUS-001294 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-005, ER-006 |
| `campaign_contact` | `CMP-CUS-001555-2026-W01` | `CUS-001555` | Campaign contact CMP-CUS-001555-2026-W01 for customer CUS-001555 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-005 |
| `campaign_contact` | `CMP-CUS-001637-2026-W01` | `CUS-001637` | Campaign contact CMP-CUS-001637-2026-W01 for customer CUS-001637 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-005 |
| `campaign_contact` | `CMP-CUS-002074-2026-W01` | `CUS-002074` | Campaign contact CMP-CUS-002074-2026-W01 for customer CUS-002074 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-002 |

### `DET-C-GROUP-LEAKAGE` (First 5 of 40)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `customer` | `CUS-000433` | `CUS-000433` | Customer CUS-000433 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000433-2026-W01', 'CMP-CUS-000433-2026-W02'] |
| `customer` | `CUS-000693` | `CUS-000693` | Customer CUS-000693 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000693-2026-W01', 'CMP-CUS-000693-2026-W02'] |
| `customer` | `CUS-001682` | `CUS-001682` | Customer CUS-001682 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-001682-2026-W01', 'CMP-CUS-001682-2026-W02'] |
| `customer` | `CUS-001795` | `CUS-001795` | Customer CUS-001795 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-001795-2026-W01', 'CMP-CUS-001795-2026-W02'] |
| `customer` | `CUS-002315` | `CUS-002315` | Customer CUS-002315 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-002315-2026-W01', 'CMP-CUS-002315-2026-W02'] |

### `DET-D-MULTI-ATTRIBUTION` (First 5 of 40)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `customer` | `CUS-000600` | `CUS-000600` | Customer CUS-000600 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
| `customer` | `CUS-001147` | `CUS-001147` | Customer CUS-001147 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
| `customer` | `CUS-001288` | `CUS-001288` | Customer CUS-001288 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
| `customer` | `CUS-001723` | `CUS-001723` | Customer CUS-001723 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000003'] |
| `customer` | `CUS-002322` | `CUS-002322` | Customer CUS-002322 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
