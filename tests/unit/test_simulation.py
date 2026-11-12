from __future__ import annotations

import pandas as pd

from churnexp.config import load_config
from churnexp.eligibility.catalog import build_catalog
from churnexp.eligibility.engine import evaluate_eligibility, get_all_eligible_customer_offers
from churnexp.experiment.assign import assign_campaign
from churnexp.experiment.pipeline import run_pipeline
from churnexp.experiment.simulate import simulate_outcomes
from churnexp.features.builder import build_features
from churnexp.generation.world import generate_world
from churnexp.modeling.score import score as score_customers
from churnexp.modeling.train import train_model
from churnexp.rng import RngFactory
from churnexp.validation.checks import validate_tables


def test_simulation_saves_and_invariants():
    cfg = load_config("starter")
    base_world = generate_world(cfg)
    final_world = run_pipeline(cfg)
    base_tables = base_world.tables
    final_tables = final_world.tables
    latent = final_world.latent.set_index("customer_id")

    saved_cids = set(final_world.summary["saved_customer_ids"])
    assert len(saved_cids) >= 1

    cc_w01 = (
        final_tables["campaign_contact"][
            final_tables["campaign_contact"]["contact_id"].astype(str).str.endswith("-W01")
        ]
        .set_index("customer_id")
    )
    cc_by_contact = final_tables["campaign_contact"].set_index("contact_id")

    # Map customer -> base last subscription (end_date, end_reason)
    base_last_sub = (
        base_tables["subscription"]
        .sort_values(["customer_id", "sequence_no"], kind="mergesort")
        .groupby("customer_id", as_index=True)
        .last()
    )

    # 1. Only TREATMENT + SENT + PERSUADABLE + VOLUNTARY customers are saved
    for cid in saved_cids:
        lat_row = latent.loc[cid]
        assert lat_row["hidden_segment"] == "PERSUADABLE"
        assert lat_row["untreated_churn_date"] is not None
        assert lat_row["treated_churn_date"] is None
        assert int(lat_row["true_effect_flag"]) == 1
        cc = cc_w01.loc[cid]
        assert cc["experiment_group"] == "TREATMENT"
        assert cc["contact_status"] == "SENT"
        assert int(cc["responded"]) == 1
        assert int(cc["redeemed"]) == 1
        assert base_last_sub.loc[cid, "end_reason"] == "VOLUNTARY_CANCEL"

    # 2. Involuntary churners are never saved
    involuntary_cids = set(
        base_last_sub[base_last_sub["end_reason"] == "INVOLUNTARY_CANCEL"].index
    )
    assert len(involuntary_cids) > 0
    assert saved_cids.isdisjoint(involuntary_cids)

    # 3. Control customers and ineligible customers have identical subscription, usage, billing, support rows
    untouched_cids = set(final_tables["customer"]["customer_id"]) - saved_cids
    untouched_sids = set(
        base_tables["subscription"].loc[
            base_tables["subscription"]["customer_id"].isin(untouched_cids), "subscription_id"
        ]
    )
    for tbl_name, key_col, key_set in [
        ("subscription", "customer_id", untouched_cids),
        ("usage_snapshot", "subscription_id", untouched_sids),
        ("billing_event", "subscription_id", untouched_sids),
        ("support_case", "customer_id", untouched_cids),
    ]:
        b_df = base_tables[tbl_name]
        f_df = final_tables[tbl_name]
        b_sub = b_df[b_df[key_col].isin(key_set)].reset_index(drop=True)
        f_sub = f_df[f_df[key_col].isin(key_set)].reset_index(drop=True)
        pd.testing.assert_frame_equal(
            b_sub, f_sub, check_dtype=False, obj=f"Untouched customer rows in {tbl_name}"
        )

    # 4. Saved customers have no churn in 2026 and have rows after original_churn_date
    final_co_2026 = final_tables["churn_outcome"][
        final_tables["churn_outcome"]["cycle_year"].astype(int) == 2026
    ].set_index("customer_id")
    for cid in saved_cids:
        orig_churn = str(latent.loc[cid, "untreated_churn_date"])
        co_row = final_co_2026.loc[cid]
        assert int(co_row["churned"]) == 0
        assert pd.isna(co_row["churn_date"])
        assert pd.isna(co_row["churn_type"])

        cust_subs = final_tables["subscription"][final_tables["subscription"]["customer_id"] == cid]
        cust_sids = set(cust_subs["subscription_id"])
        last_sub = cust_subs.sort_values("sequence_no").iloc[-1]
        assert pd.isna(last_sub["end_date"])
        assert pd.isna(last_sub["end_reason"])

        cust_usage = final_tables["usage_snapshot"][
            final_tables["usage_snapshot"]["subscription_id"].isin(cust_sids)
        ]
        cust_bill = final_tables["billing_event"][
            final_tables["billing_event"]["subscription_id"].isin(cust_sids)
        ]
        has_post_usage = (cust_usage["period_end"] > orig_churn).any()
        has_post_bill = (cust_bill["event_date"] > orig_churn).any()
        assert has_post_usage and has_post_bill

    # 5. retention_outcome windows and attributed_offer_id rule
    ro = final_tables["retention_outcome"]
    assert len(ro) == len(final_tables["campaign_contact"])
    assert (ro["window_start"] == "2026-01-05").all()
    assert (ro["window_end"] == "2026-04-05").all()

    for _, ro_row in ro.iterrows():
        cnt_id = ro_row["contact_id"]
        cc_row = cc_by_contact.loc[cnt_id]
        expected_attr = (
            cc_row["offer_id"]
            if (
                cc_row["experiment_group"] == "TREATMENT"
                and cc_row["contact_status"] == "SENT"
                and int(cc_row["redeemed"]) == 1
                and int(ro_row["retained"]) == 1
            )
            else None
        )
        if expected_attr is None:
            assert pd.isna(ro_row["attributed_offer_id"])
        else:
            assert ro_row["attributed_offer_id"] == expected_attr

    # 6. Final tables pass validate_tables with zero findings
    report = validate_tables(final_tables)
    assert len(report.findings) == 0


def test_simulation_multiple_saves_forced_persuadable():
    """Verify simulation saves and generates post-churn usage & billing when multiple churners are saved."""
    cfg = load_config("starter")
    rng_factory = RngFactory(cfg.seed)
    world = generate_world(cfg)
    base_tables = world.tables
    latent = world.latent.copy()

    # Force all untreated churners to be PERSUADABLE so multiple 2026 churners are saved across Jan-Jun
    latent.loc[latent["untreated_churn_date"].notna(), "hidden_segment"] = "PERSUADABLE"

    lookback = int(cfg.timeline.feature_lookback_months)
    feat_P0 = build_features(base_tables, cfg.timeline.train_as_of, lookback_months=lookback)
    co_2025 = base_tables["churn_outcome"]
    model = train_model(feat_P0, co_2025)
    feat_P = build_features(base_tables, cfg.timeline.score_as_of, lookback_months=lookback)
    rs = score_customers(
        model,
        feat_P,
        cfg.campaign.risk_bands.high_share,
        cfg.campaign.risk_bands.medium_share,
    )
    offers_df, rules_df, _ = build_catalog(cfg)
    rule_eval_df = evaluate_eligibility(
        tables=base_tables,
        risk_scores=rs,
        offers=offers_df,
        rules=rules_df,
        as_of=cfg.campaign.assignment_date,
    )
    all_elig = get_all_eligible_customer_offers(rule_eval_df)
    cc_df = assign_campaign(all_elig, rs, cfg, rng_factory)

    sim_res = simulate_outcomes(
        base_tables=base_tables,
        base_latent=latent,
        campaign_contacts=cc_df,
        risk_scores=rs,
        cfg=cfg,
        rng_factory=rng_factory,
    )
    assert sim_res.metrics["saved_count"] >= 2
    assert len(sim_res.tables["usage_snapshot"]) > len(base_tables["usage_snapshot"])
    assert len(sim_res.tables["billing_event"]) > len(base_tables["billing_event"])
