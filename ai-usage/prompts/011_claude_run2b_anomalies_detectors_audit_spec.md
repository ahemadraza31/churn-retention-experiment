# Prompt 011: Run 2B Architecture & Anomaly Detection Specification

- **AI Tool**: Claude (Technical Lead)
- **Phase**: Run 2B Architecture Specification
- **Task / Scope**: Specification of 4 deterministic anomaly types (A-D), blind business-rule detectors, ground truth audit scoring, and causal ITT lift evaluation with financial metrics.

## Prompt Text

```text
Develop detailed implementation specifications for Run 2B:
1. Operational Anomaly Injection: Deterministic injection of four failure modes at pipeline tail:
   - Anomaly A: Temporal label leakage (churn_date < prediction_date).
   - Anomaly B: Offer sent to customer failing eligibility rules ER-001..ER-007.
   - Anomaly C: Customer assigned to both TREATMENT and CONTROL arms.
   - Anomaly D: Retained customer credited with multiple distinct offer attributions.
2. Blind Business-Rule Detectors: Implement DET-A through DET-D operating strictly on observable SQLite tables without ground truth access.
3. Ground Truth Audit: Independent module scoring detector precision and recall against ground_truth/anomalies.csv and verifying that empirical ITT lift CIs cover latent true effect.
4. Causal & Financial Evaluation: Filter out detector anomalies, evaluate ITT lift (90d primary, 180d secondary) with unpooled 95% CIs and p-values, and calculate net financial impact in integer cents.
```

## Orchestrator Review & Action

Reviewed the design to enforce strict separation between blind runtime detectors and the ground-truth audit module. Confirmed that detector-flagged records are cleanly excluded from the causal evaluation cohort to protect statistical validity. Handed off to Antigravity for implementation.

