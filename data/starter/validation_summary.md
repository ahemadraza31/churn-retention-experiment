# Validation Summary (scale=starter)

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
| `DET-A-LABEL-BEFORE-PREDICTION` | **FAIL** | `CRITICAL` | 10 | Churn outcome has churned=1 with churn_date strictly before prediction_date |
| `DET-B-INELIGIBLE-OFFER` | **FAIL** | `CRITICAL` | 10 | Campaign contact assigned to customer/offer failing one or more of ER-001..ER-007 |
| `DET-C-GROUP-LEAKAGE` | **FAIL** | `CRITICAL` | 10 | Customer assigned to both TREATMENT and CONTROL campaign contacts |
| `DET-D-MULTI-ATTRIBUTION` | **FAIL** | `HIGH` | 10 | Customer has multiple retained outcomes attributed to distinct non-null offers |

### `DET-A-LABEL-BEFORE-PREDICTION` (First 5 of 10)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `churn_outcome` | `CHURN-CUS-000050-2026` | `CUS-000050` | Churn outcome CHURN-CUS-000050-2026 for customer CUS-000050 has churn_date (2025-09-08) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-000094-2026` | `CUS-000094` | Churn outcome CHURN-CUS-000094-2026 for customer CUS-000094 has churn_date (2025-07-21) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-000098-2026` | `CUS-000098` | Churn outcome CHURN-CUS-000098-2026 for customer CUS-000098 has churn_date (2025-09-25) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-000118-2026` | `CUS-000118` | Churn outcome CHURN-CUS-000118-2026 for customer CUS-000118 has churn_date (2025-12-11) < prediction_date (2026-01-01) |
| `churn_outcome` | `CHURN-CUS-000205-2026` | `CUS-000205` | Churn outcome CHURN-CUS-000205-2026 for customer CUS-000205 has churn_date (2025-11-26) < prediction_date (2026-01-01) |

### `DET-B-INELIGIBLE-OFFER` (First 5 of 10)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `campaign_contact` | `CMP-CUS-000108-2026-W01` | `CUS-000108` | Campaign contact CMP-CUS-000108-2026-W01 for customer CUS-000108 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-005 |
| `campaign_contact` | `CMP-CUS-000161-2026-W01` | `CUS-000161` | Campaign contact CMP-CUS-000161-2026-W01 for customer CUS-000161 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-003 |
| `campaign_contact` | `CMP-CUS-000582-2026-W01` | `CUS-000582` | Campaign contact CMP-CUS-000582-2026-W01 for customer CUS-000582 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-002, ER-004 |
| `campaign_contact` | `CMP-CUS-000587-2026-W01` | `CUS-000587` | Campaign contact CMP-CUS-000587-2026-W01 for customer CUS-000587 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-004 |
| `campaign_contact` | `CMP-CUS-000597-2026-W01` | `CUS-000597` | Campaign contact CMP-CUS-000597-2026-W01 for customer CUS-000597 (offer=OFF-2026-000001, group=TREATMENT) failed eligibility: ER-004 |

### `DET-C-GROUP-LEAKAGE` (First 5 of 10)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `customer` | `CUS-000148` | `CUS-000148` | Customer CUS-000148 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000148-2026-W01', 'CMP-CUS-000148-2026-W02'] |
| `customer` | `CUS-000207` | `CUS-000207` | Customer CUS-000207 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000207-2026-W01', 'CMP-CUS-000207-2026-W02'] |
| `customer` | `CUS-000240` | `CUS-000240` | Customer CUS-000240 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000240-2026-W01', 'CMP-CUS-000240-2026-W02'] |
| `customer` | `CUS-000298` | `CUS-000298` | Customer CUS-000298 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000298-2026-W01', 'CMP-CUS-000298-2026-W02'] |
| `customer` | `CUS-000465` | `CUS-000465` | Customer CUS-000465 has campaign contacts in both TREATMENT and CONTROL groups: ['CMP-CUS-000465-2026-W01', 'CMP-CUS-000465-2026-W02'] |

### `DET-D-MULTI-ATTRIBUTION` (First 5 of 10)

| Entity Type | Entity ID | Customer ID | Message |
| :--- | :--- | :--- | :--- |
| `customer` | `CUS-000105` | `CUS-000105` | Customer CUS-000105 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
| `customer` | `CUS-000214` | `CUS-000214` | Customer CUS-000214 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
| `customer` | `CUS-000249` | `CUS-000249` | Customer CUS-000249 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000003'] |
| `customer` | `CUS-000254` | `CUS-000254` | Customer CUS-000254 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
| `customer` | `CUS-000437` | `CUS-000437` | Customer CUS-000437 has multiple retained outcomes with distinct attributed offers: ['OFF-2026-000001', 'OFF-2026-000002'] |
