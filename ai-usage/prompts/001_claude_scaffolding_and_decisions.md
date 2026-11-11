# Prompt 001: Initial Scaffolding & Decisions D1-D9

- **AI Tool**: Claude (Technical Lead)
- **Date/Time**: 2026-11-10 23:30 IST
- **Task / Scope**: Project kickoff, foundational timeline scoping, baseline decisions D1-D9, technology stack selection, and AI disclosure scaffolding.

## Prompt Text

```text
We are starting the churn detection and retention offer experiment project.
Key requirements:
- Design a realistic subscription churn simulation, predictive modeling, eligibility rules, and randomized retention experiment.
- Scope the operational timeline (Jan 2025 to Jun 2026), prediction date 2026-01-01, 180-day churn horizon, 90-day retention window.
- Establish foundational decisions D1 through D9: overall churn target (~12%), 50/50 treatment/control split, anomaly injection scale (~40 per type), ground truth isolation, 3 retention offers, and data footprint strategy.
- Set stack: Python 3.11, pandas, NumPy, scikit-learn, SQLite, FastAPI, Streamlit, pytest.
- Initialize repo scaffolding, README, docs, decisions.md, TIMELINE.md, and AI-usage logging structure.
```

## Review Summary
Reviewed Decisions D1-D9 for feasibility, verified 18-month simulation window and temporal cutoffs, confirmed SQLite and lightweight Python stack without Docker/ORM dependencies.
