# Evaluation Report (`scale=starter`)

## 1. Anomaly Exclusions (Pre-Evaluation Hygiene)

- **Total Unique Excluded Customers**: `40`

| Detector Rule ID | Excluded Customers |
| :--- | ---: |
| `DET-A-LABEL-BEFORE-PREDICTION` | 10 |
| `DET-B-INELIGIBLE-OFFER` | 10 |
| `DET-C-GROUP-LEAKAGE` | 10 |
| `DET-D-MULTI-ATTRIBUTION` | 10 |

## 2. Churn Risk Model Performance

### 2.1 In-Sample Training Summary (`P0 = 2025-07-01`, `label_type = in_sample`)

- **Model Version**: `logreg-v1` (`in_sample`)
- **Training Rows ($P_0$)**: `876`
- **Training Positives (2025 180d)**: `30`
- **In-Sample ROC-AUC**: `0.747518`

#### Top 10 Standardized Logistic Regression Coefficients (by Absolute Magnitude)

| Rank | Feature | Coefficient | Sign | Absolute |
| ---: | :--- | ---: | :---: | ---: |
| 1 | `last_month_active_days` | -0.543915 | `-` | 0.543915 |
| 2 | `channel_PARTNER` | -0.525485 | `-` | 0.525485 |
| 3 | `channel_ORGANIC` | 0.503076 | `+` | 0.503076 |
| 4 | `is_seasonal` | -0.371651 | `-` | 0.371651 |
| 5 | `sessions_6m` | 0.311548 | `+` | 0.311548 |
| 6 | `usage_minutes_3m` | -0.283770 | `-` | 0.283770 |
| 7 | `tenure_days` | -0.252920 | `-` | 0.252920 |
| 8 | `channel_PAID` | 0.252627 | `+` | 0.252627 |
| 9 | `support_cases_6m` | 0.239746 | `+` | 0.239746 |
| 10 | `channel_REFERRAL` | -0.239028 | `-` | 0.239028 |

### 2.2 Out-of-Time Evaluation on the Untreated Cohort (`P = 2026-01-01`, ADR-012)

Evaluated strictly on scored customers with a 2026 churn outcome who are **not** in the `TREATMENT` arm (i.e., `CONTROL` and uncontacted customers), excluding detector-flagged customers.

| Horizon Label | N | Positives | Base Rate | ROC-AUC | Brier Score | HIGH Band Precision | HIGH Band Recall | HIGH Band F1 | Precision Lift |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **180-Day (2026 Horizon)** | 795 | 34 | 0.0428 | 0.514725 | 0.0417 | 0.0460 | 0.1176 | 0.0661 | 1.08x |
| **90-Day (Outcome Window)** | 795 | 17 | 0.0214 | 0.521246 | — | 0.0230 | 0.1176 | 0.0385 | 1.08x |

## 3. Randomized Retention Experiment (Intention-to-Treat)

### 3.1 Program-Level ITT Lift (Primary 90-Day & Secondary 180-Day)

| Metric | Primary: 90-Day Retention | Secondary: 180-Day Retention |
| :--- | ---: | ---: |
| **Treatment Retained / N** | 91 / 92 (0.9891) | 90 / 92 (0.9783) |
| **Control Retained / N** | 107 / 111 (0.9640) | 105 / 111 (0.9459) |
| **Absolute Lift (pp)** | +2.52 pp (+0.0252) | +3.23 pp (+0.0323) |
| **95% CI (pp, unpooled)** | [-1.55, +6.58] pp | [-1.92, +8.39] pp |
| **Two-Sided p-value (pooled z)** | 0.2495 | 0.2388 |
| **Relative Lift** | +2.61% | +3.42% |
| **Incremental Retained Customers** | +2.32 ([-1.42, +6.05]) | +2.97 ([-1.77, +7.72]) |
| **Number Needed to Treat (NNT)** | 39.74 | 30.95 |

### 3.2 Exploratory Subgroup Breakdown by Planned Offer

| Planned Offer | Horizon | Treatment Retained / N | Control Retained / N | Lift (pp) | 95% CI (pp) | p-value | Incremental Retained |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `OFF-2026-000001` *(exploratory)* | 90d | 50/50 (1.0000) | 62/63 (0.9841) | +1.59 | [-1.50, +4.67] | 0.3709 | +0.79 |
| `OFF-2026-000001` *(exploratory)* | 180d | 49/50 (0.9800) | 61/63 (0.9683) | +1.17 | [-4.64, +6.99] | 0.6997 | +0.59 |
| `OFF-2026-000002` *(exploratory)* | 90d | 41/42 (0.9762) | 43/46 (0.9348) | +4.14 | [-4.35, +12.64] | 0.3516 | +1.74 |
| `OFF-2026-000002` *(exploratory)* | 180d | 41/42 (0.9762) | 42/46 (0.9130) | +6.31 | [-3.04, +15.67] | 0.2012 | +2.65 |
| `OFF-2026-000003` *(exploratory)* | 90d | 0/0 (0.0000) | 2/2 (1.0000) | -100.00 | [-100.00, -100.00] | 0.0000 | -0.00 |
| `OFF-2026-000003` *(exploratory)* | 180d | 0/0 (0.0000) | 2/2 (1.0000) | -100.00 | [-100.00, -100.00] | 0.0000 | -0.00 |

### 3.3 Exploratory Subgroup Breakdown by Risk Stratum

| Risk Stratum | Horizon | Treatment Retained / N | Control Retained / N | Lift (pp) | 95% CI (pp) | p-value | Incremental Retained |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `HIGH` *(exploratory)* | 90d | 39/39 (1.0000) | 46/47 (0.9787) | +2.13 | [-2.00, +6.25] | 0.3595 | +0.83 |
| `HIGH` *(exploratory)* | 180d | 38/39 (0.9744) | 45/47 (0.9574) | +1.69 | [-5.92, +9.30] | 0.6704 | +0.66 |
| `MEDIUM` *(exploratory)* | 90d | 52/53 (0.9811) | 61/64 (0.9531) | +2.80 | [-3.54, +9.14] | 0.4066 | +1.48 |
| `MEDIUM` *(exploratory)* | 180d | 52/53 (0.9811) | 60/64 (0.9375) | +4.36 | [-2.61, +11.33] | 0.2454 | +2.31 |

### 3.4 Randomization & Covariate Balance Check

| Covariate | Treatment Mean | Control Mean | Standardized Mean Diff (SMD) | Flagged (`SMD >= 0.10`) |
| :--- | ---: | ---: | ---: | :---: |
| `risk_score` | 0.0516 | 0.0525 | 0.034001 | `NO` |
| `tenure_days` | 631.7717 | 596.9009 | 0.135239 | `YES` |
| `monthly_price_cents` | 1738.1304 | 1800.8018 | 0.065672 | `NO` |

### 3.5 Correlation vs. Incremental Causal Comparison

| Metric | 90-Day Window | 180-Day Horizon |
| :--- | ---: | ---: |
| **(a) All TREATMENT Retention Rate** | 0.9891 | 0.9783 |
| **(b) TREATMENT Redeemers Only Retention Rate** (`n=27`) | 1.0000 | 0.9630 |
| **(c) CONTROL Retention Rate** | 0.9640 | 0.9459 |
| **(d) Attributed Retained Customers (Naive Count)** | 27 | 27 |
| **(e) Incremental Retained Customers (Causal ITT Lift)** | +2.32 | +2.97 |

> Metrics (a), (b), and (d) are not causal because customers who respond and redeem are self-selected and include many customers who would have stayed without any offer, whereas only the randomized ITT comparison against the withheld control group (e) isolates true incremental saves.

## 4. Financial Impact Analysis (Integer Cents)

- **Expected Margin Horizon**: `6` months
- **Average Expected 6-Month Margin per Treated Customer**: `6462` cents
- **Realized Offer Cost (`redeemed=1` & `retained_90d=1`, `n=27`)**: `28773` cents

| Financial Metric | Headline: 180-Day Lift Basis (6m Horizon) | Primary Endpoint: 90-Day Lift Basis |
| :--- | ---: | ---: |
| **Incremental Retained Customers** | +2.97 ([-1.77, +7.72]) | +2.32 ([-1.42, +6.05]) |
| **Gross Retention Benefit (cents)** | 19211 ([-11436, 49859]) | 14961 ([-9195, 39118]) |
| **Realized Offer Cost (cents)** | 28773 | 28773 |
| **Net Financial Impact (cents)** | -9562 ([-40209, 21086]) | -13812 ([-37968, 10345]) |
| **Cost per Incremental Retained Customer (cents)** | 9678 | 12427 |

- **180-Day Financial Assessment**: For the 180d horizon, point-estimate net financial impact is negative (-9562 cents) and the 95% confidence interval [-40209, 21086] cents includes zero.
- **90-Day Financial Assessment**: For the 90d horizon, point-estimate net financial impact is negative (-13812 cents) and the 95% confidence interval [-37968, 10345] cents includes zero.

## 5. How to read this

1. **What Intention-to-Treat (ITT) Means**: Every eligible customer randomized into `TREATMENT` or `CONTROL` at `W01` (`2026-01-05`) is analyzed in their assigned arm regardless of whether delivery succeeded (`SENT` vs `DELIVERY_FAILED`) or whether the customer responded or redeemed. Comparing `TREATMENT` redeemers directly to `CONTROL` introduces severe selection bias because customers who open and redeem offers also have higher baseline retention propensity.
2. **Denominators and Time Windows**: Model evaluation uses the unflagged untreated cohort (`CONTROL` + uncontacted customers scored at `P = 2026-01-01`). Experiment evaluation uses unflagged eligible customers assigned at `2026-01-05`. The **90-day outcome window** (`2026-01-05` to `2026-04-05`) is the **primary experiment metric** (Decision D3), while the **180-day horizon** (`2026-01-01` to `2026-06-30`) is the **secondary experiment metric** and serves as the headline financial basis because expected gross margin is evaluated over 6 months.
3. **Subgroup Results are Exploratory**: Breakdowns by planned offer (`OFF-2026-000001..000003`) and risk stratum (`HIGH`, `MEDIUM`) have smaller sample sizes, wider confidence intervals, and no multiplicity adjustment; they should be read as directional and exploratory.
4. **Why Out-of-Time Model AUC is Modest**: In the data-generating process, observable behavioral decay (usage drop and elevated support/cancellation inquiries) manifests only during the final ~3 months prior to a voluntary churn event. Over a 180-day prediction window (`2026-01-01` to `2026-06-30`), customers who churn in the second half of the window (`April–June 2026`) have not yet begun their behavioral decay as of `P = 2026-01-01`, diluting 180-day signal.
5. **Known Limitations**:
   - Single campaign wave (`2026-W01`) on synthetic data.
   - Boundary plan-change exclusion: 5 customers at `P = 2026-01-01` and 12 customers at `P0 = 2025-07-01` (at full scale) are excluded from `build_features` because a plan change occurred exactly on the `as_of` date (`previous.end_date = as_of - 1 day`, `next.start_date = as_of`), and `build_features` strictly reads subscriptions with `start_date < as_of`.
   - Margin-rule constraint on Free Month offer: `OFF-2026-000003` (`1 free month`, cost = 100% of 1 month's price, max allowed = `0.25 * 6 * gross_margin_pct`) is mathematically eligible only for `PREMIUM` tier subscriptions (`gross_margin_pct = 0.70`, giving `1.05 >= 1.00`), whereas `BASIC` (`0.55`) and `STANDARD` (`0.62`) fail `ER-007` for `OFF-2026-000003`.
