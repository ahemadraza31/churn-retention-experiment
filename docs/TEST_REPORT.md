# Test Execution & Verification Report

## 1. Test Execution Summary

- **Total Test Cases**: 123
- **Passed**: 123
- **Failed**: 0
- **Skipped**: 0
- **Status**: ALL PASSED

### Test Counts by File

| Test File | Total | Passed | Failed | Skipped | Status |
| :--- | ---: | ---: | ---: | ---: | :---: |
| `tests/unit/test_anomalies.py` | 1 | 1 | 0 | 0 | `PASS` |
| `tests/unit/test_app.py` | 4 | 4 | 0 | 0 | `PASS` |
| `tests/unit/test_assignment.py` | 1 | 1 | 0 | 0 | `PASS` |
| `tests/unit/test_audit.py` | 1 | 1 | 0 | 0 | `PASS` |
| `tests/unit/test_cli.py` | 8 | 8 | 0 | 0 | `PASS` |
| `tests/unit/test_config.py` | 9 | 9 | 0 | 0 | `PASS` |
| `tests/unit/test_data_dictionary.py` | 2 | 2 | 0 | 0 | `PASS` |
| `tests/unit/test_detectors.py` | 5 | 5 | 0 | 0 | `PASS` |
| `tests/unit/test_eligibility.py` | 4 | 4 | 0 | 0 | `PASS` |
| `tests/unit/test_evaluation.py` | 4 | 4 | 0 | 0 | `PASS` |
| `tests/unit/test_export.py` | 5 | 5 | 0 | 0 | `PASS` |
| `tests/unit/test_features.py` | 3 | 3 | 0 | 0 | `PASS` |
| `tests/unit/test_generation_config.py` | 10 | 10 | 0 | 0 | `PASS` |
| `tests/unit/test_generation_world.py` | 11 | 11 | 0 | 0 | `PASS` |
| `tests/unit/test_ids.py` | 6 | 6 | 0 | 0 | `PASS` |
| `tests/unit/test_model.py` | 1 | 1 | 0 | 0 | `PASS` |
| `tests/unit/test_pipeline.py` | 1 | 1 | 0 | 0 | `PASS` |
| `tests/unit/test_repro.py` | 5 | 5 | 0 | 0 | `PASS` |
| `tests/unit/test_rng.py` | 6 | 6 | 0 | 0 | `PASS` |
| `tests/unit/test_schema.py` | 6 | 6 | 0 | 0 | `PASS` |
| `tests/unit/test_schema_constraints.py` | 7 | 7 | 0 | 0 | `PASS` |
| `tests/unit/test_services.py` | 6 | 6 | 0 | 0 | `PASS` |
| `tests/unit/test_simulation.py` | 2 | 2 | 0 | 0 | `PASS` |
| `tests/unit/test_traceability.py` | 1 | 1 | 0 | 0 | `PASS` |
| `tests/unit/test_validation_checks.py` | 12 | 12 | 0 | 0 | `PASS` |
| `tests/unit/test_validation_enums.py` | 2 | 2 | 0 | 0 | `PASS` |

## 2. Test Case Execution Details

| Test Case ID | Test Node (`file::name`) | Requirement ID | Result | Defect Reference |
| :--- | :--- | :---: | :---: | :--- |
| `TC-001` | `tests/unit/test_anomalies.py::test_anomaly_injection_deterministic_and_counts` | `AC-06` | `PASSED` | - |
| `TC-002` | `tests/unit/test_app.py::test_app_pages_render_without_exception` | `FR-20` | `PASSED` | - |
| `TC-003` | `tests/unit/test_app.py::test_app_support_agent_detector_flagged_finding` | `-` | `PASSED` | - |
| `TC-004` | `tests/unit/test_app.py::test_app_missing_db_error` | `-` | `PASSED` | - |
| `TC-005` | `tests/unit/test_app.py::test_app_and_services_prohibited_imports_and_strings` | `-` | `PASSED` | - |
| `TC-006` | `tests/unit/test_assignment.py::test_assignment_invariants_stratification_and_determinism` | `RULE-06` | `PASSED` | - |
| `TC-007` | `tests/unit/test_audit.py::test_audit_perfect_precision_recall_on_starter` | `AC-08` | `PASSED` | - |
| `TC-008` | `tests/unit/test_cli.py::test_cli_help` | `-` | `PASSED` | - |
| `TC-009` | `tests/unit/test_cli.py::test_cli_health` | `NFR-04` | `PASSED` | - |
| `TC-010` | `tests/unit/test_cli.py::test_cli_health_full_scale` | `-` | `PASSED` | - |
| `TC-011` | `tests/unit/test_cli.py::test_cli_config` | `-` | `PASSED` | - |
| `TC-012` | `tests/unit/test_cli.py::test_cli_generate_starter` | `-` | `PASSED` | - |
| `TC-013` | `tests/unit/test_cli.py::test_cli_stubs` | `-` | `PASSED` | - |
| `TC-014` | `tests/unit/test_cli.py::test_cli_invalid_scale` | `-` | `PASSED` | - |
| `TC-015` | `tests/unit/test_cli.py::test_cli_missing_command` | `-` | `PASSED` | - |
| `TC-016` | `tests/unit/test_config.py::test_load_config_full` | `-` | `PASSED` | - |
| `TC-017` | `tests/unit/test_config.py::test_load_config_starter` | `-` | `PASSED` | - |
| `TC-018` | `tests/unit/test_config.py::test_validation_rule_timeline_order` | `RULE-01` | `PASSED` | - |
| `TC-019` | `tests/unit/test_config.py::test_validation_rule_training_label_leakage` | `-` | `PASSED` | - |
| `TC-020` | `tests/unit/test_config.py::test_validation_rule_score_horizon_boundary` | `-` | `PASSED` | - |
| `TC-021` | `tests/unit/test_config.py::test_validation_rule_churn_rates` | `-` | `PASSED` | - |
| `TC-022` | `tests/unit/test_config.py::test_validation_rule_population` | `-` | `PASSED` | - |
| `TC-023` | `tests/unit/test_config.py::test_validation_rule_treatment_share` | `-` | `PASSED` | - |
| `TC-024` | `tests/unit/test_config.py::test_load_config_unknown_scale` | `-` | `PASSED` | - |
| `TC-025` | `tests/unit/test_data_dictionary.py::test_dictionary_sync` | `-` | `PASSED` | - |
| `TC-026` | `tests/unit/test_data_dictionary.py::test_ground_truth_dictionary_headers_match_csv` | `-` | `PASSED` | - |
| `TC-027` | `tests/unit/test_detectors.py::test_clean_untreated_world_has_zero_detector_findings` | `RULE-11` | `PASSED` | - |
| `TC-028` | `tests/unit/test_detectors.py::test_detector_a_triggers_on_leakage` | `EDGE-A` | `PASSED` | - |
| `TC-029` | `tests/unit/test_detectors.py::test_detector_b_triggers_on_ineligible_offer` | `EDGE-B` | `PASSED` | - |
| `TC-030` | `tests/unit/test_detectors.py::test_detector_c_triggers_on_group_leakage` | `EDGE-C` | `PASSED` | - |
| `TC-031` | `tests/unit/test_detectors.py::test_detector_d_triggers_on_multi_attribution` | `EDGE-D` | `PASSED` | - |
| `TC-032` | `tests/unit/test_eligibility.py::test_er001_to_er006_pass_fail_and_boundaries` | `RULE-04` | `PASSED` | - |
| `TC-033` | `tests/unit/test_eligibility.py::test_er004_grace_boundary_and_er005_resolved_day_before_in_engine` | `-` | `PASSED` | - |
| `TC-034` | `tests/unit/test_eligibility.py::test_er007_cost_and_margin_math_exact_integer_cents` | `RULE-05` | `PASSED` | - |
| `TC-035` | `tests/unit/test_eligibility.py::test_source_files_contain_no_forbidden_ground_truth_strings` | `-` | `PASSED` | - |
| `TC-036` | `tests/unit/test_evaluation.py::test_lift_matches_manual_contingency_math` | `RULE-10` | `PASSED` | - |
| `TC-037` | `tests/unit/test_evaluation.py::test_financial_calculations_integer_cents` | `AC-10` | `PASSED` | - |
| `TC-038` | `tests/unit/test_evaluation.py::test_binary_metrics_roc_auc` | `FR-07` | `PASSED` | - |
| `TC-039` | `tests/unit/test_evaluation.py::test_empty_arm_subgroups_and_markdown_formatting` | `-` | `PASSED` | - |
| `TC-040` | `tests/unit/test_export.py::test_exported_csv_reloaded_equals_db_tables` | `AC-11` | `PASSED` | - |
| `TC-041` | `tests/unit/test_export.py::test_exported_json_equals_csv` | `-` | `PASSED` | - |
| `TC-042` | `tests/unit/test_export.py::test_schema_and_seed_sql_reproduce_identical_table_hashes` | `-` | `PASSED` | - |
| `TC-043` | `tests/unit/test_export.py::test_two_exports_of_same_db_are_byte_identical` | `NFR-06` | `PASSED` | - |
| `TC-044` | `tests/unit/test_export.py::test_no_ground_truth_strings_in_csv_json_sql` | `-` | `PASSED` | - |
| `TC-045` | `tests/unit/test_features.py::test_mutate_the_future_leakage_defense[P0_2025-07-01]` | `AC-01` | `PASSED` | - |
| `TC-046` | `tests/unit/test_features.py::test_mutate_the_future_leakage_defense[P_2026-01-01]` | `RULE-02` | `PASSED` | - |
| `TC-047` | `tests/unit/test_features.py::test_hand_built_tables_known_expected_values` | `-` | `PASSED` | - |
| `TC-048` | `tests/unit/test_generation_config.py::test_generator_config_loaded_values` | `-` | `PASSED` | - |
| `TC-049` | `tests/unit/test_generation_config.py::test_generator_config_invalid_segment_probs` | `-` | `PASSED` | - |
| `TC-050` | `tests/unit/test_generation_config.py::test_generator_config_invalid_signup_dates` | `-` | `PASSED` | - |
| `TC-051` | `tests/unit/test_generation_config.py::test_generator_config_invalid_tier_prices` | `-` | `PASSED` | - |
| `TC-052` | `tests/unit/test_generation_config.py::test_generator_config_invalid_segment_conditional_probs` | `-` | `PASSED` | - |
| `TC-053` | `tests/unit/test_generation_config.py::test_generator_config_invalid_plan_limits` | `-` | `PASSED` | - |
| `TC-054` | `tests/unit/test_generation_config.py::test_generator_config_invalid_billing_reasons` | `-` | `PASSED` | - |
| `TC-055` | `tests/unit/test_generation_config.py::test_generator_config_invalid_support_escalation_prob` | `-` | `PASSED` | - |
| `TC-056` | `tests/unit/test_generation_config.py::test_campaign_config_invalid_shares_and_dates` | `-` | `PASSED` | - |
| `TC-057` | `tests/unit/test_generation_config.py::test_offers_and_effects_config_validation` | `-` | `PASSED` | - |
| `TC-058` | `tests/unit/test_generation_world.py::test_1_determinism_same_and_different_seed` | `FR-01` | `PASSED` | - |
| `TC-059` | `tests/unit/test_generation_world.py::test_2_integrity_foreign_keys_ids_chains_and_churn_cutoff` | `-` | `PASSED` | - |
| `TC-060` | `tests/unit/test_generation_world.py::test_3_churn_rate_types_plan_changes_and_seasonal` | `AC-02` | `PASSED` | - |
| `TC-061` | `tests/unit/test_generation_world.py::test_4_usage_decay_signal_loud_voluntary_vs_retained` | `-` | `PASSED` | - |
| `TC-062` | `tests/unit/test_generation_world.py::test_5_reconciliation_billing_and_usage` | `RULE-09` | `PASSED` | - |
| `TC-063` | `tests/unit/test_generation_world.py::test_6_involuntary_churners_billing_sequence` | `-` | `PASSED` | - |
| `TC-064` | `tests/unit/test_generation_world.py::test_7_churn_outcome_2025_consistency` | `FR-05` | `PASSED` | - |
| `TC-065` | `tests/unit/test_generation_world.py::test_8_latent_isolation` | `RULE-08` | `PASSED` | - |
| `TC-066` | `tests/unit/test_generation_world.py::test_reusable_generate_customer_months` | `-` | `PASSED` | - |
| `TC-067` | `tests/unit/test_generation_world.py::test_load_world_strict_rejects_extra_or_missing_not_null_columns` | `-` | `PASSED` | - |
| `TC-068` | `tests/unit/test_generation_world.py::test_hidden_segment_depends_on_untreated_churn` | `-` | `PASSED` | - |
| `TC-069` | `tests/unit/test_ids.py::test_exact_example_ids` | `-` | `PASSED` | - |
| `TC-070` | `tests/unit/test_ids.py::test_customer_id_boundaries` | `-` | `PASSED` | - |
| `TC-071` | `tests/unit/test_ids.py::test_parse_helpers` | `-` | `PASSED` | - |
| `TC-072` | `tests/unit/test_ids.py::test_subscription_id_boundaries` | `-` | `PASSED` | - |
| `TC-073` | `tests/unit/test_ids.py::test_other_id_boundaries` | `-` | `PASSED` | - |
| `TC-074` | `tests/unit/test_ids.py::test_id_determinism` | `-` | `PASSED` | - |
| `TC-075` | `tests/unit/test_model.py::test_model_determinism_and_p0_2025_alignment` | `FR-06` | `PASSED` | - |
| `TC-076` | `tests/unit/test_pipeline.py::test_pipeline_determinism_and_base_hashes` | `RULE-12` | `PASSED` | - |
| `TC-077` | `tests/unit/test_repro.py::test_repro_compare_identical_passes` | `AC-12` | `PASSED` | - |
| `TC-078` | `tests/unit/test_repro.py::test_repro_compare_fake_row_count_mismatch` | `-` | `PASSED` | - |
| `TC-079` | `tests/unit/test_repro.py::test_repro_compare_fake_file_hash_mismatch` | `-` | `PASSED` | - |
| `TC-080` | `tests/unit/test_repro.py::test_repro_compare_fake_latent_hash_mismatch` | `-` | `PASSED` | - |
| `TC-081` | `tests/unit/test_repro.py::test_repro_compare_fake_aggregate_mismatch` | `-` | `PASSED` | - |
| `TC-082` | `tests/unit/test_rng.py::test_same_seed_gives_same_draws` | `NFR-01` | `PASSED` | - |
| `TC-083` | `tests/unit/test_rng.py::test_different_names_give_different_draws` | `-` | `PASSED` | - |
| `TC-084` | `tests/unit/test_rng.py::test_order_independence_named_streams` | `-` | `PASSED` | - |
| `TC-085` | `tests/unit/test_rng.py::test_different_master_seed_gives_different_values` | `-` | `PASSED` | - |
| `TC-086` | `tests/unit/test_rng.py::test_entity_stream_independence` | `-` | `PASSED` | - |
| `TC-087` | `tests/unit/test_rng.py::test_rng_input_validation` | `-` | `PASSED` | - |
| `TC-088` | `tests/unit/test_schema.py::test_tables_exist` | `FR-02` | `PASSED` | - |
| `TC-089` | `tests/unit/test_schema.py::test_foreign_keys_enforced` | `-` | `PASSED` | - |
| `TC-090` | `tests/unit/test_schema.py::test_unique_constraints` | `-` | `PASSED` | - |
| `TC-091` | `tests/unit/test_schema.py::test_enum_and_check_constraints` | `-` | `PASSED` | - |
| `TC-092` | `tests/unit/test_schema.py::test_state_event_append_only` | `RULE-07` | `PASSED` | - |
| `TC-093` | `tests/unit/test_schema.py::test_anomaly_shapes_accepted` | `-` | `PASSED` | - |
| `TC-094` | `tests/unit/test_schema_constraints.py::test_orphan_foreign_keys` | `-` | `PASSED` | - |
| `TC-095` | `tests/unit/test_schema_constraints.py::test_enum_bad_values` | `-` | `PASSED` | - |
| `TC-096` | `tests/unit/test_schema_constraints.py::test_subscription_end_date_check` | `-` | `PASSED` | - |
| `TC-097` | `tests/unit/test_schema_constraints.py::test_churn_outcome_checks` | `RULE-03` | `PASSED` | - |
| `TC-098` | `tests/unit/test_schema_constraints.py::test_campaign_contact_checks` | `-` | `PASSED` | - |
| `TC-099` | `tests/unit/test_schema_constraints.py::test_column_name_prohibited_substrings` | `-` | `PASSED` | - |
| `TC-100` | `tests/unit/test_schema_constraints.py::test_id_format_pk_check` | `-` | `PASSED` | - |
| `TC-101` | `tests/unit/test_services.py::test_list_customers_filters_and_limit` | `-` | `PASSED` | - |
| `TC-102` | `tests/unit/test_services.py::test_customer_360_shape` | `-` | `PASSED` | - |
| `TC-103` | `tests/unit/test_services.py::test_campaign_summary` | `-` | `PASSED` | - |
| `TC-104` | `tests/unit/test_services.py::test_load_report` | `-` | `PASSED` | - |
| `TC-105` | `tests/unit/test_services.py::test_readonly_connection_rejects_insert` | `-` | `PASSED` | - |
| `TC-106` | `tests/unit/test_services.py::test_services_source_scan_no_forbidden_strings` | `-` | `PASSED` | - |
| `TC-107` | `tests/unit/test_simulation.py::test_simulation_saves_and_invariants` | `FR-13` | `PASSED` | - |
| `TC-108` | `tests/unit/test_simulation.py::test_simulation_multiple_saves_forced_persuadable` | `-` | `PASSED` | - |
| `TC-109` | `tests/unit/test_traceability.py::test_spec_and_matrix_traceability_sync` | `-` | `PASSED` | - |
| `TC-110` | `tests/unit/test_validation_checks.py::test_valid_starter_world_zero_findings` | `AC-05` | `PASSED` | - |
| `TC-111` | `tests/unit/test_validation_checks.py::test_negative_duplicate_pk_row` | `-` | `PASSED` | - |
| `TC-112` | `tests/unit/test_validation_checks.py::test_negative_orphan_fk` | `-` | `PASSED` | - |
| `TC-113` | `tests/unit/test_validation_checks.py::test_negative_invalid_enum` | `-` | `PASSED` | - |
| `TC-114` | `tests/unit/test_validation_checks.py::test_negative_invalid_id_format` | `-` | `PASSED` | - |
| `TC-115` | `tests/unit/test_validation_checks.py::test_negative_end_date_before_start_date` | `-` | `PASSED` | - |
| `TC-116` | `tests/unit/test_validation_checks.py::test_negative_sub_chain_gap` | `-` | `PASSED` | - |
| `TC-117` | `tests/unit/test_validation_checks.py::test_negative_snapshot_outside_subscription` | `-` | `PASSED` | - |
| `TC-118` | `tests/unit/test_validation_checks.py::test_negative_event_after_churn` | `-` | `PASSED` | - |
| `TC-119` | `tests/unit/test_validation_checks.py::test_negative_payment_amount_different_from_invoice` | `-` | `PASSED` | - |
| `TC-120` | `tests/unit/test_validation_checks.py::test_negative_wrong_balance` | `-` | `PASSED` | - |
| `TC-121` | `tests/unit/test_validation_checks.py::test_negative_missing_key_in_csv_copy` | `-` | `PASSED` | - |
| `TC-122` | `tests/unit/test_validation_enums.py::test_enums_match_schema_sql_check_clauses` | `-` | `PASSED` | - |
| `TC-123` | `tests/unit/test_validation_enums.py::test_allowed_state_transitions_defined` | `-` | `PASSED` | - |

## 3. Operational Checks

The following operational CLI workflows were executed against starter scale in an isolated test run:

| Subcommand Workflow | Exit Code | Operational Status |
| :--- | :---: | :---: |
| `python -m churnexp validate --scale starter` | `0` | `PASS` |
| `python -m churnexp audit --scale starter` | `0` | `PASS` |
| `python -m churnexp repro-check --scale starter` | `0` | `PASS` |
| `python -m churnexp all --scale starter` | `0` | `PASS` |
