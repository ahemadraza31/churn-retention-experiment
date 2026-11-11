# Prompt 002: Phase 2 Architecture Package Proposal

- **AI Tool**: Claude (Technical Lead)
- **Date/Time**: 2026-11-11 10:15 IST
- **Task / Scope**: Formulation of the Phase 2 Architecture Package, including pipeline design, ADR-001 through ADR-012, entity model (ERD), schema column definitions, eligibility rule catalogue (ER-001 - ER-007), feature engineering specifications, CLI/API/UI interfaces, testing strategy, and implementation roadmap.

## Prompt Text

```text
Develop the Phase 2 Architecture Package for the Churn Detection and Retention Offer Experiment.
The package must provide:
1. Architecture in one picture (monolith flow diagram from config through simulation, modeling, eligibility, randomization, anomalies, validation, evaluation, and serving).
2. The key design for data honesty: ADR-004 (temporal design with P0=2025-07-01 and P=2026-01-01), ADR-005 (latent potential outcomes in ground truth), ADR-007 (planned-offer randomization and ITT lift), and ADR-012 (model evaluation on untreated cohort only).
3. Complete Architecture Decision Records (ADR-001 through ADR-012).
4. Final technology stack specification.
5. Entity model (ERD) covering all core domain and tracking tables.
6. Database schema with column-level constraints and business rule demarcation (ADR-002).
7. Eligibility catalogue (ER-001 to ER-007) with financial margin math.
8. Feature extraction rules and automated leakage proof test.
9. Application interfaces: CLI commands, FastAPI endpoints, Streamlit actor pages.
10. Project directory layout.
11. Testing strategy across all layers.
12. Gated implementation roadmap (M1 to M12) with contingency cut order.
```

## Review Summary
Reviewed the architecture package in full. Validated the dual-snapshot leakage defense (ADR-004), planned-offer randomization structure (ADR-007), and data commitment strategy (ADR-009). Confirmed the milestone delivery schedule and contingency cut order.
