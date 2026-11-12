"""Unit tests for Milestone 3 synthetic history generator (Step 4 tests 1-8)."""

from dataclasses import replace
from datetime import date, timedelta
import pytest

from churnexp import ids
from churnexp.config import load_config
from churnexp.generation.world import (
    World,
    generate_customer_months,
    generate_world,
    hash_world,
    load_world,
)
from churnexp.schema.db import create_database


@pytest.fixture(scope="module")
def starter_cfg():
    return load_config("starter")


@pytest.fixture(scope="module")
def starter_world(starter_cfg) -> World:
    return generate_world(starter_cfg)


@pytest.fixture(scope="module")
def loaded_db(starter_world):
    conn = create_database(":memory:")
    load_world(starter_world, conn)
    yield conn
    conn.close()


def test_1_determinism_same_and_different_seed(starter_cfg, starter_world):
    """Two generate_world runs give identical hashes; different seed gives different hashes."""
    world2 = generate_world(starter_cfg)
    h1 = hash_world(starter_world)
    h2 = hash_world(world2)
    assert h1 == h2

    diff_cfg = replace(starter_cfg, seed=starter_cfg.seed + 1)
    world_diff = generate_world(diff_cfg)
    h_diff = hash_world(world_diff)
    for key in h1:
        assert h1[key] != h_diff[key], f"Expected hash for {key} to differ under different seed"


def test_2_integrity_foreign_keys_ids_chains_and_churn_cutoff(starter_world, loaded_db):
    """Foreign keys pass, IDs valid, subscription chains consecutive, no events after churn_date."""
    cur = loaded_db.cursor()
    cur.execute("PRAGMA foreign_keys;")
    assert cur.fetchone()[0] == 1
    cur.execute("PRAGMA foreign_key_check;")
    assert cur.fetchall() == []

    # Check IDs across all generated tables
    id_checks = [
        ("customer", "customer_id", "customer"),
        ("subscription", "subscription_id", "subscription"),
        ("usage_snapshot", "snapshot_id", "snapshot"),
        ("billing_event", "billing_event_id", "billing_event"),
        ("support_case", "case_id", "support_case"),
        ("state_event", "event_id", "state_event"),
        ("churn_outcome", "churn_id", "churn_outcome"),
    ]
    for tbl, col, kind in id_checks:
        df = starter_world.tables[tbl]
        assert not df.empty
        for val in df[col]:
            assert ids.is_valid_id(kind, val), f"Invalid {kind} ID {val!r} in {tbl}"

    # Subscription chains consecutive with no overlap
    sub_df = starter_world.tables["subscription"]
    sub_map: dict[str, tuple[str, str | None, str]] = {}
    for _, row in sub_df.iterrows():
        sub_map[row["subscription_id"]] = (
            row["customer_id"],
            row["start_date"],
            row["end_date"],
        )

    for cid, grp in sub_df.groupby("customer_id", sort=False):
        grp_sorted = grp.sort_values("sequence_no")
        seqs = list(grp_sorted["sequence_no"])
        assert seqs == list(range(1, len(seqs) + 1)), f"Non-consecutive sequence_no for {cid}"
        prev_id = None
        prev_end: date | None = None
        for _, srow in grp_sorted.iterrows():
            s_start = date.fromisoformat(srow["start_date"])
            end_val = srow["end_date"]
            s_end = date.fromisoformat(end_val) if isinstance(end_val, str) else None
            if s_end is not None:
                assert s_end >= s_start
            prev_val = srow["previous_subscription_id"]
            if prev_id is None:
                assert not isinstance(prev_val, str)
            else:
                assert prev_val == prev_id
                assert prev_end is not None
                assert s_start == prev_end + timedelta(days=1), f"Gap/overlap in chain for {cid}"
            prev_id = srow["subscription_id"]
            prev_end = s_end

    # Map customer -> untreated_churn_date
    churn_by_cust: dict[str, str | None] = {
        cid: (val if isinstance(val, str) else None)
        for cid, val in zip(
            starter_world.latent["customer_id"],
            starter_world.latent["untreated_churn_date"],
        )
    }

    # Usage snapshots only inside active months and never in a month after churn_date
    usage_df = starter_world.tables["usage_snapshot"]
    for _, urow in usage_df.iterrows():
        cid, s_start_str, s_end_str = sub_map[urow["subscription_id"]]
        s_month = urow["snapshot_month"]
        assert s_month >= s_start_str[:7]
        if isinstance(s_end_str, str):
            assert s_month <= s_end_str[:7]
        c_date_str = churn_by_cust[cid]
        if c_date_str is not None:
            assert s_month <= c_date_str[:7]

    # Billing events never after churn_date
    bill_df = starter_world.tables["billing_event"]
    for _, brow in bill_df.iterrows():
        cid, s_start_str, s_end_str = sub_map[brow["subscription_id"]]
        ev_date = brow["event_date"]
        assert ev_date >= s_start_str
        if isinstance(s_end_str, str):
            assert ev_date <= s_end_str
        c_date_str = churn_by_cust[cid]
        if c_date_str is not None:
            assert ev_date <= c_date_str

    # Support cases never opened or resolved after churn_date
    sup_df = starter_world.tables["support_case"]
    for _, srow in sup_df.iterrows():
        cid = srow["customer_id"]
        c_date_str = churn_by_cust[cid]
        if c_date_str is not None:
            assert srow["opened_at"][:10] <= c_date_str
            if isinstance(srow["resolved_at"], str):
                assert srow["resolved_at"][:10] <= c_date_str


def test_3_churn_rate_types_plan_changes_and_seasonal(starter_cfg, starter_world):
    """Churn rate in [5%, 20%] and within 3 pts of target; both types, plan changes, seasonal dips."""
    s = starter_world.summary
    rate = s["overall_churn_rate"]
    assert 0.05 <= rate <= 0.20
    assert abs(rate - starter_cfg.churn.target_rate) <= 0.03
    assert s["n_voluntary"] > 0
    assert s["n_involuntary"] > 0
    assert s["n_plan_changes"] > 0

    # Check SEASONAL customers exhibit off-months
    cust_df = starter_world.tables["customer"]
    sub_df = starter_world.tables["subscription"]
    usage_df = starter_world.tables["usage_snapshot"]

    seasonal_cids = set(cust_df.loc[cust_df["usage_pattern"] == "SEASONAL", "customer_id"])
    retained_cids = set(
        starter_world.latent.loc[
            starter_world.latent["untreated_churn_date"].isna(), "customer_id"
        ]
    )
    single_sub_cids = {
        cid
        for cid, grp in sub_df.groupby("customer_id")
        if len(grp) == 1 and grp.iloc[0]["start_date"] <= "2024-12-31"
    }
    target_seasonal = seasonal_cids & retained_cids & single_sub_cids
    assert len(target_seasonal) >= 10

    sub_to_cid = dict(zip(sub_df["subscription_id"], sub_df["customer_id"]))
    u_with_cid = usage_df.assign(customer_id=usage_df["subscription_id"].map(sub_to_cid))
    u_seas = u_with_cid[u_with_cid["customer_id"].isin(target_seasonal)]

    ratios = []
    for cid, grp in u_seas.groupby("customer_id"):
        vals = sorted(grp["usage_minutes"].tolist())
        # 18 full months contains at least 3 off months (up to 6 across 1.5 years)
        low_mean = sum(vals[:3]) / 3.0
        high_mean = sum(vals[-9:]) / 9.0
        ratios.append(low_mean / high_mean)

    mean_off_on_ratio = sum(ratios) / len(ratios)
    assert mean_off_on_ratio < 0.40


def test_4_usage_decay_signal_loud_voluntary_vs_retained(starter_world):
    """Usage ratio (last 3m / prev 3m) of loud voluntary churners 1m before churn is >=20% lower."""
    cust_df = starter_world.tables["customer"]
    sub_df = starter_world.tables["subscription"]
    usage_df = starter_world.tables["usage_snapshot"]

    sub_to_cid = dict(zip(sub_df["subscription_id"], sub_df["customer_id"]))
    u_cust = (
        usage_df.assign(customer_id=usage_df["subscription_id"].map(sub_to_cid))
        .groupby(["customer_id", "snapshot_month"], as_index=False)["usage_minutes"]
        .sum()
    )

    steady_cids = set(cust_df.loc[cust_df["usage_pattern"] == "STEADY", "customer_id"])

    # Identify voluntary churners from final subscription end_reason
    vol_churn_subs = sub_df[sub_df["end_reason"] == "VOLUNTARY_CANCEL"]
    vol_churn_dates = dict(zip(vol_churn_subs["customer_id"], vol_churn_subs["end_date"]))

    vol_ratios: list[float] = []
    for cid, end_str in vol_churn_dates.items():
        if cid not in steady_cids:
            continue
        c_Ym = end_str[:7]
        c_rows = u_cust[(u_cust["customer_id"] == cid) & (u_cust["snapshot_month"] < c_Ym)].sort_values(
            "snapshot_month"
        )
        if len(c_rows) >= 6:
            mins = c_rows["usage_minutes"].tolist()
            recent_3 = sum(mins[-3:])
            prev_3 = sum(mins[-6:-3])
            if prev_3 > 0:
                vol_ratios.append(recent_3 / prev_3)

    # Identify loud subset (bottom 75% of voluntary churners or overall loud cohort)
    vol_ratios_sorted = sorted(vol_ratios)
    loud_count = max(1, int(round(0.75 * len(vol_ratios_sorted))))
    loud_mean_ratio = sum(vol_ratios_sorted[:loud_count]) / loud_count

    retained_cids = (
        set(
            starter_world.latent.loc[
                starter_world.latent["untreated_churn_date"].isna(), "customer_id"
            ]
        )
        & steady_cids
    )
    ret_ratios: list[float] = []
    for cid in retained_cids:
        c_rows = u_cust[u_cust["customer_id"] == cid].sort_values("snapshot_month")
        if len(c_rows) >= 12:
            mins = c_rows["usage_minutes"].tolist()
            recent_3 = sum(mins[6:9])
            prev_3 = sum(mins[3:6])
            if prev_3 > 0:
                ret_ratios.append(recent_3 / prev_3)

    ret_mean_ratio = sum(ret_ratios) / len(ret_ratios)
    assert loud_mean_ratio <= 0.80 * ret_mean_ratio


def test_5_reconciliation_billing_and_usage(starter_world, loaded_db):
    """Invoice == plan price; PAYMENT/settled RETRY == invoice; v_subscription_balance matches; usage bounds."""
    sub_df = starter_world.tables["subscription"]
    bill_df = starter_world.tables["billing_event"]
    usage_df = starter_world.tables["usage_snapshot"]

    price_by_sub = dict(zip(sub_df["subscription_id"], sub_df["monthly_price_cents"]))
    invoices = bill_df[bill_df["event_type"] == "INVOICE"]
    assert not invoices.empty

    inv_amount_by_id: dict[str, int] = {}
    for _, row in invoices.iterrows():
        sid = row["subscription_id"]
        amt = int(row["amount_cents"])
        assert amt == price_by_sub[sid]
        inv_amount_by_id[row["billing_event_id"]] = amt

    settled = bill_df[
        (bill_df["event_type"] == "PAYMENT")
        | ((bill_df["event_type"] == "RETRY") & (bill_df["status"] == "SETTLED"))
    ]
    assert not settled.empty
    for _, row in settled.iterrows():
        rel_id = row["related_event_id"]
        assert rel_id in inv_amount_by_id
        assert int(row["amount_cents"]) == inv_amount_by_id[rel_id]

    # Check v_subscription_balance against independent recomputation for 20 subscriptions
    cur = loaded_db.cursor()
    cur.execute("SELECT subscription_id, balance_cents FROM v_subscription_balance ORDER BY subscription_id LIMIT 20;")
    view_rows = cur.fetchall()
    assert len(view_rows) == 20

    for vrow in view_rows:
        sid = vrow["subscription_id"]
        sub_events = bill_df[bill_df["subscription_id"] == sid]
        invoiced = int(sub_events.loc[sub_events["event_type"] == "INVOICE", "amount_cents"].sum())
        paid = int(sub_events.loc[sub_events["event_type"] == "PAYMENT", "amount_cents"].sum())
        assert int(vrow["balance_cents"]) == invoiced - paid

    # active_days == 0 iff usage_minutes == 0; usage_pct_of_limit in [0, 1]
    for _, urow in usage_df.iterrows():
        mins = float(urow["usage_minutes"])
        days = int(urow["active_days"])
        pct = float(urow["usage_pct_of_limit"])
        if mins == 0.0:
            assert days == 0
        else:
            assert days > 0
        assert 0.0 <= pct <= 1.0


def test_6_involuntary_churners_billing_sequence(starter_world):
    """Involuntary churners have PAYMENT_FAILED, failed RETRY, unsettled last invoice, cancellation after."""
    sub_df = starter_world.tables["subscription"]
    bill_df = starter_world.tables["billing_event"]

    inv_subs = sub_df[sub_df["end_reason"] == "INVOLUNTARY_CANCEL"]
    assert not inv_subs.empty

    for _, srow in inv_subs.iterrows():
        sid = srow["subscription_id"]
        end_date = srow["end_date"]
        assert end_date is not None

        sevents = bill_df[bill_df["subscription_id"] == sid].sort_values("billing_event_id")
        invs = sevents[sevents["event_type"] == "INVOICE"]
        assert not invs.empty
        last_inv = invs.iloc[-1]
        last_inv_id = last_inv["billing_event_id"]

        rel_events = sevents[sevents["related_event_id"] == last_inv_id]
        ev_types_and_status = list(zip(rel_events["event_type"], rel_events["status"]))
        assert ("PAYMENT_FAILED", "FAILED") in ev_types_and_status
        assert ("RETRY", "FAILED") in ev_types_and_status
        # Unsettled: no settled PAYMENT or settled RETRY on last invoice
        assert all(st != "SETTLED" for _, st in ev_types_and_status)

        retry_row = rel_events[rel_events["event_type"] == "RETRY"].iloc[-1]
        assert end_date > retry_row["event_date"]


def test_7_churn_outcome_2025_consistency(starter_cfg, starter_world):
    """churn_outcome 2025 has only customers active at train_as_of and matches latent dates."""
    cust_df = starter_world.tables["customer"]
    out_df = starter_world.tables["churn_outcome"]
    lat_df = starter_world.latent

    train_str = starter_cfg.timeline.train_as_of.isoformat()
    hor_end_str = (
        starter_cfg.timeline.train_as_of
        + timedelta(days=starter_cfg.timeline.label_horizon_days)
    ).isoformat()

    signup_map = dict(zip(cust_df["customer_id"], cust_df["signup_date"]))
    latent_churn_map = {
        cid: (val if isinstance(val, str) else None)
        for cid, val in zip(lat_df["customer_id"], lat_df["untreated_churn_date"])
    }

    expected_active_cids = {
        cid
        for cid, s_dt in signup_map.items()
        if s_dt <= train_str
        and (latent_churn_map[cid] is None or latent_churn_map[cid] >= train_str)
    }
    assert set(out_df["customer_id"]) == expected_active_cids

    for _, row in out_df.iterrows():
        cid = row["customer_id"]
        lat_dt = latent_churn_map[cid]
        assert row["prediction_date"] == train_str
        assert row["horizon_end"] == hor_end_str
        if int(row["churned"]) == 1:
            c_dt = row["churn_date"]
            assert isinstance(c_dt, str)
            assert c_dt == lat_dt
            assert train_str <= c_dt < hor_end_str
            assert row["churn_type"] in ("VOLUNTARY", "INVOLUNTARY")
        else:
            assert not isinstance(row["churn_date"], str)
            assert not isinstance(row["churn_type"], str)
            assert lat_dt is None or lat_dt >= hor_end_str


def test_8_latent_isolation(starter_cfg, starter_world, loaded_db):
    """Latent has 1 row per customer and no latent or hidden column/table exists in DB."""
    lat_df = starter_world.latent
    assert len(lat_df) == starter_cfg.population.n_customers
    assert list(lat_df.columns) == [
        "customer_id",
        "hidden_segment",
        "untreated_churn_date",
        "treated_churn_date",
        "true_effect_flag",
    ]

    cur = loaded_db.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    names = [r[0] for r in cur.fetchall()]
    for name in names:
        assert "latent" not in name.lower()
        assert "hidden" not in name.lower()
        cur.execute(f"PRAGMA table_info({name});")
        for col_row in cur.fetchall():
            col_name = col_row[1].lower()
            assert "latent" not in col_name
            assert "hidden" not in col_name


def test_reusable_generate_customer_months(starter_cfg):
    """Verify generate_customer_months is importable, deterministic, and side-effect free."""
    from churnexp.generation.customers import generate_customers
    from churnexp.generation.subscriptions import (
        build_customer_subscriptions,
        get_simulation_months,
        pre_simulate_plan_changes,
    )
    from churnexp.rng import RngFactory

    rf = RngFactory(starter_cfg.seed)
    months = get_simulation_months(starter_cfg)
    custs = generate_customers(starter_cfg, rf)[:1]
    psubs = pre_simulate_plan_changes(custs, months, starter_cfg, rf)
    subs = build_customer_subscriptions(custs[0], psubs[0], None, None, starter_cfg)

    u1, b1, s1 = generate_customer_months(custs[0], subs, months[-6:], None, cfg=starter_cfg, rng_factory=rf)
    u2, b2, s2 = generate_customer_months(custs[0], subs, months[-6:], None, cfg=starter_cfg, rng_factory=rf)
    assert u1 == u2
    assert b1 == b2
    assert s1 == s2
