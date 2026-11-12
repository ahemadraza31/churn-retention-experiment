# Data Source & Provenance Manifest

## 1. Synthetic Provenance Statement
- **100% Synthetic Data**: Every table, record, identifier, timestamp, behavioral metric, and latent variable in `data/` and `output/` is **fully synthetic** and generated deterministically by this repository (`churnexp`).
- **No External Datasets**: No third-party, public, scraped, or proprietary external datasets were used or derived from.
- **Zero Personal Data (PII)**: No real individuals, accounts, organizations, payment instruments, or support transcripts exist anywhere in this repository. No Faker or PII-like strings (names, emails, phone numbers, addresses) are generated.

## 2. Generator Entry Point & Master Seed
- **CLI Entry Point**:
  ```bash
  python -m churnexp generate --scale [starter|full]
  python -m churnexp export --scale [starter|full]
  ```
- **Orchestrator Module**: `src/churnexp/generation/world.py` (`generate_world`, `load_world`, `hash_world`)
- **Master Random Seed**: `20261022` (configured in `config/default.yaml` via `numpy.random.SeedSequence(20261022)` and per-entity substreams in `src/churnexp/rng.py`).
- **Ground-Truth Isolation**: Counterfactual potential outcomes (`hidden_segment`, `untreated_churn_date`, `treated_churn_date`, `true_effect_flag`) are written exclusively to `ground_truth/latent_customer_state.csv` and never appear in the SQLite database or in `csv/`, `json/`, or `sql/` exports.

## 3. Runtime & Dependency Licenses

| Package | Role | License |
| :--- | :--- | :--- |
| **pandas** | Tabular data manipulation and CSV/JSON serialization | BSD-3-Clause |
| **numpy** | Deterministic `SeedSequence` / `PCG64` RNG and numerical arrays | BSD-3-Clause |
| **scikit-learn** | Explainable Logistic Regression and model evaluation metrics | BSD-3-Clause |
| **PyYAML** | YAML configuration parsing (`config/default.yaml`, `config/starter.yaml`) | MIT |
| **Streamlit** | Multi-actor interactive dashboard UI | Apache-2.0 |
| **FastAPI** | Read-only REST API service | MIT |
| **pytest** | Unit, integration, and end-to-end automated test suite | MIT |
