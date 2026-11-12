"""Model evaluation metrics using scikit-learn."""

from typing import Sequence
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


def compute_metrics(
    y_true: Sequence[int] | np.ndarray,
    y_score: Sequence[float] | np.ndarray,
    threshold: float = 0.5,
) -> dict[str, float]:
    """Compute ROC-AUC, precision, recall, and F1 at the given probability threshold."""
    y_t = np.asarray(y_true, dtype=np.int64)
    y_s = np.asarray(y_score, dtype=np.float64)
    y_pred = (y_s >= float(threshold)).astype(np.int64)

    if len(np.unique(y_t)) >= 2:
        auc = float(roc_auc_score(y_t, y_s))
    else:
        auc = 0.0

    prec = float(precision_score(y_t, y_pred, zero_division=0))
    rec = float(recall_score(y_t, y_pred, zero_division=0))
    f1 = float(f1_score(y_t, y_pred, zero_division=0))

    return {
        "roc_auc": round(auc, 6),
        "precision": round(prec, 6),
        "recall": round(rec, 6),
        "f1": round(f1, 6),
    }

