# Phase 1: Requirements Specification

## 1. Executive Summary & Problem Context

In subscription-based businesses, reducing customer churn is a primary driver of enterprise value and unit economics. However, traditional churn mitigation programs face critical failure modes:
1. **Correlation vs. Causation Illusion**: Naive retention reporting ("customers who received discounts had a 90% retention rate") routinely confuses natural retention with treatment efficacy. In reality, many recipients were "sure things" who would have remained anyway, wasting budget without driving incremental retention.
2. **Data Leakage in Predictive Features**: Machine learning features frequently incorporate subtle lookahead signals (e.g., billing failures or support escalations occurring after the nominal prediction date), leading to inflated backtest performance that degrades completely in production.
3. **Financial Margin Dilution**: Indiscriminate discounting damages unit economics when the cost of retention offers exceeds the expected customer lifetime value or gross margin.
4. **Data Corruption & Quality Gaps**: Real-world operations suffer from temporal inversions, invalid overrides of eligibility, duplicate assignments, and untracked attribution.

The goal of this project is to construct an end-to-end, scientifically honest, and fully reproducible **Churn Detection and Retention Offer Experiment** system implemented as a modular Python monolith (`churnexp`).

---

## 2. Approved Foundational Decisions (D1 - D9)

The following core decisions have been formally approved and govern all system behavior:

- **D1 (Timeline)**: Observation and generation span January 2025 to June 2026 (18 months total). The production prediction cut-off date is **2026-01-01**.
- **D2 (Churn Label Horizon)**: The churn prediction horizon is fixed at **180 days** following the prediction date.
- **D3 (Retention Window)**: The campaign contact outcome window is **90 days** post-assignment.
- **D4 (Baseline Churn Distribution)**: Overall annualized churn rate is modeled at approximately **12%** across the 18-month simulation, strictly maintained within realistic enterprise boundaries of **5% to 20%**.
- **D5 (Experiment Split)**: Eligible high-risk subscribers are split **50/50** between Treatment and Control, stratified by risk score band.
- **D6 (Anomaly Injection Scale)**: Approximately **40 injected records per anomaly type** are parameterized and introduced into the post-assignment data.
- **D7 (Ground Truth Isolation)**: Anomaly labels and latent potential outcomes reside exclusively in an isolated `ground_truth/` directory. No production database table or CSV export contains an `issue_type` or cheat column.
- **D8 (Offer Catalogue)**: Three distinct retention offers are modeled:
  1. 10% discount for 6 months
  2. 20% discount for 3 months
  3. 1 free month
  Each offer has configured duration and maximum allowable cost share of expected 6-month gross margin.
- **D9 (Repository Data Footprint)**: A lightweight starter dataset (1,000 subscribers) is committed to Git across CSV, JSON, and SQLite formats. The full 20,000-subscriber dataset is generated deterministically via CLI and committed if the CSV aggregate is under 50 MB, otherwise verified through committed SHA-256 manifests.

---

## 3. Operational Timeline & Chronological Scope

```
Jan 2025          Jul 2025                     Dec 2025   Jan 2026                    Jun 2026
|--------------------|----------------------------|----------|---------------------------|
|<- 6m Train Lookback|<- 180d Train Churn Horizon>|          |                           |
|                    P0: 2025-07-01 (Train Cutoff)|          |                           |
|                                                            P: 2026-01-01 (Score Cutoff)|
|                                 <- 6m Scoring Lookback ->  |<- 180d Score Churn Horizon>|
|                                                            |<- 90d Retention Window -->|
```

- **Training Cutoff ($P_0 = \text{2025-07-01}$)**: Features look back across $[2025-01-01, 2025-06-30]$. Churn labels are evaluated over $[2025-07-01, 2025-12-28]$. All labels for $P_0$ are completely known and resolved prior to $P$.
- **Scoring Cutoff ($P = \text{2026-01-01}$)**: Features look back across $[2025-07-01, 2025-12-31]$. The model trained at $P_0$ is evaluated and produces risk scores at $P$. No event occurring on or after $P$ is accessible.
- **Post-Prediction Simulation ($[2026-01-01, 2026-06-30]$)**: Retention campaign contacts, redemptions, counterfactual churn/retention events, and operational anomalies are simulated.

---

## 4. Cohort Scales & Data Volume Requirements

| Parameter | Starter Scale (`--scale starter`) | Full Production Scale (`--scale full`) |
| :--- | :--- | :--- |
| **Subscriber Count** | 1,000 subscribers | 20,000 subscribers |
| **Historical Range** | 18 months (Jan 2025 - Jun 2026) | 18 months (Jan 2025 - Jun 2026) |
| **Baseline Churn Rate** | $12\% \pm 2\%$ | $12\% \pm 1\%$ |
| **Eligible Campaign Cohort** | $\approx 100 - 150$ subscribers | $\approx 2,000 - 3,000$ subscribers |
| **Randomization Arm Split** | $50\%$ Treatment / $50\%$ Control | $50\%$ Treatment / $50\%$ Control |
| **Injected Anomaly Rows** | 10 per type ($\approx 40$ total) | 40 per type ($\approx 160$ total) |
| **Storage Targets** | CSV + JSON + SQLite ($\le 5\text{ MB}$) | SQLite DB ($\le 120\text{ MB}$), CSV ($\le 50\text{ MB}$) |

---

## 5. Feature Engineering Requirements & Leakage Prevention

### Requirements for Feature Extraction
- **Zero-Lookahead Guarantee**: All feature extractors must accept an explicit `as_of_date` parameter. An event record is eligible for feature calculation if and only if:
  $$\text{event\_date} < \text{as\_of\_date}$$
  For monthly aggregations (usage snapshots), a snapshot is valid if and only if:
  $$\text{period\_end} < \text{as\_of\_date}$$
- **Extracted Feature Vector** (16 pre-prediction features):
  1. `usage_ratio_3m_prior`: Trend ratio comparing recent 3-month volume to prior 3-month volume.
  2. `last_month_active_days`: Active days in the calendar month immediately preceding `as_of_date`.
  3. `usage_slope_6m`: OLS regression slope over 6 monthly usage snapshot values.
  4. `failed_payments_6m`: Count of payment failure events in the 6-month lookback window.
  5. `days_since_last_failure`: Recency of billing disruption (imputed with 999 if no failure).
  6. `outstanding_balance`: Sum of open unpaid invoice amounts.
  7. `support_cases_6m`: Total support tickets opened in the lookback window.
  8. `high_severity_cases_6m`: Urgent or critical ticket volume in the lookback window.
  9. `cancellation_inquiries_6m`: Explicit tickets inquiring regarding cancellation procedures.
  10. `tenure_days`: Elapsed days between `signup_date` and `as_of_date`.
  11. `plan_tier`: Subscription tier (`BASIC`, `STANDARD`, `PREMIUM`).
  12. `monthly_price`: Monthly fee in USD.
  13. `plan_downgraded_6m`: Boolean indicator of subscription downgrade during lookback.
  14. `segment`: Customer segment (`CONSUMER`, `SMB`).
  15. `channel`: Acquisition source (`ORGANIC`, `PAID`, `PARTNER`, `REFERRAL`).
  16. `usage_pattern`: Known behavioral profile (`STEADY`, `SEASONAL`).
- **Decoy Feature Handling**: Seasonal subscribers exhibit natural off-peak usage contractions without churning; the model must learn to disambiguate seasonal dips from genuine pre-churn decay.

---

## 6. Risk Scoring & Predictive Modeling Requirements

- **Model Specification**: Logistic Regression with standard scaling and L2 regularization as primary; coefficients must be directly exportable as log-odds and odds-ratios for stakeholder transparency.
- **Stratification**: Continuous churn probabilities are segmented into three operational risk bands:
  - **HIGH**: Top 20th percentile ($score \ge \tau_{\text{high}}$) $\rightarrow$ eligible for intervention.
  - **MEDIUM**: 50th to 80th percentile.
  - **LOW**: Bottom 50th percentile.
- **Evaluation Independence (ADR-012)**:
  - Predictive accuracy metrics (AUC-ROC, Brier score, Precision-Recall) must be computed **exclusively on untreated subscribers** (Control group + Untargeted medium/low risk + Ineligible accounts).
  - Treated subscribers are censored from baseline model evaluation to prevent intervention bias from corrupting baseline model metrics.

---

## 7. Eligibility Rules Engine & Financial Margin Guardrails

Every customer must be evaluated through a rules pipeline before campaign inclusion. Each evaluation generates a persistent row in `rule_evaluation` detailing the rule code, pass/fail status, observed value, and configured threshold.

- **ER-001 (Active Subscription)**: Subscription must be current as of `as_of_date`.
- **ER-002 (Tenure Threshold)**: Tenure must be $\ge 90$ days.
- **ER-003 (Marketing Opt-in)**: Privacy and marketing consent must be affirmative (`marketing_opt_in == True`).
- **ER-004 (Clean Billing)**: No unresolved overdue billing balance (`outstanding_balance == 0.0`).
- **ER-005 (Support Escalation Guard)**: No open unresolved high/critical support cases (prevents automated discount marketing to frustrated customers requiring human agent care).
- **ER-006 (Risk Threshold)**: Model predicted risk band must be `HIGH`.
- **ER-007 (Financial Margin Gate)**: Evaluated per candidate offer:
  $$\text{Offer Cost} \le \text{max\_cost\_share\_of\_margin} \times (6 \times \text{monthly\_price} \times \text{gross\_margin\_pct})$$
  Offers that breach this financial threshold are disqualified for that specific customer.

---

## 8. Experimentation Design & Causal Lift Requirements

- **Planned Offer First (ADR-007)**:
  1. For each eligible customer, candidate offers passing ER-007 are identified.
  2. One offer is selected uniformly at random as the customer's **planned offer**.
  3. Customers are randomized 50/50 into `TREATMENT` or `CONTROL`, stratified by risk score decile.
- **Control Group Auditing**:
  - Control customers receive a `campaign_contact` record with `contact_status = 'WITHHELD'` and preserve their planned `offer_id`.
  - This allows unbiased estimation of offer-specific lift in addition to aggregate campaign lift.
- **Causal Metric Requirements**:
  1. **Primary Metric (Intention-To-Treat Lift)**:
     $$\text{Lift}_{\text{ITT}} = \frac{R_{\text{treatment}}}{N_{\text{treatment}}} - \frac{R_{\text{control}}}{N_{\text{control}}}$$
     where $R$ is retained customer count at day 90, and $N$ is total assigned customers in the arm.
  2. **Standard Error & 95% Confidence Interval**:
     $$\text{SE} = \sqrt{\frac{p_T(1-p_T)}{N_T} + \frac{p_C(1-p_C)}{N_C}}, \quad \text{CI}_{95\%} = \text{Lift}_{\text{ITT}} \pm 1.96 \times \text{SE}$$
  3. **Correlation vs. Causation Proof**: The system must compute and contrast:
     - Naive Treated Retention: $\text{Retention rate among treatment recipients}$
     - Naive Redeemed Retention: $\text{Retention rate among offer redeemers}$
     - Causal ITT Lift: $\text{Incremental retention over withheld control baseline}$
- **Counterfactual Ground Truth (ADR-005)**:
  - Latent segments (`persuadable`, `sure-thing`, `lost-cause`) stored in `ground_truth/` generate the observed outcomes.
  - Evaluation reporting must compare empirical ITT lift against the true latent population effect.

---

## 9. Anomaly Injection & Blind Detection Framework

Four operational failure modes must be injected into the post-assignment data to simulate real enterprise system bugs:

1. **Anomaly A (Temporal Inversion)**:
   - *Bug*: Churn date or cancellation event recorded prior to prediction cutoff date $P$, or billing event occurring after recorded account termination.
   - *Target Count*: $\approx 40$ records (starter: 10).
2. **Anomaly B (Eligibility Violation)**:
   - *Bug*: Customer contacted with an offer despite failing eligibility criteria (e.g., tenure $< 90$ days, opted out of marketing, or outstanding failed payment balance).
   - *Target Count*: $\approx 40$ records (starter: 10).
3. **Anomaly C (Group Exclusivity Violation)**:
   - *Bug*: Customer erroneously assigned to both Treatment and Control arms, or assigned multiple simultaneous retention offers.
   - *Target Count*: $\approx 40$ records (starter: 10).
4. **Anomaly D (Attribution & Margin Breach)**:
   - *Bug*: Retention outcome credited without prior campaign contact record, or realized offer discount exceeding configured margin share cap.
   - *Target Count*: $\approx 40$ records (starter: 10).

### Blind Detection & Audit Rules
- Detectors must run using only production database queries and business rules (zero access to `ground_truth/`).
- An independent `audit` module loads ground truth to evaluate detector **Recall** and **Precision**:
  - Target Recall: **100%** on injected test cases.
  - Detected anomaly rows must be flagged and excluded from official causal lift and financial impact evaluation.

---

## 10. System Interfaces & Usability Requirements

### 1. CLI Commands
- `python -m churnexp generate --scale [starter|full]`: Generate all synthetic history, features, assignments, outcomes, and anomalies.
- `python -m churnexp validate`: Execute structural, temporal, and referential integrity checks.
- `python -m churnexp train`: Train risk model on $P_0$ snapshot and compute validation metrics.
- `python -m churnexp campaign`: Execute scoring at $P$, evaluate eligibility rules, and allocate experiment arms.
- `python -m churnexp evaluate`: Compute ITT lift, naive comparisons, confidence intervals, and financial impact.
- `python -m churnexp audit`: Run blind detectors and score precision/recall against ground truth.
- `python -m churnexp repro-check`: Execute end-to-end reproducibility check using seed `20261022` and verify bitwise file hashes.
- `python -m churnexp all --scale [starter|full]`: Run complete pipeline from generation to evaluation.

### 2. Read-Only REST API (FastAPI)
- `GET /health`
- `GET /customers/{id}`
- `GET /customers/{id}/timeline`
- `GET /customers/{id}/eligibility`
- `GET /campaign/summary`
- `GET /experiment/results`
- `GET /model/metrics`
- `GET /validation/report`
- `GET /anomalies/detected`

### 3. Streamlit Actor Dashboard
- **Marketing Operations**: Campaign configuration, offer performance, treatment vs control balance, financial cost reconciliation.
- **Support Agent**: Customer 360 overview, chronological event timeline, rule trace explanation for customer questions.
- **Data Analyst**: ROC curves, feature coefficients, ITT causal lift vs naive metrics, anomaly inspection.
- **Platform Admin**: System health metrics, SQLite validation report, reproducibility verification, checksum manifests.

---

## 11. Non-Functional & Reproducibility Requirements

- **Determinism**: The entire data generation and randomized allocation pipeline must stem from a single root `SeedSequence(20261022)`. Sub-generators spawn deterministic child streams indexed by entity ID.
- **Temporal Sorting**: All exported CSV and JSON artifacts must be deterministically sorted by primary keys and timestamps. No non-deterministic wall-clock timestamps in generated data.
- **Performance**:
  - Starter scale generation and evaluation: $\le 10\text{ seconds}$.
  - Full scale (20,000 customers) generation and evaluation: $\le 90\text{ seconds}$.
- **Zero Heavy Dependencies**: Pure Python 3.11 with pandas, NumPy, scikit-learn, SQLite, FastAPI, and Streamlit. No Docker containers, no external database servers, no message brokers.

---

## 12. Requirement catalog (added in Run 3)

These IDs were assigned during Run 3 so that requirements can be traced to tests. They restate the requirements in sections 1-11 and the challenge brief. They are not a change to those requirements. The numbering differs from the planning notes used earlier in the project.

### Deviations from the original plan
- (a) FR-20: the read-only FastAPI service was not built; the Streamlit dashboard plus a read-only services layer replaces it;
- (b) the optional gradient-boosting comparison was not built; logistic regression only.

### Functional Requirements (FR-01 to FR-20)
- **FR-01**: Synthetic customer and subscription history generator across 18 months for starter (1k) and full (20k) scales.
- **FR-02**: Relational SQLite storage with plain SQL schema, primary/foreign keys, and analytical views.
- **FR-03**: Append-only event tracking and subscription versioning for customer lifecycle states.
- **FR-04**: Dual-snapshot point-in-time feature extraction ($P_0 = 2025-07-01$, $P = 2026-01-01$) with zero leakage.
- **FR-05**: 180-day churn label resolution fully finalized before scoring cutoff date.
- **FR-06**: Explainable churn prediction modeling via standardized L2-penalized Logistic Regression.
- **FR-07**: Churn risk scoring and quantile band stratification (HIGH, MEDIUM, LOW).
- **FR-08**: Retention offer catalog defining 3 distinct offers (10% 6m, 20% 3m, 1 free month).
- **FR-09**: Seven-rule eligibility engine evaluating tenure, opt-in, billing, support, and risk.
- **FR-10**: Financial gross margin cap guardrail (ER-007) evaluated per candidate offer.
- **FR-11**: Planned offer assignment to eligible candidates prior to arm randomization.
- **FR-12**: Stratified 50/50 randomized experiment assignment (TREATMENT vs CONTROL with WITHHELD status).
- **FR-13**: Counterfactual simulation of response, redemption, and post-churn usage generation.
- **FR-14**: Deterministic operational anomaly injection across four failure types (A, B, C, D).
- **FR-15**: Blind business-rule detectors (DET-A, DET-B, DET-C, DET-D) operating without ground truth.
- **FR-16**: Ground-truth audit module scoring detector precision/recall and causal estimator coverage.
- **FR-17**: Causal Intention-to-Treat (ITT) lift estimation (primary 90d, secondary 180d, exploratory subgroups) with 95% CIs.
- **FR-18**: Integer-cent financial impact and ROI calculation (realized cost vs incremental margin).
- **FR-19**: Multi-format data exporter (CSV, JSON, SQL) with cryptographic SHA-256 manifests.
- **FR-20**: Serving interface (FastAPI read-only REST API replaced by Streamlit actor dashboard and services layer).

### Non-Functional Requirements (NFR-01 to NFR-07)
- **NFR-01**: Deterministic reproducibility via master SeedSequence(20261022) and per-entity child substreams.
- **NFR-02**: Zero temporal lookahead data leakage guaranteed by design.
- **NFR-03**: Strict ground truth isolation (no cheat columns in database, isolated ground_truth/ directory).
- **NFR-04**: Modular monolith architecture in pure Python 3.11 with no external daemons.
- **NFR-05**: Strict runtime performance targets (starter <= 10s, full <= 90s).
- **NFR-06**: Deterministic formatting and primary key sorting across all exports.
- **NFR-07**: Comprehensive automated test and validation coverage.

### Acceptance Criteria (AC-01 to AC-12)
- **AC-01**: Dual temporal snapshot isolation verified with mutate-the-future tests.
- **AC-02**: Baseline 18-month annualized churn rate within 5% to 20% boundary.
- **AC-03**: 50/50 stratified randomization balance across risk strata and plan tiers.
- **AC-04**: Planned offer recorded for both Treatment and Control arms.
- **AC-05**: 18 structural and relational integrity validation rules pass with zero findings.
- **AC-06**: Four operational anomalies (A, B, C, D) deterministically injected at pipeline tail.
- **AC-07**: Blind detectors identify injected anomalies without ground truth access.
- **AC-08**: Ground truth audit confirms 100% precision and recall on injected anomalies.
- **AC-09**: Primary 90-day and secondary 180-day ITT lift evaluated with unpooled 95% CIs.
- **AC-10**: Financial impact evaluated in integer cents using realized costs and 6-month margins.
- **AC-11**: Multi-format exports match SQLite database with verified SHA-256 manifests.
- **AC-12**: Independent runs with different PYTHONHASHSEED produce bitwise identical outputs.

