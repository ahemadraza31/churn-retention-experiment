# Evaluation Report (`scale=full`)

## 1. Anomaly Exclusions (Pre-Evaluation Hygiene)

- **Total Unique Excluded Customers**: `160`

| Detector Rule ID | Excluded Customers |
| :--- | ---: |
| `DET-A-LABEL-BEFORE-PREDICTION` | 40 |
| `DET-B-INELIGIBLE-OFFER` | 40 |
| `DET-C-GROUP-LEAKAGE` | 40 |
| `DET-D-MULTI-ATTRIBUTION` | 40 |

## 2. Churn Risk Model Performance

### 2.1 In-Sample Training Summary (`P0 = 2025-07-01`, `label_type = in_sample`)

- **Model Version**: `logreg-v1` (`in_sample`)
- **Training Rows ($P_0$)**: `17726`
- **Training Positives (2025 180d)**: `723`
- **In-Sample ROC-AUC**: `0.655942`

#### Top 10 Standardized Logistic Regression Coefficients (by Absolute Magnitude)

| Rank | Feature | Coefficient | Sign | Absolute |
| ---: | :--- | ---: | :---: | ---: |
| 1 | `segment_CONSUMER` | -0.845048 | `-` | 0.845048 |
| 2 | `channel_REFERRAL` | -0.836316 | `-` | 0.836316 |
| 3 | `segment_SMB` | -0.716888 | `-` | 0.716888 |
| 4 | `plan_tier_BASIC` | -0.591492 | `-` | 0.591492 |
| 5 | `plan_tier_STANDARD` | -0.525066 | `-` | 0.525066 |
| 6 | `plan_tier_PREMIUM` | -0.445377 | `-` | 0.445377 |
| 7 | `channel_ORGANIC` | -0.434991 | `-` | 0.434991 |
| 8 | `last_month_active_days` | -0.383091 | `-` | 0.383091 |
| 9 | `channel_PARTNER` | -0.310328 | `-` | 0.310328 |
| 10 | `monthly_price_cents` | -0.249854 | `-` | 0.249854 |

### 2.2 Out-of-Time Evaluation on the Untreated Cohort (`P = 2026-01-01`, ADR-012)

Evaluated strictly on scored customers with a 2026 churn outcome who are **not** in the `TREATMENT` arm (i.e., `CONTROL` and uncontacted customers), excluding detector-flagged customers.

| Horizon Label | N | Positives | Base Rate | ROC-AUC | Brier Score | HIGH Band Precision | HIGH Band Recall | HIGH Band F1 | Precision Lift |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **180-Day (2026 Horizon)** | 15889 | 615 | 0.0387 | 0.599602 | 0.0364 | 0.0830 | 0.2325 | 0.1223 | 2.14x |
| **90-Day (Outcome Window)** | 15889 | 298 | 0.0188 | 0.670142 | — | 0.0592 | 0.3423 | 0.1009 | 3.16x |

## 3. Randomized Retention Experiment (Intention-to-Treat)

### 3.1 Program-Level ITT Lift (Primary 90-Day & Secondary 180-Day)

| Metric | Primary: 90-Day Retention | Secondary: 180-Day Retention |
| :--- | ---: | ---: |
| **Treatment Retained / N** | 2292 / 2354 (0.9737) | 2257 / 2354 (0.9588) |
| **Control Retained / N** | 2356 / 2433 (0.9684) | 2301 / 2433 (0.9457) |
| **Absolute Lift (pp)** | +0.53 pp (+0.0053) | +1.30 pp (+0.0130) |
| **95% CI (pp, unpooled)** | [-0.42, +1.48] pp | [+0.10, +2.51] pp |
| **Two-Sided p-value (pooled z)** | 0.2740 | 0.0345 |
| **Relative Lift** | +0.55% | +1.38% |
| **Incremental Retained Customers** | +12.50 ([-9.86, +34.86]) | +30.71 ([+2.32, +59.11]) |
| **Number Needed to Treat (NNT)** | 188.32 | 76.64 |

### 3.2 Exploratory Subgroup Breakdown by Planned Offer

| Planned Offer | Horizon | Treatment Retained / N | Control Retained / N | Lift (pp) | 95% CI (pp) | p-value | Incremental Retained |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `OFF-2026-000001` *(exploratory)* | 90d | 1113/1147 (0.9704) | 1152/1184 (0.9730) | -0.26 | [-1.61, +1.09] | 0.7035 | -3.00 |
| `OFF-2026-000001` *(exploratory)* | 180d | 1100/1147 (0.9590) | 1124/1184 (0.9493) | +0.97 | [-0.73, +2.67] | 0.2633 | +11.12 |
| `OFF-2026-000002` *(exploratory)* | 90d | 1122/1148 (0.9774) | 1153/1194 (0.9657) | +1.17 | [-0.18, +2.51] | 0.0898 | +13.42 |
| `OFF-2026-000002` *(exploratory)* | 180d | 1101/1148 (0.9591) | 1127/1194 (0.9439) | +1.52 | [-0.22, +3.25] | 0.0880 | +17.42 |
| `OFF-2026-000003` *(exploratory)* | 90d | 57/59 (0.9661) | 51/55 (0.9273) | +3.88 | [-4.39, +12.15] | 0.3535 | +2.29 |
| `OFF-2026-000003` *(exploratory)* | 180d | 56/59 (0.9492) | 50/55 (0.9091) | +4.01 | [-5.44, +13.45] | 0.4027 | +2.36 |

### 3.3 Exploratory Subgroup Breakdown by Risk Stratum

| Risk Stratum | Horizon | Treatment Retained / N | Control Retained / N | Lift (pp) | 95% CI (pp) | p-value | Incremental Retained |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `HIGH` *(exploratory)* | 90d | 937/980 (0.9561) | 972/1021 (0.9520) | +0.41 | [-1.42, +2.25] | 0.6604 | +4.03 |
| `HIGH` *(exploratory)* | 180d | 920/980 (0.9388) | 946/1021 (0.9265) | +1.22 | [-0.97, +3.42] | 0.2755 | +11.99 |
| `MEDIUM` *(exploratory)* | 90d | 1355/1374 (0.9862) | 1384/1412 (0.9802) | +0.60 | [-0.35, +1.55] | 0.2188 | +8.25 |
| `MEDIUM` *(exploratory)* | 180d | 1337/1374 (0.9731) | 1355/1412 (0.9596) | +1.34 | [+0.01, +2.68] | 0.0495 | +18.47 |

### 3.4 Randomization & Covariate Balance Check

| Covariate | Treatment Mean | Control Mean | Standardized Mean Diff (SMD) | Flagged (`SMD >= 0.10`) |
| :--- | ---: | ---: | ---: | :---: |
| `risk_score` | 0.0654 | 0.0645 | 0.019148 | `NO` |
| `tenure_days` | 663.3951 | 662.9712 | 0.001619 | `NO` |
| `monthly_price_cents` | 1634.0892 | 1627.0312 | 0.008248 | `NO` |

### 3.5 Correlation vs. Incremental Causal Comparison

| Metric | 90-Day Window | 180-Day Horizon |
| :--- | ---: | ---: |
| **(a) All TREATMENT Retention Rate** | 0.9737 | 0.9588 |
| **(b) TREATMENT Redeemers Only Retention Rate** (`n=824`) | 0.9769 | 0.9612 |
| **(c) CONTROL Retention Rate** | 0.9684 | 0.9457 |
| **(d) Attributed Retained Customers (Naive Count)** | 805 | 805 |
| **(e) Incremental Retained Customers (Causal ITT Lift)** | +12.50 | +30.71 |

> Metrics (a), (b), and (d) are not causal because customers who respond and redeem are self-selected and include many customers who would have stayed without any offer, whereas only the randomized ITT comparison against the withheld control group (e) isolates true incremental saves.

## 4. Financial Impact Analysis (Integer Cents)

- **Expected Margin Horizon**: `6` months
- **Average Expected 6-Month Margin per Treated Customer**: `6027` cents
- **Realized Offer Cost (`redeemed=1` & `retained_90d=1`, `n=805`)**: `827795` cents

| Financial Metric | Headline: 180-Day Lift Basis (6m Horizon) | Primary Endpoint: 90-Day Lift Basis |
| :--- | ---: | ---: |
| **Incremental Retained Customers** | +30.71 ([+2.32, +59.11]) | +12.50 ([-9.86, +34.86]) |
| **Gross Retention Benefit (cents)** | 185119 ([13989, 356235]) | 75336 ([-59432, 210104]) |
| **Realized Offer Cost (cents)** | 827795 | 827795 |
| **Net Financial Impact (cents)** | -642676 ([-813806, -471560]) | -752459 ([-887227, -617691]) |
| **Cost per Incremental Retained Customer (cents)** | 26951 | 66225 |

- **180-Day Financial Assessment**: For the 180d horizon, net financial impact is negative (-642676 cents; 95% CI [-813806, -471560] cents).
- **90-Day Financial Assessment**: For the 90d horizon, net financial impact is negative (-752459 cents; 95% CI [-887227, -617691] cents).

## 5. How to read this

1. **What Intention-to-Treat (ITT) Means**: Every eligible customer randomized into `TREATMENT` or `CONTROL` at `W01` (`2026-01-05`) is analyzed in their assigned arm regardless of whether delivery succeeded (`SENT` vs `DELIVERY_FAILED`) or whether the customer responded or redeemed. Comparing `TREATMENT` redeemers directly to `CONTROL` introduces severe selection bias because customers who open and redeem offers also have higher baseline retention propensity.
2. **Denominators and Time Windows**: Model evaluation uses the unflagged untreated cohort (`CONTROL` + uncontacted customers scored at `P = 2026-01-01`). Experiment evaluation uses unflagged eligible customers assigned at `2026-01-05`. The **90-day outcome window** (`2026-01-05` to `2026-04-05`) is the **primary experiment metric** (Decision D3), while the **180-day horizon** (`2026-01-01` to `2026-06-30`) is the **secondary experiment metric** and serves as the headline financial basis because expected gross margin is evaluated over 6 months.
3. **Subgroup Results are Exploratory**: Breakdowns by planned offer (`OFF-2026-000001..000003`) and risk stratum (`HIGH`, `MEDIUM`) have smaller sample sizes, wider confidence intervals, and no multiplicity adjustment; they should be read as directional and exploratory.
4. **Why Out-of-Time Model AUC is Modest**: In the data-generating process, observable behavioral decay (usage drop and elevated support/cancellation inquiries) manifests only during the final ~3 months prior to a voluntary churn event. Over a 180-day prediction window (`2026-01-01` to `2026-06-30`), customers who churn in the second half of the window (`April–June 2026`) have not yet begun their behavioral decay as of `P = 2026-01-01`, diluting 180-day signal.
5. **Known Limitations**:
   - Single campaign wave (`2026-W01`) on synthetic data.
   - Boundary plan-change exclusion: 5 customers at `P = 2026-01-01` and 12 customers at `P0 = 2025-07-01` (at full scale) are excluded from `build_features` because a plan change occurred exactly on the `as_of` date (`previous.end_date = as_of - 1 day`, `next.start_date = as_of`), and `build_features` strictly reads subscriptions with `start_date < as_of`.
   - Margin-rule constraint on Free Month offer: `OFF-2026-000003` (`1 free month`, cost = 100% of 1 month's price, max allowed = `0.25 * 6 * gross_margin_pct`) is mathematically eligible only for `PREMIUM` tier subscriptions (`gross_margin_pct = 0.70`, giving `1.05 >= 1.00`), whereas `BASIC` (`0.55`) and `STANDARD` (`0.62`) fail `ER-007` for `OFF-2026-000003`.
