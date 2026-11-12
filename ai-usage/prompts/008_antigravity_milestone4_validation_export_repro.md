# Prompt 008: Milestone 4 Validation Suite, Exporters & Reproducibility Check

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Milestone 4 (Data Quality, Export & Reproducibility)
- **Task / Scope**: 18 structural and temporal data validation checks, multi-format export (CSV, JSON, SQL seed), cryptographic manifests, and automated reproducibility comparison.

## Prompt Text

```text
Execute Milestone 4: Validation, Export & Reproducibility.
1. Implement src/churnexp/validation/checks.py with 18 automated rules covering primary key uniqueness, foreign key integrity, allowed enums, date ordering, sub-chain continuity, balance reconciliation, and cross-file row counts.
2. Implement src/churnexp/io/exporters.py exporting tables to CSV, formatted JSON, and SQL seed data with SHA-256 manifests (src/churnexp/io/manifest.py).
3. Implement src/churnexp/repro.py running two independent pipeline generations under differing PYTHONHASHSEED environments and verifying bitwise identical checksums across all exports.
4. Wire CLI commands: churnexp validate, churnexp export, churnexp repro-check.
5. Provide unit tests in tests/unit/test_validation_checks.py, test_export.py, and test_repro.py.
```

## Orchestrator Review & Action

Tested `python -m churnexp repro-check --scale starter` in personal terminal. Confirmed that all 18 validation rules pass with 0 findings on clean baseline data. Verified that exported CSV and JSON files match the SQLite tables byte-for-byte. Committed Milestone 4.

