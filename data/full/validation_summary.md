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
