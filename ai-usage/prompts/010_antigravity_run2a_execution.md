# Prompt 010: Run 2A Implementation Execution

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Run 2A Execution
- **Task / Scope**: Implementing feature extraction, model training, risk scoring, eligibility engine, randomized assignment, counterfactual simulation, and pipeline orchestration.

## Prompt Text

```text
Execute Run 2A: Features, Model, Eligibility, Experiment Assignment & Simulation.
1. Implement src/churnexp/features/builder.py: extract backwards-looking features for P0 (2025-07-01) and P (2026-01-01) with zero lookahead.
2. Implement src/churnexp/modeling/train.py and score.py: train Logistic Regression at P0, export model weights and metrics, and score accounts at P into risk bands.
3. Implement src/churnexp/eligibility/catalog.py and rules.py: evaluate ER-001 through ER-007, recording every evaluation to rule_evaluation.csv.
4. Implement src/churnexp/experiment/assign.py: assign planned offers, then stratify by risk band and randomly assign 50/50 to TREATMENT vs CONTROL (WITHHELD).
5. Implement src/churnexp/experiment/simulate.py: counterfactual simulation saving persuadable treatment customers and generating post-campaign usage/events.
6. Provide tests in tests/unit/test_features.py, test_model.py, test_eligibility.py, test_assignment.py, and test_simulation.py.
```

## Orchestrator Review & Action

Ran all tests locally. Inspected `test_mutate_the_future_leakage_defense` to verify that corrupt future data injected after $P$ leaves extracted features untouched. Verified that control group contacts preserve their planned offer with status `WITHHELD`. Committed Run 2A.

