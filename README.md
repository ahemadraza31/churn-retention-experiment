# Churn Detection and Retention Offer Experiment

Identify churn risk from behavioral change using only pre-prediction data, apply eligibility and margin rules, run a randomized treatment/control experiment, and measure incremental retention lift.

**Status**: Phase 2 Approved — Ready for Milestone 1 (Foundation & Skeleton)

---

## Documentation

- [Phase 1: Requirements Specification](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/01_requirements_spec.md)
- [Phase 2: Architecture Package](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/02_architecture.md)
- [Architecture Decision Records & Decisions D1-D9](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/decisions.md)
- [Project Timeline & Milestones](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/docs/TIMELINE.md)
- [AI Usage Log & Disclosure](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/README.md)

---

## Key Architectural Principles

1. **Strict Temporal Integrity (ADR-004)**: Lookback windows strictly enforce `event_date < as_of_date`. Training snapshot at $P_0 = \text{2025-07-01}$ with 180-day labels fully resolved before scoring snapshot $P = \text{2026-01-01}$.
2. **Latent Potential Outcomes (ADR-005)**: Customers possess hidden segments (`persuadable`, `sure-thing`, `lost-cause`) stored in `ground_truth/` to establish an objective causal baseline.
3. **Planned-Offer Randomization (ADR-007)**: Eligible accounts receive a planned offer before 50/50 stratified randomization; control accounts receive `WITHHELD` contacts with their planned offer recorded for valid offer-level lift.
4. **Clean Baseline Evaluation (ADR-012)**: Predictive model evaluation strictly excludes treated accounts whose churn trajectory was influenced by retention interventions.
5. **Blind Anomaly Detection (ADR-002, ADR-006)**: Operational anomalies (A-D) are detected blind to ground truth; auditing occurs downstream in an isolated audit module.

---

## Setup & Execution (Roadmap)

```bash
# Setup virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run complete pipeline (Starter scale: 1,000 subscribers)
python -m churnexp all --scale starter

# Launch UI
streamlit run app/streamlit_app.py

# Launch FastAPI Service
uvicorn churnexp.api.main:app --reload --port 8000

# Execute full test suite
pytest
```

---

## AI Usage Disclosure

All prompts, model outputs, and engineering reviews are tracked sequentially under [`ai-usage/`](file:///Users/ahemadrajapathan/Projects/churn-retention-experiment/ai-usage/README.md) with full transparency on AI collaboration (Claude as technical lead, Google Antigravity as implementation agent).
