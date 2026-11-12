"""Deterministic churn prediction model training (ADR-004)."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_FEATURE_COLS: list[str] = [
    "usage_minutes_3m",
    "usage_minutes_prev3m",
    "usage_ratio_3m_vs_prev3m",
    "last_month_active_days",
    "usage_slope_6m",
    "sessions_6m",
    "failed_payments_6m",
    "days_since_last_failed_payment",
    "outstanding_balance_cents",
    "support_cases_6m",
    "high_severity_cases_6m",
    "cancellation_inquiries_6m",
    "tenure_days",
    "monthly_price_cents",
    "plan_downgrade_6m",
    "is_seasonal",
]

CATEGORICAL_FEATURE_COLS: list[str] = [
    "plan_tier",
    "segment",
    "channel",
]

ALL_MODEL_FEATURE_COLS: list[str] = NUMERIC_FEATURE_COLS + CATEGORICAL_FEATURE_COLS


def prepare_feature_frame(features_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare a deterministic feature DataFrame with proper dtypes for sklearn."""
    out = features_df[ALL_MODEL_FEATURE_COLS].copy()
    for col in NUMERIC_FEATURE_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
    for col in CATEGORICAL_FEATURE_COLS:
        out[col] = out[col].astype(str)
    return out


def train_model(
    features_P0: pd.DataFrame,
    churn_outcome_2025: pd.DataFrame,
) -> Pipeline:
    """Train a deterministic logistic regression pipeline on P0 features and 2025 labels.

    - Imputes NULL `days_since_last_failed_payment` (and any numeric NaN) with constant 999
      with no missingness indicator.
    - Standardizes all numeric columns with StandardScaler.
    - One-hot encodes `plan_tier`, `segment`, `channel` with fixed category ordering.
    - Fits `LogisticRegression(max_iter=1000, C=1.0, solver='lbfgs', random_state=20261022)`.
    - Uses ONLY cycle_year == 2025 churn_outcome rows aligned to P0 features.
    """
    if features_P0.empty:
        raise ValueError("features_P0 must not be empty")
    if churn_outcome_2025.empty:
        raise ValueError("churn_outcome_2025 must not be empty")

    as_of_vals = set(features_P0["as_of_date"].astype(str).unique())
    if len(as_of_vals) != 1:
        raise ValueError(
            f"features_P0 must have a single as_of_date, got {sorted(as_of_vals)}"
        )

    outcomes_2025 = churn_outcome_2025[
        churn_outcome_2025["cycle_year"].astype(int) == 2025
    ].copy()
    if outcomes_2025.empty:
        raise ValueError("No cycle_year == 2025 rows found in churn_outcome_2025")

    pred_vals = set(outcomes_2025["prediction_date"].astype(str).unique())
    if pred_vals != as_of_vals:
        raise ValueError(
            f"features_P0 as_of_date {sorted(as_of_vals)} does not match "
            f"2025 outcome prediction_date {sorted(pred_vals)}"
        )

    merged = pd.merge(
        features_P0,
        outcomes_2025[["customer_id", "churned"]],
        on="customer_id",
        how="inner",
    ).sort_values("customer_id", kind="mergesort").reset_index(drop=True)

    if merged.empty:
        raise ValueError("No matching customer_id rows between features_P0 and churn_outcome_2025")

    X = prepare_feature_frame(merged)
    y = merged["churned"].astype(int).to_numpy(dtype=np.int64)

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=999.0, add_indicator=False)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = OneHotEncoder(
        categories=[
            ["BASIC", "STANDARD", "PREMIUM"],
            ["CONSUMER", "SMB"],
            ["ORGANIC", "PAID", "PARTNER", "REFERRAL"],
        ],
        handle_unknown="ignore",
        sparse_output=False,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURE_COLS),
            ("cat", categorical_transformer, CATEGORICAL_FEATURE_COLS),
        ],
        remainder="drop",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    C=1.0,
                    solver="lbfgs",
                    random_state=20261022,
                ),
            ),
        ]
    )
    pipeline.fit(X, y)
    return pipeline

