# Prompt 013: Run 3 Final Build & QA Specification

- **AI Tool**: Claude (Technical Lead)
- **Phase**: Run 3 Final Build Specification
- **Task / Scope**: Specification for Part A fixes (ADR renumbering, ground truth data dictionary, empty arm lift handling, evaluation report template, validate final line), Part B read-only Streamlit dashboard and domain services layer, Part C QA documents, and Part D reviewer README and scripts.

## Prompt Text

```text
Draft the comprehensive execution instructions for Run 3 (Final Build Run):
- Part A: Fixes (renumber ADR-013..016, update docs/03_data_dictionary.md with exact CSV columns and honest provenance, empty-arm lift null in json and "n/a" in md, dynamic business reading template in evaluation report, validate summary line format, confirm no test assertion weakened).
- Part B: Services (src/churnexp/services/queries.py with mode=ro connections) and Streamlit dashboard (app/streamlit_app.py across 5 personas: Overview, Marketing Ops, Support Agent, Analyst, System Admin).
- Part C: QA Documents (docs/REQUIREMENTS_TRACEABILITY.md covering all FRs, NFRs, ACs; scripts/make_test_report.py generating docs/TEST_REPORT.md).
- Part D: Reviewer README.md, Makefile targets (demo, qa, full), clean clone check script (scripts/clean_clone_check.sh), and docs/FINAL_REPORT.md.
```

## Orchestrator Review & Action

Reviewed and approved the Run 3 scope. Confirmed that replacing FastAPI with a direct read-only services layer and Streamlit avoids unnecessary network overhead while maintaining complete architectural decoupling and read-only isolation. Handed off to Antigravity.

