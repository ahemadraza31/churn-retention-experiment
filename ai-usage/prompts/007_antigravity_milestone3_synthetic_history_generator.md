# Prompt 007: Milestone 3 Synthetic History Generator

- **AI Tool**: Google Antigravity (Implementation Agent)
- **Phase**: Milestone 3 (Synthetic Data Generator)
- **Task / Scope**: Generating customer, subscription, usage snapshot, billing event, and support case history over 18 months with realistic behavioral churn dynamics.

## Prompt Text

```text
Execute Milestone 3: Base Synthetic Data Generator.
1. Implement src/churnexp/generation/world.py generating realistic untreated customer histories over 18 months (2025-01-01 to 2026-06-30).
2. Model customer cohorts across plan tiers (BASIC, STANDARD, PREMIUM), usage decay signals for voluntary churners, payment retry failure cascades for involuntary churners, and seasonal summer spikes.
3. Track non-overlapping subscription versioning (-01, -02) linked by previous_subscription_id.
4. Record state changes to append-only StateEvent.
5. Implement strict table loading and schema validation to ensure child records reference valid parent IDs.
6. Provide unit tests in tests/unit/test_generation_world.py verifying determinism, churn boundaries (5-20%), usage decay separation, billing balance reconciliation, and latent state isolation.
```

## Orchestrator Review & Action

Reviewed generator code to ensure voluntary churners exhibit clear usage decline prior to cancellation. Validated that billing events calculate running balances and that latent states (`persuadable`, `sure-thing`, `lost-cause`) are saved only to `ground_truth/` and never written to the SQLite database. Ran tests and committed Milestone 3.

