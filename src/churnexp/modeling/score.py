"""Churn risk scoring, ranking, and risk-band assignment."""

import pandas as pd
from sklearn.pipeline import Pipeline

from churnexp.modeling.train import prepare_feature_frame

RISK_SCORE_COLUMNS: list[str] = [
    "score_id",
    "customer_id",
    "as_of_date",
    "model_version",
    "score",
    "band",
    "rank",
]


def format_risk_score_id(customer_id: str, as_of_date: str) -> str:
    """Format risk_score PK matching schema.sql GLOB: RS-CUS-000001-YYYY-MMDD."""
    dt_clean = str(as_of_date).strip()
    # Expect YYYY-MM-DD -> YYYY-MMDD
    if len(dt_clean) == 10 and dt_clean[4] == "-" and dt_clean[7] == "-":
        yyyy = dt_clean[:4]
        mmdd = dt_clean[5:7] + dt_clean[8:10]
    elif len(dt_clean) == 8 and dt_clean.isdigit():
        yyyy = dt_clean[:4]
        mmdd = dt_clean[4:8]
    else:
        raise ValueError(f"Invalid as_of_date format for risk_score ID: {as_of_date!r}")
    return f"RS-{customer_id}-{yyyy}-{mmdd}"


def score(
    model: Pipeline,
    features_P: pd.DataFrame,
    high_share: float = 0.15,
    medium_share: float = 0.20,
    model_version: str = "logreg-v1",
) -> pd.DataFrame:
    """Score customers active at P, round to 6 decimals, rank (1=highest, tie-break customer_id), and assign bands."""
    if features_P.empty:
        return pd.DataFrame(columns=RISK_SCORE_COLUMNS)

    sorted_feats = features_P.sort_values("customer_id", kind="mergesort").reset_index(
        drop=True
    )
    X = prepare_feature_frame(sorted_feats)
    probs = model.predict_proba(X)[:, 1]
    rounded_scores = [round(float(p), 6) for p in probs]

    cids = sorted_feats["customer_id"].astype(str).tolist()
    as_of_dates = sorted_feats["as_of_date"].astype(str).tolist()

    # Order by (-score, customer_id) for deterministic rank 1..N
    indexed = list(range(len(cids)))
    indexed.sort(key=lambda idx: (-rounded_scores[idx], cids[idx]))

    n_total = len(cids)
    n_high = int(round(n_total * float(high_share)))
    n_med = int(round(n_total * float(medium_share)))

    ranks = [0] * n_total
    bands = ["LOW"] * n_total

    for rank_pos, orig_idx in enumerate(indexed, start=1):
        ranks[orig_idx] = rank_pos
        if rank_pos <= n_high:
            bands[orig_idx] = "HIGH"
        elif rank_pos <= n_high + n_med:
            bands[orig_idx] = "MEDIUM"
        else:
            bands[orig_idx] = "LOW"

    rows = [
        {
            "score_id": format_risk_score_id(cids[i], as_of_dates[i]),
            "customer_id": cids[i],
            "as_of_date": as_of_dates[i],
            "model_version": model_version,
            "score": rounded_scores[i],
            "band": bands[i],
            "rank": ranks[i],
        }
        for i in range(n_total)
    ]

    df = pd.DataFrame(rows, columns=RISK_SCORE_COLUMNS)
    return df.sort_values("score_id", kind="mergesort").reset_index(drop=True)

