"""End-to-end world + campaign pipeline orchestrator (Run 2A)."""

from datetime import timedelta
import math
from typing import Any
import numpy as np
import pandas as pd

from churnexp.config import Config
from churnexp.eligibility.catalog import build_catalog
from churnexp.eligibility.engine import (
    evaluate_eligibility,
    get_all_eligible_customer_offers,
)
from churnexp.experiment.assign import assign_campaign
from churnexp.experiment.simulate import simulate_outcomes
from churnexp.features.builder import build_features
from churnexp.generation.world import World, generate_world, hash_world
from churnexp.modeling.metrics import compute_metrics
from churnexp.modeling.score import score as score_customers
from churnexp.modeling.train import prepare_feature_frame, train_model
from churnexp.rng import RngFactory

M4_STARTER_REFERENCE_HASH_PREFIXES: dict[str, str] = {
    "customer": "42fceda91e1115b8",
    "subscription": "ff0da53478779b8",
    "usage_snapshot": "66cab0c26503e1a9",
    "billing_event": "bb9ae7b893e5efcb",
    "support_case": "2950fef5fd10e2da",
    "state_event": "bab1f7626566fe46",
    "churn_outcome": "3af349e014bff249",
}


def _compute_smd(vals_t: np.ndarray, vals_c: np.ndarray) -> float:
    if len(vals_t) < 2 or len(vals_c) < 2:
        return 0.0
    mean_t = float(np.mean(vals_t))
    mean_c = float(np.mean(vals_c))
    var_t = float(np.var(vals_t, ddof=1))
    var_c = float(np.var(vals_c, ddof=1))
    denom = math.sqrt((var_t + var_c) / 2.0)
    if denom == 0.0:
        return 0.0
    return round(abs(mean_t - mean_c) / denom, 6)


def run_pipeline(cfg: Config) -> World:
    """Run the full untreated world + features + model + eligibility + assignment + simulation pipeline."""
    rng_factory = RngFactory(cfg.seed)

    # 1. Base untreated world
    base_world = generate_world(cfg)
    base_hashes = hash_world(base_world)

    # 2. Features at P0 (train_as_of) and P (score_as_of)
    lookback = int(cfg.timeline.feature_lookback_months)
    features_P0 = build_features(
        base_world.tables,
        as_of=cfg.timeline.train_as_of,
        lookback_months=lookback,
    )
    features_P = build_features(
        base_world.tables,
        as_of=cfg.timeline.score_as_of,
        lookback_months=lookback,
    )
    feature_snapshot_df = (
        pd.concat([features_P0, features_P], ignore_index=True)
        .sort_values(["customer_id", "as_of_date"], kind="mergesort")
        .reset_index(drop=True)
    )

    # 3. Train logistic regression at P0, score all customers active at P
    churn_2025_df = base_world.tables["churn_outcome"]
    model = train_model(features_P0, churn_2025_df)

    # Training metrics at P0
    train_merged = (
        pd.merge(
            features_P0,
            churn_2025_df[["customer_id", "churned"]],
            on="customer_id",
            how="inner",
        )
        .sort_values("customer_id", kind="mergesort")
        .reset_index(drop=True)
    )
    X_train = prepare_feature_frame(train_merged)
    y_train = train_merged["churned"].astype(int).to_numpy(dtype=np.int64)
    p_train = model.predict_proba(X_train)[:, 1]
    train_metrics = compute_metrics(y_train, p_train)

    risk_score_df = score_customers(
        model=model,
        features_P=features_P,
        high_share=cfg.campaign.risk_bands.high_share,
        medium_share=cfg.campaign.risk_bands.medium_share,
        model_version="logreg-v1",
    )

    # 4. Offer catalog and eligibility evaluation as of assignment_date
    offer_df, eligibility_rule_df, offer_eligibility_rule_df = build_catalog(cfg)
    rule_evaluation_df = evaluate_eligibility(
        tables=base_world.tables,
        risk_scores=risk_score_df,
        offers=offer_df,
        rules=eligibility_rule_df,
        as_of=cfg.campaign.assignment_date,
    )
    eligible_offers_by_cid = get_all_eligible_customer_offers(rule_evaluation_df)

    # 5. Planned offer and stratified randomized assignment
    campaign_contact_df = assign_campaign(
        eligible_offers_by_cid=eligible_offers_by_cid,
        risk_scores=risk_score_df,
        cfg=cfg,
        rng_factory=rng_factory,
    )

    # 6. Counterfactual & observed outcome simulation + state_event rebuild
    sim_res = simulate_outcomes(
        base_tables=base_world.tables,
        base_latent=base_world.latent,
        campaign_contacts=campaign_contact_df,
        risk_scores=risk_score_df,
        cfg=cfg,
        rng_factory=rng_factory,
    )

    final_tables = dict(sim_res.tables)
    final_tables["offer"] = offer_df
    final_tables["eligibility_rule"] = eligibility_rule_df
    final_tables["offer_eligibility_rule"] = offer_eligibility_rule_df
    final_tables["feature_snapshot"] = feature_snapshot_df
    final_tables["risk_score"] = risk_score_df
    final_tables["rule_evaluation"] = rule_evaluation_df

    # Compute summary statistics for CLI and tests
    band_counts = {
        b: int((risk_score_df["band"] == b).sum()) for b in ("HIGH", "MEDIUM", "LOW")
    }

    rule_fail_counts: dict[str, int] = {}
    for r_num in range(1, 7):
        rid = f"ER-{r_num:03d}"
        r_sub = rule_evaluation_df[rule_evaluation_df["rule_id"] == rid]
        rule_fail_counts[rid] = int((r_sub["passed"].astype(int) == 0).sum())

    er007_sub = rule_evaluation_df[rule_evaluation_df["rule_id"] == "ER-007"]
    rule_fail_counts["ER-007_eval_rows"] = int(
        (er007_sub["passed"].astype(int) == 0).sum()
    )
    er007_pass_by_cid = er007_sub.groupby("customer_id")["passed"].sum()
    rule_fail_counts["ER-007_all_offers"] = int((er007_pass_by_cid == 0).sum())
    for oid in offer_df["offer_id"].astype(str).tolist():
        o_sub = er007_sub[er007_sub["offer_id"] == oid]
        rule_fail_counts[f"ER-007:{oid}"] = int(
            (o_sub["passed"].astype(int) == 0).sum()
        )

    final_cc = final_tables["campaign_contact"]
    planned_offer_counts: dict[str, int] = {
        oid: int((final_cc["offer_id"] == oid).sum())
        for oid in offer_df["offer_id"].astype(str).tolist()
    }

    stratum_arm_counts: dict[str, dict[str, int]] = {}
    for stratum in ("HIGH", "MEDIUM"):
        s_rows = final_cc[final_cc["stratum"] == stratum]
        stratum_arm_counts[stratum] = {
            "TREATMENT": int((s_rows["experiment_group"] == "TREATMENT").sum()),
            "CONTROL": int((s_rows["experiment_group"] == "CONTROL").sum()),
        }

    # Covariate balance (SMD across arms for risk_score, tenure_days, monthly_price_cents)
    cc_with_covs = (
        final_cc[["customer_id", "experiment_group"]]
        .merge(risk_score_df[["customer_id", "score"]], on="customer_id", how="inner")
        .merge(
            features_P[["customer_id", "tenure_days", "monthly_price_cents"]],
            on="customer_id",
            how="inner",
        )
    )
    t_cov = cc_with_covs[cc_with_covs["experiment_group"] == "TREATMENT"]
    c_cov = cc_with_covs[cc_with_covs["experiment_group"] == "CONTROL"]
    smd_by_cov = {
        "risk_score": _compute_smd(
            t_cov["score"].to_numpy(dtype=np.float64),
            c_cov["score"].to_numpy(dtype=np.float64),
        ),
        "tenure_days": _compute_smd(
            t_cov["tenure_days"].to_numpy(dtype=np.float64),
            c_cov["tenure_days"].to_numpy(dtype=np.float64),
        ),
        "monthly_price_cents": _compute_smd(
            t_cov["monthly_price_cents"].to_numpy(dtype=np.float64),
            c_cov["monthly_price_cents"].to_numpy(dtype=np.float64),
        ),
    }
    max_smd = max(smd_by_cov.values()) if smd_by_cov else 0.0

    # 2026 AUC on customers NOT in TREATMENT
    treatment_cids = set(
        final_cc.loc[final_cc["experiment_group"] == "TREATMENT", "customer_id"].astype(str)
    )
    churn_2026_df = final_tables["churn_outcome"][
        final_tables["churn_outcome"]["cycle_year"].astype(int) == 2026
    ]
    non_treat_eval = (
        risk_score_df[~risk_score_df["customer_id"].isin(treatment_cids)]
        .merge(churn_2026_df[["customer_id", "churned"]], on="customer_id", how="inner")
        .sort_values("customer_id", kind="mergesort")
    )
    non_treat_2026_metrics = compute_metrics(
        non_treat_eval["churned"].astype(int).to_numpy(),
        non_treat_eval["score"].astype(float).to_numpy(),
    )

    # Observed cohort metrics after simulation
    obs_sub_df = final_tables["subscription"]
    obs_vol = int((obs_sub_df["end_reason"] == "VOLUNTARY_CANCEL").sum())
    obs_inv = int((obs_sub_df["end_reason"] == "INVOLUNTARY_CANCEL").sum())
    obs_churned = obs_vol + obs_inv
    n_cust = len(final_tables["customer"])

    pipeline_summary: dict[str, Any] = dict(base_world.summary)
    pipeline_summary.update(
        {
            "base_hashes": base_hashes,
            "observed_n_churned": obs_churned,
            "observed_churn_rate": obs_churned / float(n_cust) if n_cust else 0.0,
            "observed_n_voluntary": obs_vol,
            "observed_n_involuntary": obs_inv,
            "train_rows": len(train_merged),
            "train_positives": int(y_train.sum()),
            "train_auc": train_metrics["roc_auc"],
            "scored_customers": len(risk_score_df),
            "band_counts": band_counts,
            "rule_fail_counts": rule_fail_counts,
            "eligible_customers": len(final_cc),
            "planned_offer_counts": planned_offer_counts,
            "stratum_arm_counts": stratum_arm_counts,
            "delivery_failed_count": sim_res.metrics["delivery_failed_count"],
            "sent_count": sim_res.metrics["sent_count"],
            "withheld_count": sim_res.metrics["withheld_count"],
            "responded_count": sim_res.metrics["responded_count"],
            "redeemed_count": sim_res.metrics["redeemed_count"],
            "saveable_count": sim_res.metrics["saveable_count"],
            "saved_count": sim_res.metrics["saved_count"],
            "saved_customer_ids": sim_res.metrics["saved_customer_ids"],
            "retention_90d_treatment": sim_res.metrics["retention_90d_treatment"],
            "retention_90d_control": sim_res.metrics["retention_90d_control"],
            "smd_by_covariate": smd_by_cov,
            "max_smd": max_smd,
            "non_treatment_2026_auc": non_treat_2026_metrics["roc_auc"],
            "non_treatment_2026_rows": len(non_treat_eval),
            "non_treatment_2026_positives": int(non_treat_eval["churned"].astype(int).sum()),
        }
    )

    return World(
        tables=final_tables,
        latent=sim_res.latent,
        summary=pipeline_summary,
    )

