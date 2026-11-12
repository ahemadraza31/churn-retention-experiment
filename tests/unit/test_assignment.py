"""Unit tests for campaign offer planning and stratified randomized assignment (Step 7 item 5)."""

import pandas as pd
import pytest

from churnexp.config import load_config
from churnexp.eligibility.catalog import build_catalog
from churnexp.eligibility.engine import (
    evaluate_eligibility,
    get_all_eligible_customer_offers,
)
from churnexp.experiment.assign import assign_campaign
from churnexp.features.builder import build_features
from churnexp.generation.world import generate_world
from churnexp.modeling.score import score
from churnexp.modeling.train import train_model
from churnexp.rng import RngFactory


@pytest.fixture(scope="module")
def starter_cfg():
    return load_config("starter")


@pytest.fixture(scope="module")
def assignment_setup(starter_cfg):
    world = generate_world(starter_cfg)
    feats_p0 = build_features(world.tables, as_of=starter_cfg.timeline.train_as_of)
    feats_p = build_features(world.tables, as_of=starter_cfg.timeline.score_as_of)
    model = train_model(feats_p0, world.tables["churn_outcome"])
    rs = score(
        model,
        feats_p,
        high_share=starter_cfg.campaign.risk_bands.high_share,
        medium_share=starter_cfg.campaign.risk_bands.medium_share,
    )
    offers, rules, _ = build_catalog(starter_cfg)
    re_df = evaluate_eligibility(
        world.tables, rs, offers, rules, as_of=starter_cfg.campaign.assignment_date
    )
    elig_map = get_all_eligible_customer_offers(re_df)
    return starter_cfg, world, rs, re_df, elig_map


def test_assignment_invariants_stratification_and_determinism(assignment_setup):
    """1 contact per eligible, 0 for ineligible, |T - C| <= 1 per stratum, valid offer, deterministic, control WITHHELD."""
    cfg, world, rs, re_df, elig_map = assignment_setup
    assert len(elig_map) > 0

    cc1 = assign_campaign(elig_map, rs, cfg, RngFactory(cfg.seed))
    cc2 = assign_campaign(elig_map, rs, cfg, RngFactory(cfg.seed))
    pd.testing.assert_frame_equal(cc1, cc2, check_exact=True)

    # 1. Exactly one contact per eligible customer, none for ineligible
    all_cids = set(world.tables["customer"]["customer_id"].astype(str))
    elig_cids = set(elig_map.keys())
    inelig_cids = all_cids - elig_cids

    assert len(cc1) == len(elig_cids)
    assert set(cc1["customer_id"].astype(str)) == elig_cids
    assert cc1["customer_id"].is_unique
    assert not (set(cc1["customer_id"].astype(str)) & inelig_cids)

    # 2. |T - C| <= 1 per stratum
    for stratum, grp in cc1.groupby("stratum"):
        assert stratum in ("HIGH", "MEDIUM")
        n_t = int((grp["experiment_group"] == "TREATMENT").sum())
        n_c = int((grp["experiment_group"] == "CONTROL").sum())
        assert abs(n_t - n_c) <= 1, f"Stratum {stratum} imbalance: T={n_t}, C={n_c}"

    # 3. Planned offer always passes ER-007 for that customer
    for row in cc1.itertuples(index=False):
        cid = str(row.customer_id)
        oid = str(row.offer_id)
        assert oid in elig_map[cid]

    # 4. Control keeps its offer_id with WITHHELD and sent_at NULL; TREATMENT has SENT or DELIVERY_FAILED and sent_at set
    ctrl_rows = cc1[cc1["experiment_group"] == "CONTROL"]
    assert not ctrl_rows.empty
    assert (ctrl_rows["contact_status"] == "WITHHELD").all()
    assert ctrl_rows["sent_at"].isna().all()
    assert ctrl_rows["offer_id"].notna().all()

    treat_rows = cc1[cc1["experiment_group"] == "TREATMENT"]
    assert not treat_rows.empty
    assert set(treat_rows["contact_status"]).issubset({"SENT", "DELIVERY_FAILED"})
    assert (treat_rows["sent_at"] == "2026-01-05T10:00:00").all()
    assert (cc1["assigned_at"] == "2026-01-05T08:00:00").all()
    assert (cc1["responded"] == 0).all()
    assert (cc1["redeemed"] == 0).all()

