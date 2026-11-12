# Prompt 009: Run 2A Architecture & Implementation Specification

- **AI Tool**: Claude (Technical Lead)
- **Phase**: Run 2A Architecture Specification
- **Task / Scope**: Specification of dual-snapshot feature extraction ($P_0, P$), standardized logistic regression modeling, 7-rule eligibility engine, planned offer assignment, and counterfactual simulation.

## Prompt Text

```text
Develop detailed implementation specifications for Run 2A:
1. Feature Builder: Dual temporal snapshots at P0 = 2025-07-01 (training) and P = 2026-01-01 (scoring). Strict point-in-time filtering: event_date < as_of_date. Include mutate-the-future test.
2. Modeling: Standardized L2-regularized Logistic Regression trained on P0, frozen, and scoring active accounts at P. Quantile risk band assignment (HIGH, MEDIUM, LOW).
3. Retention Offers & Eligibility: Catalog of 3 offers (10% 6m, 20% 3m, 1 free month). Seven eligibility rules (ER-001..ER-006 + ER-007 margin cap in integer cents).
4. Experiment Assignment: Planned offer assigned first to all eligible accounts, followed by 50/50 stratified randomization into TREATMENT vs CONTROL (with WITHHELD status).
5. Counterfactual Simulation: Simulate treatment response, redemption, and post-campaign retention using latent customer states without leaking ground truth.
```

## Orchestrator Review & Action

Reviewed and approved the specification. Confirmed that assigning planned offers prior to 50/50 randomization protects causal inference against post-treatment selection bias. Verified that financial limits are computed strictly in integer cents. Handed off to Antigravity for implementation.

