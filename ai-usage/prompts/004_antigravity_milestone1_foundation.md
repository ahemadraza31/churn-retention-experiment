# Prompt 004: Milestone 1 Foundation

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Milestone 1 (Foundation)
- **Task / Scope**: Package configuration, deterministic ID generators, seeded RNG streams, and CLI health check.

## Prompt Text

```text
Execute Milestone 1: Foundation.
1. Configure project metadata in pyproject.toml and requirements.txt for pure Python 3.11 with zero external daemons.
2. Implement src/churnexp/config.py to load config/default.yaml and config/starter.yaml, enforcing temporal invariants (data_start < train_as_of < score_as_of < data_end).
3. Implement src/churnexp/ids.py with regex validation and zero-padded ID formatters (CUS-000001, SUB-CUS-000001-01, SNAP-SUB-CUS-000001-01-2026-01, OFF-2026-000001, CHURN-CUS-000001-2026).
4. Implement src/churnexp/rng.py using numpy.random.SeedSequence(20261022) with order-independent child stream derivation keyed by entity name and index.
5. Implement src/churnexp/cli.py providing health check and command stubs (generate, export, validate, evaluate, audit, repro-check).
6. Provide comprehensive unit tests in tests/unit/test_config.py, test_ids.py, test_rng.py, and test_cli.py.
```

## Orchestrator Review & Action

Verified all tests pass in local environment (`pytest -q`). Confirmed that child RNG streams are order-independent and deterministic. Tested `python -m churnexp health --scale starter` in personal terminal. Personally committed Milestone 1 changes.

