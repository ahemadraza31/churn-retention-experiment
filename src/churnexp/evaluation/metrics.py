"""Out-of-time model evaluation on the untreated cohort (ADR-012)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping
import numpy as np
import pandas as pd

from churnexp.modeling.metrics import compute_metrics
from churnexp.validation.report import Finding


def _round_float(val: float) -> float:
    return round(float(val), 6)


def _compute_band_classification_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    is_high_band: np.ndarray,
    include_brier: bool = False,
) -> dict[str, Any]:
    n = int(len(y_true))
    positives = int(np.sum(y_true == 1))
    base_rate = (positives / float(n)) if n > 0 else 0.0

    if n > 0 and len(np.unique(y_true)) >= 2:
        base_m = compute_metrics(y_true, y_score)
        roc_auc: float | None = _round_float(base_m["roc_auc"])
        brier_val = (
            _round_float(float(np.mean((y_score - y_true) ** 2))) if n > 0 else 0.0
        )
    else:
        roc_auc = None
        brier_val = (
            _round_float(float(np.mean((y_score - y_true) ** 2))) if n > 0 else 0.0
        )

    tp = int(np.sum((is_high_band == 1) & (y_true == 1)))
    fp = int(np.sum((is_high_band == 1) & (y_true == 0)))
    fn = int(np.sum((is_high_band == 0) & (y_true == 1)))
    tn = int(np.sum((is_high_band == 0) & (y_true == 0)))

    precision = (tp / float(tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / float(tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (
        (2.0 * precision * recall / (precision + recall))
        if (precision + recall) > 0.0
        else 0.0
    )
    precision_lift = (precision / base_rate) if base_rate > 0.0 else 0.0

    out: dict[str, Any] = {
        "n": n,
        "positives": positives,
        "base_rate": _round_float(base_rate),
        "roc_auc": roc_auc,
        "high_band_decision_rule": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": _round_float(precision),
            "recall": _round_float(recall),
            "f1": _round_float(f1),
            "precision_lift": _round_float(precision_lift),
        },
    }
    if include_brier:
        out["brier_score"] = brier_val
    return out


def evaluate_model_metrics(
    tables: Mapping[str, pd.DataFrame],
    detector_findings: list[Finding],
    assignment_date: date | str = "2026-01-05",
    outcome_window_days: int = 90,
    model_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate 2026 model discrimination and calibration on the unflagged untreated cohort."""
    flagged_cids: set[str] = {
        str(f.evidence["customer_id"])
        for f in detector_findings
        if "customer_id" in f.evidence and f.evidence["customer_id"]
    }

    assign_dt = (
        assignment_date
        if isinstance(assignment_date, date)
        else date.fromisoformat(str(assignment_date)[:10])
    )
    cutoff_90d_str = (assign_dt + timedelta(days=int(outcome_window_days))).isoformat()

    rs_df = tables.get("risk_score", pd.DataFrame())
    churn_df = tables.get("churn_outcome", pd.DataFrame())
    cc_df = tables.get("campaign_contact", pd.DataFrame())

    # Identify TREATMENT-assigned customers
    if not cc_df.empty:
        treatment_cids = set(
            cc_df.loc[
                cc_df["experiment_group"] == "TREATMENT", "customer_id"
            ].astype(str)
        )
    else:
        treatment_cids = set()

    if rs_df.empty or churn_df.empty:
        empty_m = _compute_band_classification_metrics(
            np.array([], dtype=np.int64),
            np.array([], dtype=np.float64),
            np.array([], dtype=np.int64),
            include_brier=True,
        )
        return {
            "cohort": "untreated_2026_unflagged",
            "label_180d": empty_m,
            "label_90d": _compute_band_classification_metrics(
                np.array([], dtype=np.int64),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.int64),
                include_brier=False,
            ),
            "in_sample_model_info": model_info or {},
        }

    churn_2026 = churn_df[churn_df["cycle_year"].astype(int) == 2026].copy()
    merged = (
        rs_df.merge(
            churn_2026[["customer_id", "churned", "churn_date"]],
            on="customer_id",
            how="inner",
        )
        .sort_values("customer_id", kind="mergesort")
        .reset_index(drop=True)
    )

    keep_mask = (~merged["customer_id"].astype(str).isin(treatment_cids)) & (
        ~merged["customer_id"].astype(str).isin(flagged_cids)
    )
    cohort_df = merged[keep_mask].reset_index(drop=True)

    y_score = cohort_df["score"].astype(float).to_numpy(dtype=np.float64)
    is_high = (cohort_df["band"].astype(str) == "HIGH").to_numpy(dtype=np.int64)
    y_180d = cohort_df["churned"].astype(int).to_numpy(dtype=np.int64)

    y_90d_list: list[int] = []
    for row in cohort_df.itertuples(index=False):
        if int(row.churned) == 1:
            c_val = getattr(row, "churn_date", None)
            c_str = (
                ""
                if c_val is None or pd.isna(c_val) or str(c_val) == ""
                else str(c_val)[:10]
            )
            y_90d_list.append(1 if (c_str and c_str < cutoff_90d_str) else 0)
        else:
            y_90d_list.append(0)
    y_90d = np.array(y_90d_list, dtype=np.int64)

    metrics_180d = _compute_band_classification_metrics(
        y_true=y_180d,
        y_score=y_score,
        is_high_band=is_high,
        include_brier=True,
    )
    metrics_90d = _compute_band_classification_metrics(
        y_true=y_90d,
        y_score=y_score,
        is_high_band=is_high,
        include_brier=False,
    )

    return {
        "cohort": "untreated_2026_unflagged",
        "cutoff_90d_date": cutoff_90d_str,
        "label_180d": metrics_180d,
        "label_90d": metrics_90d,
        "in_sample_model_info": model_info or {},
    }

