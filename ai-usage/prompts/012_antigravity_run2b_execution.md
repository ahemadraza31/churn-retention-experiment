# Prompt 012: Run 2B Implementation Execution

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Run 2B Execution
- **Task / Scope**: Implementing anomaly injection, blind detectors, ground truth audit scoring, causal ITT lift calculation, and financial reporting.

## Prompt Text

```text
Execute Run 2B: Anomalies, Detectors, Audit, and Evaluation.
1. Implement src/churnexp/anomalies/inject.py: inject 40 anomalies (10 per type at starter scale) deterministically, writing ground_truth/anomalies.csv.
2. Implement src/churnexp/validation/detectors.py: implement DET-A, DET-B, DET-C, DET-D evaluating observable tables blind to ground truth. Output anomaly_report.json.
3. Implement src/churnexp/audit/score.py: calculate confusion matrix, precision, recall, and causal estimator coverage, writing audit_report.json.
4. Implement src/churnexp/evaluation/lift.py and financial.py: unpooled 95% CIs, p-values, incremental retained customers, and net financial impact in integer cents.
5. Provide tests in tests/unit/test_anomalies.py, test_detectors.py, test_audit.py, and test_evaluation.py.
```

## Orchestrator Review & Action

Verified that detectors achieve 100% precision and recall on the starter dataset without accessing ground truth. Caught that the agent had overwritten approved ADR numbers (ADR-008..011) in documentation, and flagged for renumbering to ADR-013..016 in Run 3. Ran tests locally and committed Run 2B.

