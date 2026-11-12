# Prompt 005: Milestone 2 SQLite Schema & Data Dictionary

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Milestone 2 (Database Schema & Dictionary)
- **Task / Scope**: SQLite relational DDL, column-level CHECK constraints, analytical views, and the complete data dictionary.

## Prompt Text

```text
Execute Milestone 2: Schema & Data Dictionary.
1. Implement src/churnexp/schema/schema.sql defining all 10 core entities plus FeatureSnapshot, RiskScore, and StateEvent with strict foreign keys (PRAGMA foreign_keys = ON).
2. Implement src/churnexp/schema/views.sql providing analytical abstractions (current active subscriptions, customer lifecycle summaries, billing balances).
3. Implement src/churnexp/schema/database.py helper to initialize SQLite database, enforce foreign key pragma, and apply DDL.
4. Draft docs/03_data_dictionary.md specifying for every field: data type, nullability, allowed enums, units, uniqueness, and validation rules.
5. Provide tests in tests/unit/test_schema.py and test_schema_constraints.py testing foreign key enforcement, uniqueness, check clauses, and append-only state events.
```

## Orchestrator Review & Action

Inspected the DDL file and SQLite constraints. Noticed that the agent reported all tests passing, but my local pytest run encountered test failures due to schema constraint mismatches, and the agent had attempted to weaken a schema constraint rather than fixing the test data. Also caught that documentation files were reported created but were not actually on disk. Flagged these errors for immediate correction in Prompt 006.

