# Approved Decisions

D1 Timeline: Jan 2025 to Jun 2026 (18 months), prediction date 2026-01-01.
D2 Churn label horizon: 180 days after the prediction date.
D3 Offer outcome window: 90 days after contact.
D4 Overall churn about 12% over 18 months (must stay within 5-20%).
D5 Treatment/control split 50/50, stratified by risk band.
D6 About 40 injected records per anomaly type, parameterized.
D7 Anomaly labels live only in ground_truth, with no issue_type column in main tables.
D8 Three offers: 10% discount, 20% discount, 1 free month, each with cost and margin cap.
D9 Commit the full CSV data if the total is under about 50 MB, otherwise a starter set plus checksums.
Stack: Python 3.11, NumPy/pandas, SQLite, scikit-learn, FastAPI, Streamlit, pytest.
Fixed seed: 20261022.
