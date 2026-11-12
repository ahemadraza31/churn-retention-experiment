# Final Engineering & Evaluation Report: Churn Detection and Retention Offer Experiment

**Project**: Churn Detection and Retention Offer Experiment  
**Package**: `churnexp` (v0.1.0)  
**Date**: November 12, 2026  
**Status**: Milestone 12 Complete (Final Delivery)  

---

## 1. Project Overview

Subscription-based business models rely on retaining high-value subscribers while maintaining healthy customer acquisition and retention margins. In practice, retention campaigns frequently fall victim to the **correlation vs. causation illusion**: naive reporting credits retention offers for keeping customers who were "sure things" who would have remained anyway. Furthermore, real-world data pipelines suffer from subtle lookahead feature leakage, invalid eligibility overrides, and group exclusivity bugs.

The **Churn Detection and Retention Offer Experiment** system (`churnexp`) is an end-to-end, reproducible, and mathematically rigorous platform designed to:
1. Synthesize 18 months of realistic subscriber history without lookahead leakage.
2. Train explainable churn risk models at $P_0 = \text{2025-07-01}$ and score active accounts at $P = \text{2026-01-01}$.
3. Enforce multi-tier business eligibility rules (ER-001 through ER-006) and gross margin caps (ER-007).
4. Assign planned offers and execute 50/50 stratified randomized allocation into Treatment and Withheld Control arms.
5. Inforce deterministic operational anomalies (Types A-D) and detect them blind to ground truth.
6. Evaluate true causal Intention-to-Treat (ITT) lift with unpooled 95% confidence intervals and exact integer-cent net financial return.
7. Provide actor-specific read-only interfaces (Streamlit dashboard and domain query services).

---

## 2. Implemented Capabilities

- **Synthetic History Generation (`churnexp.generation`)**: Parametric simulation of subscriptions, plan downgrades/upgrades, usage minutes, sessions, billing invoices, failed payments, retries, and support tickets across 18 months.
- **Strict Point-in-Time Temporal Feature Builder (`churnexp.features`)**: Dual-snapshot feature extraction ($P_0$ and $P$) enforcing zero lookahead with mutate-the-future validation.
- **Explainable Predictive Modeling (`churnexp.modeling`)**: Standardized $L_2$-regularized Logistic Regression outputting quantile risk bands (HIGH, MEDIUM, LOW) and transparent odds ratios.
- **Eligibility & Margin Engine (`churnexp.eligibility`)**: Evaluates candidate accounts against 7 rules, ensuring offers do not breach the 25% expected 6-month gross margin threshold.
- **Planned-Offer Stratified Assignment (`churnexp.experiment`)**: Assigns planned offers prior to 50/50 stratified randomization; records planned offers for withheld control contacts to preserve causal comparability.
- **Counterfactual Outcome Simulation (`churnexp.experiment`)**: Models response, redemption, and post-churn history on isolated customer RNG sub-streams.
- **Deterministic Anomaly Injection (`churnexp.anomalies`)**: Injects operational anomalies (Types A-D) at the pipeline tail strictly by adding rows.
- **Blind Business-Rule Detectors (`churnexp.validation`)**: Operates on production tables without ground truth access, flagging temporal inversions, ineligible contacts, group leakage, and multi-attribution.
- **Ground Truth Audit (`churnexp.audit`)**: Measures detector precision/recall against isolated ground truth and validates causal estimator confidence interval coverage.
- **Causal & Financial Evaluation (`churnexp.evaluation`)**: Excludes corrupt contacts, estimates ITT lift across 90-day and 180-day horizons, and calculates exact integer-cent financial impact.
- **Multi-Format Export & Manifest Verification (`churnexp.io`, `churnexp.repro`)**: Exports SQLite tables to CSV, JSON, and SQL dumps, verifying bitwise reproducibility across independent seeds.
- **Actor Dashboard & Services (`churnexp.services`, `app/streamlit_app.py`)**: Read-only Streamlit dashboard tailored for Marketing Ops, Support Agents, Data Analysts, and System Administrators.

---

## 3. Architecture Summary

The system is implemented as a single modular monolith package `churnexp` following Architecture Decision Records (ADRs 001 through 016):
- **ADR-001**: Modular Monolith Architecture.
- **ADR-002**: Separation of DB constraints vs application business-rule validators.
- **ADR-003**: Append-only status tracking with subscription chaining (`previous_subscription_id`) and state events.
- **ADR-004**: Dual temporal snapshot leakage defense ($P_0 = 2025-07-01$, $P = 2026-01-01$).
- **ADR-005**: Hidden latent counterfactual outcomes stored in isolated `ground_truth/`.
- **ADR-006**: Ground truth isolation; zero cheat columns in production tables.
- **ADR-007**: Planned offer assignment first, 50/50 stratified randomization, ITT primary metric with withheld controls.
- **ADR-008**: Determinism via master `SeedSequence(20261022)` and per-entity child substreams.
- **ADR-009**: Starter scale committed to Git; full scale verified via SHA-256 manifests.
- **ADR-010**: Explainable Logistic Regression with standardized coefficients.
- **ADR-011**: Serving architecture; Streamlit calls shared domain services directly with read-only SQLite connections.
- **ADR-012**: Post-experiment model evaluation strictly on untreated cohorts.
- **ADR-013**: Deterministic injection of four operational anomalies at pipeline tail.
- **ADR-014**: Blind business-rule detectors operating on production database tables.
- **ADR-015**: Ground truth audit verifying 100% precision and recall and causal coverage.
- **ADR-016**: Causal evaluation filtering detector-flagged records with integer-cent financials.

---

## 4. Technology Stack

- **Runtime & Language**: Python 3.11
- **Numerical & Data Processing**: NumPy, pandas, scikit-learn
- **Database**: SQLite 3 with plain SQL DDL (`schema.sql`, `views.sql`)
- **Configuration Management**: PyYAML (`config/default.yaml`, `config/starter.yaml`)
- **Web Application & UI**: Streamlit (native widgets and caching only)
- **Automated Testing & QA**: pytest, XML test reporting
- **Design Invariants**: No Faker (avoids non-deterministic PII), no ORM (explicit SQL schema), no Docker containers or background daemon processes required.

---

## 5. Database & Data-Generation Summary

Real row counts extracted directly from committed `MANIFEST.json` files:

| Relational Table / File | Starter Scale (`--scale starter`) | Full Production Scale (`--scale full`) |
| :--- | ---: | ---: |
| `customer` | 1,000 | 20,000 |
| `subscription` | 1,200 | 23,875 |
| `usage_snapshot` | 16,255 | 327,426 |
| `billing_event` | 32,381 | 653,119 |
| `support_case` | 1,028 | 20,859 |
| `offer` | 3 | 3 |
| `eligibility_rule` | 7 | 7 |
| `offer_eligibility_rule` | 21 | 21 |
| `feature_snapshot` | 1,793 | 36,089 |
| `risk_score` | 917 | 18,363 |
| `rule_evaluation` | 8,253 | 165,267 |
| `campaign_contact` | 253 | 4,987 |
| `retention_outcome` | 253 | 4,987 |
| `churn_outcome` | 1,803 | 36,141 |
| `state_event` | 3,165 | 64,021 |
| **Ground Truth**: `anomalies.csv` | 40 | 160 |
| **Ground Truth**: `expected_decisions.csv` | 8,253 | 165,267 |
| **Ground Truth**: `latent_customer_state.csv` | 1,000 | 20,000 |

---

## 6. Business Workflow Demonstration

Executing `python -m churnexp all --scale starter` runs the complete operational sequence:

```bash
$ python -m churnexp all --scale starter
=== Running Full Pipeline ('all') (scale=starter) ===
=== Generation Summary (scale=starter, seed=20261022) ===
  customers                   : 1000
  subscriptions               : 1200
  overall_churn_rate          : 0.1240
  feature_snapshots           : 1793
  scored_customers (P)        : 917
  eligible_contacts           : 203
  planned_offer_counts        : OFF-2026-000001=113, OFF-2026-000002=88, OFF-2026-000003=2
  stratum HIGH   arms         : TREATMENT=39, CONTROL=47
  stratum MEDIUM arms         : TREATMENT=53, CONTROL=64
  saved (TREATMENT+SENT)      : 1
=== Validation Report (scale=starter) ===
  Overall data quality: PASS | business-rule detector findings: 40 (expected when anomalies are injected; see anomaly_report.json)
=== Evaluation Summary (scale=starter) ===
  Detector Exclusions: 40 unique customers
  Untreated Model AUC: 180d=0.5516, 90d=0.6869
  Primary 90d ITT Lift: +1.37 pp [-8.00, +10.74] (p=0.7745)
  Secondary 180d ITT Lift: +3.23 pp [-1.92, +8.39] (p=0.2192)
  Financial Impact (180d headline): Net Impact=-9562 cents, Benefit=30750 cents, Cost=40312 cents
=== Audit Report (scale=starter) ===
  Detectors: 4/4 PASS (100% Precision, 100% Recall)
  Causal Estimator Check: PASS (95% CI encompasses true treatment effect)

=== Pipeline Execution Summary ===
  generate  : PASS
  export    : PASS
  validate  : PASS
  evaluate  : PASS
  audit     : PASS
```

---

## 7. Evaluation Metrics & Experimental Results (Full Scale)

Exact metrics copied from [`data/full/evaluation_results.json`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/data/full/evaluation_results.json):

### 1. Intention-to-Treat (ITT) Experimental Lift

| Horizon / Dimension | Treatment Retained / N | Control Retained / N | Absolute Lift | 95% Confidence Interval | p-value | Incremental Retained |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary 90-Day** | 2,292 / 2,354 (97.37%) | 2,356 / 2,433 (96.84%) | **+0.53 pp** | `[-0.42, +1.48] pp` | `0.2740` | +12.50 customers |
| **Secondary 180-Day**| 2,257 / 2,354 (95.88%) | 2,301 / 2,433 (94.57%) | **+1.30 pp** | `[+0.10, +2.51] pp` | `0.0345` | +30.71 customers |

### 2. Predictive Model Quality (Untreated Clean Cohort)
- **180-Day Untreated Cohort ROC-AUC**: `0.5996` (Brier score: `0.0514`)
- **90-Day Untreated Cohort ROC-AUC**: `0.6701` (Brier score: `0.0305`)
- **HIGH Band Decision Rule (Top 15%)**: Precision = 14.13%, Recall = 37.16%, Lift over base rate = 2.48x.

### 3. Financial Impact & Return on Investment (Integer Cents)
- **Expected Margin Horizon**: 6 months
- **Average Expected 6-Month Margin per Treated Account**: `6,027 cents` ($60.27)
- **Realized Offer Cost (Redeemed & Retained)**: `827,795 cents` ($8,277.95)
- **Gross Retention Benefit (30.71 incremental saves $\times$ \$60.27)**: `185,119 cents` ($1,851.19)
- **Net Financial Impact**: **-642,676 cents** (-$6,426.76)
- **95% Confidence Interval of Net Impact**: `[-813,806, -471,560] cents`
- **Cost per Incremental Retained Customer**: `26,951 cents` ($269.51)

### Business Assessment
The 180-day retention lift is positive (+1.30 pp) and statistically significant at the 5% level ($p = 0.0345$, CI $[+0.10, +2.51]$ pp). However, the program produces a net financial loss (-$6,426.76, CI excludes zero) because the cost per incremental retained customer ($269.51) exceeds the customer's 6-month expected gross margin ($60.27) by a factor of 4.5x. Under the simulated parameters, indiscriminately discounting all high-risk accounts is financially destructive.

---

## 8. Test Execution Summary

Real test counts from the latest automated test run (`make qa`):

- **Total Test Cases**: **123**
- **Passed**: **123 (100%)**
- **Failed**: **0**
- **Skipped**: **0**
- **Test Modules**: 26 unit test modules across `tests/unit/`
- **Operational Checks**:
  - `python -m churnexp validate --scale starter`: Exit Code 0 (PASS)
  - `python -m churnexp audit --scale starter`: Exit Code 0 (PASS)
  - `python -m churnexp repro-check --scale starter`: Exit Code 0 (PASS)
  - `python -m churnexp all --scale starter`: Exit Code 0 (PASS)

---

## 9. Requirements Traceability Coverage

Summary counts from [`docs/REQUIREMENTS_TRACEABILITY.md`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/REQUIREMENTS_TRACEABILITY.md):

- **Functional Requirements (FR-01 to FR-20)**: 20 / 20 covered (19 implemented, 1 documented design change for FR-20)
- **Non-Functional Requirements (NFR-01 to NFR-07)**: 7 / 7 covered (100% verified)
- **Acceptance Criteria (AC-01 to AC-12)**: 12 / 12 covered (100% verified)
- **Operational Anomalies (ANOM-A to ANOM-D)**: 4 / 4 covered (100% verified)
- **Relational Integrity Validation Rules**: 12 / 12 covered (100% verified)

---

## 10. Known Limitations & Remaining Risks

1. **Single Promotional Wave**: The experiment simulates wave `2026-W01`. Multiple rolling waves with re-contact fatigue were not simulated.
2. **Parametric Behavioral Dynamics**: Pre-churn usage contraction follows geometric decay. Human operational churn often exhibits sporadic or catastrophic churn patterns.
3. **Weak Distant Signal**: Behavioral decay is strongest in the 90 days prior to churn; predicting a 180-day window dilutes model signal to ~0.60 AUC.
4. **Plan Change Boundary Rule**: Accounts with plan transitions exactly on the `as_of` boundary date are excluded from feature extraction.
5. **Free Month Offer Constraint**: Rule ER-007 mathematically restricts the Free Month offer (`OFF-2026-000003`) to `PREMIUM` tier subscriptions only.
6. **No Live Production Database**: Designed and tested for embedded SQLite databases; enterprise migration to PostgreSQL/Snowflake would require migrating plain DDL into dialect-specific dialects.

---

## 11. Installation & Execution Instructions

```bash
# Clone and enter directory
git clone <repo-url>
cd churn-retention-experiment

# Environment setup (Python 3.11)
make setup

# Run test suite
make test

# Generate QA documentation and test report
make qa

# Launch actor dashboard
make demo
```

