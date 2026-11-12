"""Unit tests for churn model training, scoring, and metrics (Step 7 item 3)."""

import pandas as pd
import pytest

from churnexp import ids
from churnexp.config import load_config
from churnexp.features.builder import build_features
from churnexp.generation.world import generate_world
from churnexp.modeling.metrics import compute_metrics
from churnexp.modeling.score import score
from churnexp.modeling.train import prepare_feature_frame, train_model


@pytest.fixture(scope="module")
def starter_cfg():
    return load_config("starter")


@pytest.fixture(scope="module")
def base_world(starter_cfg):
    return generate_world(starter_cfg)


def test_model_determinism_and_p0_2025_alignment(starter_cfg, base_world):
    """Two fits give identical scores; training uses only 2025 labels and P0 features; scores exist for all active at P."""
    p0 = starter_cfg.timeline.train_as_of
    p = starter_cfg.timeline.score_as_of
    lookback = starter_cfg.timeline.feature_lookback_months

    feats_p0 = build_features(base_world.tables, as_of=p0, lookback_months=lookback)
    feats_p = build_features(base_world.tables, as_of=p, lookback_months=lookback)

    # Assert feature as_of_date values match P0 and P
    assert set(feats_p0["as_of_date"]) == {"2025-07-01"}
    assert set(feats_p["as_of_date"]) == {"2026-01-01"}

    churn_2025 = base_world.tables["churn_outcome"]
    assert set(churn_2025["cycle_year"].astype(int)) == {2025}
    assert set(churn_2025["prediction_date"]) == {"2025-07-01"}

    # Reject mismatched as_of_date if someone passes P features with 2025 labels
    with pytest.raises(ValueError, match="does not match"):
        train_model(feats_p, churn_2025)

    model1 = train_model(feats_p0, churn_2025)
    model2 = train_model(feats_p0, churn_2025)

    rs1 = score(
        model1,
        feats_p,
        high_share=starter_cfg.campaign.risk_bands.high_share,
        medium_share=starter_cfg.campaign.risk_bands.medium_share,
    )
    rs2 = score(
        model2,
        feats_p,
        high_share=starter_cfg.campaign.risk_bands.high_share,
        medium_share=starter_cfg.campaign.risk_bands.medium_share,
    )
    pd.testing.assert_frame_equal(rs1, rs2, check_exact=True)

    # Verify scores exist for every customer active at P
    sub_df = base_world.tables["subscription"]
    p_str = p.isoformat()
    active_p_subs = sub_df[
        (sub_df["start_date"].astype(str) < p_str)
        & (sub_df["end_date"].isna() | (sub_df["end_date"].astype(str) >= p_str))
    ]
    expected_active_cids = set(active_p_subs["customer_id"].astype(str))
    assert set(rs1["customer_id"].astype(str)) == expected_active_cids
    assert len(rs1) == len(expected_active_cids)

    # Check ranks 1..N and risk band shares
    assert sorted(rs1["rank"].astype(int).tolist()) == list(range(1, len(rs1) + 1))
    n_high = int(round(len(rs1) * starter_cfg.campaign.risk_bands.high_share))
    n_med = int(round(len(rs1) * starter_cfg.campaign.risk_bands.medium_share))
    assert int((rs1["band"] == "HIGH").sum()) == n_high
    assert int((rs1["band"] == "MEDIUM").sum()) == n_med
    assert int((rs1["band"] == "LOW").sum()) == len(rs1) - n_high - n_med
    assert set(rs1["model_version"]) == {"logreg-v1"}

    # Check training AUC is meaningful (> 0.65)
    merged_p0 = pd.merge(feats_p0, churn_2025[["customer_id", "churned"]], on="customer_id")
    X_p0 = prepare_feature_frame(merged_p0)
    y_p0 = merged_p0["churned"].astype(int).to_numpy()
    p_p0 = model1.predict_proba(X_p0)[:, 1]
    m = compute_metrics(y_p0, p_p0)
    assert m["roc_auc"] > 0.65

