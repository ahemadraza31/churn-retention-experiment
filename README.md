# Churn Detection and Retention Offer Experiment

Identify churn risk from behavioral change using only pre-prediction data, apply eligibility and margin rules, run a randomized treatment/control experiment, and measure incremental retention lift.

**Status**: Milestone 4 Complete (Generators, Validators, Exporters & Reproducibility)

---

## Setup

Create the Python 3.11 virtual environment, install dependencies, and register editable package `churnexp`:

```bash
make setup
```

Or manually:
```bash
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Run

Run the CLI health check, inspect configuration presets, generate synthetic data, export datasets, validate rules, and verify reproducibility:

```bash
# Verify environment, package, config loading, and sqlite3 functionality
make health

# Or invoke directly via module runner
python -m churnexp health --scale starter
python -m churnexp health --scale full

# View CLI options and available subcommands
python -m churnexp --help

# Inspect resolved configuration
python -m churnexp config --scale starter

# Generate synthetic untreated world into output/<scale>/churnexp.db
python -m churnexp generate --scale starter
python -m churnexp generate --scale full

# Export database tables to data/<scale>/ (csv,json,sql for starter; csv for full)
python -m churnexp export --scale starter
python -m churnexp export --scale full

# Validate structural, temporal, reconciliation, and cross-file rules
python -m churnexp validate --scale starter
python -m churnexp validate --scale full

# Verify two-run subprocess reproducibility (PYTHONHASHSEED=1 vs 2)
python -m churnexp repro-check --scale starter
python -m churnexp repro-check --scale full
```

---

## Test

Run the automated test suite with pytest:

```bash
make test
```

Or invoke pytest directly:
```bash
.venv/bin/pytest -q
```

---

## Documentation

- [Phase 1: Requirements Specification](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/01_requirements_spec.md)
- [Phase 2: Architecture Package](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/02_architecture.md)
- [Architecture Decision Records & Decisions D1-D9](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/decisions.md)
- [Project Timeline & Milestones](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/TIMELINE.md)
- [Data Dictionary](docs/03_data_dictionary.md)
- [AI Usage Log & Disclosure](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/README.md)

---

## Key Architectural Principles

1. **Strict Temporal Integrity (ADR-004)**: Lookback windows strictly enforce `event_date < as_of_date`. Training snapshot at $P_0 = \text{2025-07-01}$ with 180-day labels fully resolved before scoring snapshot $P = \text{2026-01-01}$.
2. **Latent Potential Outcomes (ADR-005)**: Customers possess hidden segments (`persuadable`, `sure-thing`, `lost-cause`) stored in `ground_truth/` to establish an objective causal baseline.
3. **Planned-Offer Randomization (ADR-007)**: Eligible accounts receive a planned offer before 50/50 stratified randomization; control accounts receive `WITHHELD` contacts with their planned offer recorded for valid offer-level lift.
4. **Clean Baseline Evaluation (ADR-012)**: Predictive model evaluation strictly excludes treated accounts whose churn trajectory was influenced by retention interventions.
5. **Blind Anomaly Detection (ADR-002, ADR-006)**: Operational anomalies (A-D) are detected blind to ground truth; auditing occurs downstream in an isolated audit module.

---

## AI Usage Disclosure

All prompts, model outputs, and engineering reviews are tracked sequentially under [`ai-usage/`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/README.md) with full transparency on AI collaboration (Claude as technical lead, Google Antigravity as implementation agent).
