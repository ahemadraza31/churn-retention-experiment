# Requirements Traceability Matrix

This document provides complete bidirectional traceability from the approved specifications in [`docs/01_requirements_spec.md`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/01_requirements_spec.md) and the project challenge brief to package implementations, automated pytest verification nodes, and committed evidence artifacts.

## 1. Specification Requirements (FR-01 to FR-20, NFR-01 to NFR-07, AC-01 to AC-12)

| Requirement ID | Summary | Implemented in | Tests (pytest node names) | Evidence file |
| :--- | :--- | :--- | :--- | :--- |
| **FR-01** | Synthetic customer & subscription history generator (18 months, starter/full) | `src/churnexp/generation/` | `tests/unit/test_generation_world.py::test_1_determinism_same_and_different_seed` | `data/starter/MANIFEST.json` |
| **FR-02** | Relational SQLite storage with plain DDL schema and analytical views | `src/churnexp/schema/` | `tests/unit/test_schema.py::test_tables_exist` | `data/starter/sql/seed.sql` |
| **FR-03** | Append-only lifecycle event tracking and subscription chain versioning | `src/churnexp/generation/world.py` | `tests/unit/test_schema.py::test_state_event_append_only` | `data/starter/csv/state_event.csv` |
| **FR-04** | Dual point-in-time feature extraction ($P_0, P$) with zero lookahead leakage | `src/churnexp/features/builder.py` | `tests/unit/test_features.py::test_mutate_the_future_leakage_defense[P0_2025-07-01]` | `data/starter/csv/feature_snapshot.csv` |
| **FR-05** | 180-day churn label generation resolved prior to prediction cutoff | `src/churnexp/generation/world.py` | `tests/unit/test_generation_world.py::test_7_churn_outcome_2025_consistency` | `data/starter/csv/churn_outcome.csv` |
| **FR-06** | Explainable Logistic Regression with standard scaling and exportable weights | `src/churnexp/modeling/train.py` | `tests/unit/test_model.py::test_model_determinism_and_p0_2025_alignment` | `data/starter/model_info.json` |
| **FR-07** | Risk scoring and quantile risk band stratification (HIGH, MEDIUM, LOW) | `src/churnexp/modeling/score.py` | `tests/unit/test_evaluation.py::test_binary_metrics_roc_auc` | `data/starter/csv/risk_score.csv` |
| **FR-08** | Retention offer catalog (3 offers: 10% 6m, 20% 3m, 1 free month) | `src/churnexp/eligibility/catalog.py` | `tests/unit/test_eligibility.py::test_er007_cost_and_margin_math_exact_integer_cents` | `data/starter/csv/offer.csv` |
| **FR-09** | Seven-rule eligibility engine evaluating tenure, billing, support, and risk | `src/churnexp/eligibility/rules.py` | `tests/unit/test_eligibility.py::test_er001_to_er006_pass_fail_and_boundaries` | `data/starter/csv/rule_evaluation.csv` |
| **FR-10** | Offer margin guardrail gate (ER-007) evaluating cost vs 6-month gross margin | `src/churnexp/eligibility/rules.py` | `tests/unit/test_eligibility.py::test_er007_cost_and_margin_math_exact_integer_cents` | `data/starter/csv/offer_eligibility_rule.csv` |
| **FR-11** | Planned offer assignment to eligible candidates prior to arm randomization | `src/churnexp/experiment/assign.py` | `tests/unit/test_assignment.py::test_assignment_invariants_stratification_and_determinism` | `data/starter/csv/campaign_contact.csv` |
| **FR-12** | 50/50 stratified randomized allocation (TREATMENT vs CONTROL with WITHHELD) | `src/churnexp/experiment/assign.py` | `tests/unit/test_assignment.py::test_assignment_invariants_stratification_and_determinism` | `data/starter/csv/campaign_contact.csv` |
| **FR-13** | Counterfactual simulation of response, redemption, and post-churn history | `src/churnexp/experiment/simulate.py` | `tests/unit/test_simulation.py::test_simulation_saves_and_invariants` | `data/starter/csv/retention_outcome.csv` |
| **FR-14** | Deterministic operational anomaly injection across four failure types (A-D) | `src/churnexp/anomalies/inject.py` | `tests/unit/test_anomalies.py::test_anomaly_injection_deterministic_and_counts` | `data/starter/ground_truth/anomalies.csv` |
| **FR-15** | Blind business-rule detectors (DET-A through DET-D) operating without ground truth | `src/churnexp/validation/detectors.py` | `tests/unit/test_detectors.py::test_detector_a_triggers_on_leakage` | `data/starter/anomaly_report.json` |
| **FR-16** | Ground-truth audit module scoring detector precision/recall and causal coverage | `src/churnexp/audit/score.py` | `tests/unit/test_audit.py::test_audit_perfect_precision_recall_on_starter` | `data/starter/audit_report.json` |
| **FR-17** | Causal Intention-to-Treat (ITT) lift estimation with unpooled 95% CIs and p-values | `src/churnexp/evaluation/lift.py` | `tests/unit/test_evaluation.py::test_lift_matches_manual_contingency_math` | `data/starter/evaluation_results.json` |
| **FR-18** | Integer-cent financial impact and ROI calculation (realized cost vs margin) | `src/churnexp/evaluation/financial.py` | `tests/unit/test_evaluation.py::test_financial_calculations_integer_cents` | `data/starter/evaluation_report.md` |
| **FR-19** | Multi-format data exporter (CSV, JSON, SQL) with SHA-256 manifests | `src/churnexp/io/exporters.py` | `tests/unit/test_export.py::test_exported_csv_reloaded_equals_db_tables` | `data/starter/MANIFEST.json` |
| **FR-20** | Read-only serving interface | Not implemented (FastAPI replaced by Streamlit actor dashboard and services layer) | `tests/unit/test_app.py::test_app_pages_render_without_exception` | `app/streamlit_app.py` |
| **NFR-01** | Deterministic reproducibility via master SeedSequence(20261022) | `src/churnexp/rng.py` | `tests/unit/test_rng.py::test_same_seed_gives_same_draws` | `data/starter/REPRODUCIBILITY.md` |
| **NFR-02** | Zero temporal lookahead data leakage guaranteed by design | `src/churnexp/features/builder.py` | `tests/unit/test_features.py::test_mutate_the_future_leakage_defense[P_2026-01-01]` | `docs/02_architecture.md` |
| **NFR-03** | Strict ground truth isolation (no cheat columns in DB, isolated files) | `src/churnexp/generation/world.py` | `tests/unit/test_generation_world.py::test_8_latent_isolation` | `data/starter/ground_truth/latent_customer_state.csv` |
| **NFR-04** | Modular monolith architecture in pure Python 3.11 with no external daemons | `src/churnexp/cli.py` | `tests/unit/test_cli.py::test_cli_health` | `pyproject.toml` |
| **NFR-05** | Runtime performance targets (starter <= 10s, full <= 90s) | `src/churnexp/generation/` | `tests/unit/test_pipeline.py::test_pipeline_determinism_and_base_hashes` | `docs/TIMELINE.md` |
| **NFR-06** | Deterministic formatting and primary key sorting across all exports | `src/churnexp/io/manifest.py` | `tests/unit/test_export.py::test_two_exports_of_same_db_are_byte_identical` | `data/starter/MANIFEST.json` |
| **NFR-07** | Automated end-to-end test and data validation coverage | `tests/` | `tests/unit/test_validation_checks.py::test_valid_starter_world_zero_findings` | `docs/TEST_REPORT.md` |
| **AC-01** | Dual temporal snapshot isolation verified with mutate-the-future tests | `src/churnexp/features/builder.py` | `tests/unit/test_features.py::test_mutate_the_future_leakage_defense[P0_2025-07-01]` | `data/starter/csv/feature_snapshot.csv` |
| **AC-02** | Baseline 18-month annualized churn rate within 5% to 20% boundary | `src/churnexp/generation/world.py` | `tests/unit/test_generation_world.py::test_3_churn_rate_types_plan_changes_and_seasonal` | `data/starter/MANIFEST.json` |
| **AC-03** | 50/50 stratified randomization balance across risk strata and plan tiers | `src/churnexp/experiment/assign.py` | `tests/unit/test_assignment.py::test_assignment_invariants_stratification_and_determinism` | `data/starter/csv/campaign_contact.csv` |
| **AC-04** | Planned offer recorded for both Treatment and Control arms | `src/churnexp/experiment/assign.py` | `tests/unit/test_assignment.py::test_assignment_invariants_stratification_and_determinism` | `data/starter/csv/campaign_contact.csv` |
| **AC-05** | 18 structural and relational integrity validation rules pass with zero findings | `src/churnexp/validation/checks.py` | `tests/unit/test_validation_checks.py::test_valid_starter_world_zero_findings` | `data/starter/validation_summary.md` |
| **AC-06** | Four operational anomalies (A, B, C, D) deterministically injected at pipeline tail | `src/churnexp/anomalies/inject.py` | `tests/unit/test_anomalies.py::test_anomaly_injection_deterministic_and_counts` | `data/starter/ground_truth/anomalies.csv` |
| **AC-07** | Blind detectors identify injected anomalies without ground truth access | `src/churnexp/validation/detectors.py` | `tests/unit/test_detectors.py::test_detector_a_triggers_on_leakage` | `data/starter/anomaly_report.json` |
| **AC-08** | Ground truth audit confirms 100% precision and recall on injected anomalies | `src/churnexp/audit/score.py` | `tests/unit/test_audit.py::test_audit_perfect_precision_recall_on_starter` | `data/starter/audit_report.json` |
| **AC-09** | Primary 90-day and secondary 180-day ITT lift evaluated with unpooled 95% CIs | `src/churnexp/evaluation/lift.py` | `tests/unit/test_evaluation.py::test_lift_matches_manual_contingency_math` | `data/starter/evaluation_results.json` |
| **AC-10** | Financial impact evaluated in integer cents using realized costs and 6-month margins | `src/churnexp/evaluation/financial.py` | `tests/unit/test_evaluation.py::test_financial_calculations_integer_cents` | `data/starter/evaluation_report.md` |
| **AC-11** | Multi-format exports match SQLite database with verified SHA-256 manifests | `src/churnexp/io/exporters.py` | `tests/unit/test_export.py::test_exported_csv_reloaded_equals_db_tables` | `data/starter/MANIFEST.json` |
| **AC-12** | Independent runs with different PYTHONHASHSEED produce bitwise identical outputs | `src/churnexp/repro.py` | `tests/unit/test_repro.py::test_repro_compare_identical_passes` | `data/starter/REPRODUCIBILITY.md` |

---

## 2. Four Mandatory Edge Cases (Anomalies A-D)

| Requirement ID | Summary | Implemented in | Tests (pytest node names) | Evidence file |
| :--- | :--- | :--- | :--- | :--- |
| **EDGE-A** | Temporal label leakage injection (churn_date < prediction_date) | `src/churnexp/anomalies/inject.py` & `src/churnexp/validation/detectors.py` | `tests/unit/test_detectors.py::test_detector_a_triggers_on_leakage` | `data/starter/ground_truth/anomalies.csv` |
| **EDGE-B** | Ineligible offer contact injection (fails eligibility ER-001..ER-007) | `src/churnexp/anomalies/inject.py` & `src/churnexp/validation/detectors.py` | `tests/unit/test_detectors.py::test_detector_b_triggers_on_ineligible_offer` | `data/starter/ground_truth/anomalies.csv` |
| **EDGE-C** | Group exclusivity violation injection (both Treatment and Control) | `src/churnexp/anomalies/inject.py` & `src/churnexp/validation/detectors.py` | `tests/unit/test_detectors.py::test_detector_c_triggers_on_group_leakage` | `data/starter/ground_truth/anomalies.csv` |
| **EDGE-D** | Multi-offer attribution injection (multiple retained offers credited) | `src/churnexp/anomalies/inject.py` & `src/churnexp/validation/detectors.py` | `tests/unit/test_detectors.py::test_detector_d_triggers_on_multi_attribution` | `data/starter/ground_truth/anomalies.csv` |

---

## 3. Twelve Challenge Brief Validation Rules

| Requirement ID | Validation Rule (Challenge Brief) | Implemented in | Tests (pytest node names) | Evidence file |
| :--- | :--- | :--- | :--- | :--- |
| **RULE-01** | Evaluation temporally valid | `src/churnexp/evaluation/cohorts.py` & `src/churnexp/evaluation/report.py` | `tests/unit/test_config.py::test_validation_rule_timeline_order` | `data/starter/evaluation_report.md` |
| **RULE-02** | No future information in features | `src/churnexp/features/builder.py` | `tests/unit/test_features.py::test_mutate_the_future_leakage_defense[P_2026-01-01]` | `data/starter/csv/feature_snapshot.csv` |
| **RULE-03** | Explicit churn definition | `src/churnexp/generation/world.py` | `tests/unit/test_schema_constraints.py::test_churn_outcome_checks` | `data/starter/csv/churn_outcome.csv` |
| **RULE-04** | Offer eligibility enforced | `src/churnexp/eligibility/rules.py` | `tests/unit/test_eligibility.py::test_er001_to_er006_pass_fail_and_boundaries` | `data/starter/csv/rule_evaluation.csv` |
| **RULE-05** | Cost and margin respected | `src/churnexp/eligibility/rules.py` | `tests/unit/test_eligibility.py::test_er007_cost_and_margin_math_exact_integer_cents` | `data/starter/csv/offer_eligibility_rule.csv` |
| **RULE-06** | Randomized valid assignment | `src/churnexp/experiment/assign.py` | `tests/unit/test_assignment.py::test_assignment_invariants_stratification_and_determinism` | `data/starter/csv/campaign_contact.csv` |
| **RULE-07** | Traceable state changes | `src/churnexp/generation/world.py` | `tests/unit/test_schema.py::test_state_event_append_only` | `data/starter/csv/state_event.csv` |
| **RULE-08** | Ground truth isolated | `src/churnexp/generation/world.py` & `src/churnexp/io/exporters.py` | `tests/unit/test_generation_world.py::test_8_latent_isolation` | `data/starter/ground_truth/latent_customer_state.csv` |
| **RULE-09** | Derived values reconcile | `src/churnexp/generation/world.py` & `src/churnexp/validation/checks.py` | `tests/unit/test_generation_world.py::test_5_reconciliation_billing_and_usage` | `data/starter/validation_summary.md` |
| **RULE-10** | Incremental lift vs correlation | `src/churnexp/evaluation/lift.py` & `src/churnexp/evaluation/report.py` | `tests/unit/test_evaluation.py::test_lift_matches_manual_contingency_math` | `data/starter/evaluation_results.json` |
| **RULE-11** | Exceptions documented | `src/churnexp/validation/detectors.py` & `src/churnexp/evaluation/report.py` | `tests/unit/test_detectors.py::test_clean_untreated_world_has_zero_detector_findings` | `data/starter/anomaly_report.json` |
| **RULE-12** | Reproducible generation | `src/churnexp/repro.py` & `src/churnexp/rng.py` | `tests/unit/test_pipeline.py::test_pipeline_determinism_and_base_hashes` | `data/starter/REPRODUCIBILITY.md` |
