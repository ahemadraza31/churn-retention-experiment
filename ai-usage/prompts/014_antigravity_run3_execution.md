# Prompt 014: Run 3 Final Build Execution

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Run 3 Execution
- **Task / Scope**: Implementing Part A fixes (ADR renumbering, empty-arm handling, evaluation reading), Part B domain services (`src/churnexp/services/queries.py`) and Streamlit actor dashboard (`app/streamlit_app.py`), Part C requirements traceability and test report script, and Part D complete README, Makefile targets, and clean clone check script.

## Prompt Text

```text
Execute Run 3: The Final Build Run.
- PART A: Fixes (A1 ADR-013..016 renumbering, A2 data dictionary sync test, A3 empty-arm lift null and small sample SMD note, A4 evaluation template & integer cents, A5 validate line format, A6 simulation test assertion diff check).
- PART B: Read-only services (src/churnexp/services/queries.py with mode=ro connections) and Streamlit dashboard (app/streamlit_app.py for Overview, Marketing Ops, Support Agent, Analyst, System Admin). Test with AppTest.
- PART C: docs/REQUIREMENTS_TRACEABILITY.md and scripts/make_test_report.py (generating docs/TEST_REPORT.md).
- PART D: Comprehensive README.md, Makefile targets (setup, test, health, demo, app, qa, full), scripts/clean_clone_check.sh, and docs/FINAL_REPORT.md.
```

## Orchestrator Review & Action

Executed `make qa` in local terminal, confirming all 123 tests pass and operational CLI checks exit with code 0. Inspected Streamlit dashboard across all 5 pages. Caught that the agent printed fabricated git history in its pre-flight check, and instructed it to never print unverified command outputs. Personally committed Run 3.

