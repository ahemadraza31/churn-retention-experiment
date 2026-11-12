"""Potential outcomes and observed outcome simulation for the retention experiment (ADR-005, ADR-007).

This is the ONLY module in `churnexp.experiment` allowed to read the latent ground-truth DataFrame.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Mapping
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.generation.billing import BillingEventRecord, billing_to_dataframe
from churnexp.generation.customers import CustomerRecord
from churnexp.generation.events import rebuild_state_events_from_tables
from churnexp.generation.subscriptions import TIER_RANK, SubscriptionRecord
from churnexp.generation.support import SupportCaseRecord, support_to_dataframe
from churnexp.generation.usage import UsageSnapshotRecord, usage_to_dataframe
from churnexp.generation.world import generate_customer_months
from churnexp.rng import RngFactory

RETENTION_OUTCOME_COLUMNS: list[str] = [
    "retention_id",
    "contact_id",
    "customer_id",
    "attributed_offer_id",
    "window_start",
    "window_end",
    "retained",
    "churned_at",
]

CHURN_OUTCOME_COLUMNS: list[str] = [
    "churn_id",
    "customer_id",
    "cycle_year",
    "prediction_date",
    "horizon_end",
    "churned",
    "churn_date",
    "churn_type",
]


@dataclass(frozen=True)
class SimulationResult:
    tables: dict[str, pd.DataFrame]
    latent: pd.DataFrame
    metrics: dict[str, Any]


def _offer_number_from_id(offer_id: str) -> int:
    # OFF-2026-000001 -> 1
    parts = str(offer_id).split("-")
    return int(parts[-1])


def _reconstruct_customer_record(
    row: Any,
    hidden_segment: str,
    max_billing_day: int = 28,
) -> CustomerRecord:
    cid = str(row.customer_id)
    signup_dt = date.fromisoformat(str(row.signup_date))
    b_day = (
        int(row.billing_day)
        if hasattr(row, "billing_day")
        else min(signup_dt.day, int(max_billing_day))
    )
    return CustomerRecord(
        index=ids.parse_customer_id(cid),
        customer_id=cid,
        signup_date=signup_dt,
        segment=str(row.segment),
        channel=str(row.channel),
        region=str(row.region),
        usage_pattern=str(row.usage_pattern),
        marketing_opt_in=int(row.marketing_opt_in),
        billing_day=b_day,
        hidden_segment=hidden_segment,
    )


def _reconstruct_saved_subscriptions(
    sub_rows: pd.DataFrame,
) -> list[SubscriptionRecord]:
    """Reconstruct SubscriptionRecord chain for a saved customer (final end_date and end_reason = None)."""
    sorted_rows = sub_rows.sort_values("sequence_no", kind="mergesort")
    n_subs = len(sorted_rows)
    subs: list[SubscriptionRecord] = []
    upgrades = 0
    downgrades = 0
    prev_tier: str | None = None

    for idx, row in enumerate(sorted_rows.itertuples(index=False)):
        tier = str(row.plan_tier)
        if prev_tier is not None:
            if TIER_RANK[tier] > TIER_RANK[prev_tier]:
                upgrades += 1
            elif TIER_RANK[tier] < TIER_RANK[prev_tier]:
                downgrades += 1
        prev_tier = tier

        prev_val = getattr(row, "previous_subscription_id", None)
        prev_sid = (
            None
            if prev_val is None or pd.isna(prev_val) or str(prev_val) == ""
            else str(prev_val)
        )
        is_last = idx == (n_subs - 1)
        if is_last:
            end_dt = None
            end_reason = None
        else:
            e_val = getattr(row, "end_date", None)
            end_dt = (
                None
                if e_val is None or pd.isna(e_val) or str(e_val) == ""
                else date.fromisoformat(str(e_val))
            )
            r_val = getattr(row, "end_reason", None)
            end_reason = (
                None
                if r_val is None or pd.isna(r_val) or str(r_val) == ""
                else str(r_val)
            )

        subs.append(
            SubscriptionRecord(
                subscription_id=str(row.subscription_id),
                customer_id=str(row.customer_id),
                previous_subscription_id=prev_sid,
                sequence_no=int(row.sequence_no),
                plan_tier=tier,
                monthly_price_cents=int(row.monthly_price_cents),
                gross_margin_pct=float(row.gross_margin_pct),
                start_date=date.fromisoformat(str(row.start_date)),
                end_date=end_dt,
                end_reason=end_reason,
                upgrades_count=upgrades,
                downgrades_count=downgrades,
            )
        )
    return subs


def _months_from(start_ym: tuple[int, int], end_ym: tuple[int, int]) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    y, m = start_ym
    while (y, m) <= end_ym:
        months.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return months


def simulate_outcomes(
    base_tables: Mapping[str, pd.DataFrame],
    base_latent: pd.DataFrame,
    campaign_contacts: pd.DataFrame,
    risk_scores: pd.DataFrame,
    cfg: Config,
    rng_factory: RngFactory | None = None,
) -> SimulationResult:
    """Simulate counterfactual potential outcomes, observed saved customer histories, and 2026 outcomes.

    Note on SLEEPING_DOG: per ADR-005 and the Run 2A prototype design, SLEEPING_DOG customers
    have no adverse or saving treatment effect in this prototype (never saved, untreated churn unchanged).
    """
    if rng_factory is None:
        rng_factory = RngFactory(cfg.seed)

    eff_cfg = cfg.experiment.effects
    respond_prob_map = {str(k): float(v) for k, v in eff_cfg.respond_prob.items()}
    redeem_prob = float(eff_cfg.redeem_given_respond)
    save_prob_map = {int(k): float(v) for k, v in eff_cfg.save_prob_given_redeem.items()}

    assign_dt = cfg.campaign.assignment_date
    assign_str = assign_dt.isoformat()
    score_as_of = cfg.timeline.score_as_of
    score_str = score_as_of.isoformat()
    horizon_end = score_as_of + timedelta(days=int(cfg.timeline.label_horizon_days))
    horizon_end_str = horizon_end.isoformat()
    outcome_window_end = assign_dt + timedelta(days=int(cfg.timeline.outcome_window_days))
    outcome_window_end_str = outcome_window_end.isoformat()
    data_end_ym = (cfg.timeline.data_end.year, cfg.timeline.data_end.month)

    cust_df = base_tables["customer"].copy()
    sub_df = base_tables["subscription"].copy()
    usage_df = base_tables["usage_snapshot"].copy()
    bill_df = base_tables["billing_event"].copy()
    sup_df = base_tables["support_case"].copy()
    churn_2025_df = base_tables["churn_outcome"].copy()
    latent_df = base_latent.copy()
    cc_df = campaign_contacts.copy()

    # Map customer -> hidden_segment and untreated_churn_date from latent
    hidden_seg_by_cid: dict[str, str] = {}
    untreated_churn_by_cid: dict[str, str | None] = {}
    for row in latent_df.itertuples(index=False):
        cid = str(row.customer_id)
        hidden_seg_by_cid[cid] = str(row.hidden_segment)
        u_val = getattr(row, "untreated_churn_date", None)
        untreated_churn_by_cid[cid] = (
            None
            if u_val is None or pd.isna(u_val) or str(u_val) == ""
            else str(u_val)
        )

    # Map customer -> untreated churn type ("VOLUNTARY" | "INVOLUNTARY" | None) from base subscription
    untreated_type_by_cid: dict[str, str | None] = {}
    sub_sorted_base = sub_df.sort_values(["customer_id", "sequence_no"], kind="mergesort")
    for row in sub_sorted_base.itertuples(index=False):
        cid = str(row.customer_id)
        r_val = getattr(row, "end_reason", None)
        r_str = None if r_val is None or pd.isna(r_val) or str(r_val) == "" else str(r_val)
        if r_str == "VOLUNTARY_CANCEL":
            untreated_type_by_cid[cid] = "VOLUNTARY"
        elif r_str == "INVOLUNTARY_CANCEL":
            untreated_type_by_cid[cid] = "INVOLUNTARY"
        else:
            untreated_type_by_cid.setdefault(cid, None)

    # Potential outcomes for EVERY eligible customer (either arm)
    cc_sorted = cc_df.sort_values("customer_id", kind="mergesort").reset_index(drop=True)
    saveable_by_cid: dict[str, bool] = {}
    responds_by_cid: dict[str, bool] = {}
    redeems_by_cid: dict[str, bool] = {}
    saved_cids: set[str] = set()

    for row in cc_sorted.itertuples(index=False):
        cid = str(row.customer_id)
        c_idx = ids.parse_customer_id(cid)
        rng_eff = rng_factory.entity_stream("effect", c_idx)
        u_respond = float(rng_eff.random())
        u_redeem = float(rng_eff.random())
        u_save = float(rng_eff.random())

        h_seg = hidden_seg_by_cid[cid]
        u_churn_str = untreated_churn_by_cid[cid]
        u_churn_type = untreated_type_by_cid.get(cid)
        offer_num = _offer_number_from_id(str(row.offer_id))

        responds = u_respond < respond_prob_map[h_seg]
        redeems = responds and (u_redeem < redeem_prob)
        is_saveable = (
            redeems
            and (u_save < save_prob_map[offer_num])
            and (h_seg == "PERSUADABLE")
            and (u_churn_type == "VOLUNTARY")
            and (u_churn_str is not None)
            and (assign_str <= u_churn_str < horizon_end_str)
        )

        responds_by_cid[cid] = responds
        redeems_by_cid[cid] = redeems
        saveable_by_cid[cid] = is_saveable

        if (
            is_saveable
            and str(row.experiment_group) == "TREATMENT"
            and str(row.contact_status) == "SENT"
        ):
            saved_cids.add(cid)

    # Update campaign_contact responded and redeemed for SENT treatment contacts
    responded_col: list[int] = []
    redeemed_col: list[int] = []
    for row in cc_df.itertuples(index=False):
        cid = str(row.customer_id)
        if str(row.experiment_group) == "TREATMENT" and str(row.contact_status) == "SENT":
            responded_col.append(1 if responds_by_cid.get(cid, False) else 0)
            redeemed_col.append(1 if redeems_by_cid.get(cid, False) else 0)
        else:
            responded_col.append(0)
            redeemed_col.append(0)
    cc_df["responded"] = responded_col
    cc_df["redeemed"] = redeemed_col
    cc_df = cc_df.sort_values("contact_id", kind="mergesort").reset_index(drop=True)

    # Update latent DataFrame: treated_churn_date and true_effect_flag for eligible customers
    treated_dates: list[str | None] = []
    effect_flags: list[int | None] = []
    for row in latent_df.itertuples(index=False):
        cid = str(row.customer_id)
        u_churn_str = untreated_churn_by_cid[cid]
        if cid in saveable_by_cid:
            if saveable_by_cid[cid]:
                treated_dates.append(None)
                effect_flags.append(1)
            else:
                treated_dates.append(u_churn_str)
                effect_flags.append(0)
        else:
            treated_dates.append(None)
            effect_flags.append(None)

    latent_df["treated_churn_date"] = pd.Series(treated_dates, dtype="object")
    latent_df["true_effect_flag"] = pd.Series(effect_flags, dtype="object")

    # Apply observed savings: update final subscription end_date/end_reason and resume post-churn events
    if saved_cids:
        cust_row_by_cid = {
            str(r.customer_id): r for r in cust_df.itertuples(index=False)
        }
        new_usage_records: list[UsageSnapshotRecord] = []
        new_billing_records: list[BillingEventRecord] = []
        new_support_records: list[SupportCaseRecord] = []

        # Count existing support cases per saved customer and track existing billing event IDs
        existing_sup_counts: dict[str, int] = {cid: 0 for cid in saved_cids}
        if not sup_df.empty:
            for cid_val in sup_df["customer_id"].astype(str):
                if cid_val in existing_sup_counts:
                    existing_sup_counts[cid_val] += 1
        existing_billing_ids: set[str] = (
            set(bill_df["billing_event_id"].astype(str)) if not bill_df.empty else set()
        )

        for cid in sorted(saved_cids):
            orig_churn_str = untreated_churn_by_cid[cid]
            assert orig_churn_str is not None
            orig_churn_dt = date.fromisoformat(orig_churn_str)
            orig_ym = (orig_churn_dt.year, orig_churn_dt.month)

            # Clear end_date and end_reason on customer's final subscription in sub_df
            c_sub_mask = sub_df["customer_id"] == cid
            max_seq = int(sub_df.loc[c_sub_mask, "sequence_no"].max())
            final_mask = c_sub_mask & (sub_df["sequence_no"] == max_seq)
            sub_df.loc[final_mask, "end_date"] = None
            sub_df.loc[final_mask, "end_reason"] = None

            # Reconstruct CustomerRecord and SubscriptionRecord list for reusable generator
            c_rec = _reconstruct_customer_record(
                cust_row_by_cid[cid],
                hidden_seg_by_cid[cid],
                max_billing_day=cfg.generator.customers.max_billing_day,
            )
            c_subs = _reconstruct_saved_subscriptions(sub_df[c_sub_mask])
            months_to_run = _months_from(orig_ym, data_end_ym)

            u_gen, b_gen, s_gen = generate_customer_months(
                customer=c_rec,
                subs=c_subs,
                months=months_to_run,
                churn_date_or_None=None,
                churn_type=None,
                is_loud=False,
                cfg=cfg,
                rng_factory=rng_factory,
                starting_case_seq=1,
            )

            # Keep usage snapshots for months strictly after original churn month
            for u_rec in u_gen:
                if u_rec.snapshot_month > orig_churn_str[:7]:
                    new_usage_records.append(u_rec)

            # Keep billing events for monthly billing cycles after original churn date
            for b_rec in b_gen:
                inv_id_for_cycle = b_rec.billing_event_id[:-2] + "01"
                if (
                    inv_id_for_cycle not in existing_billing_ids
                    and b_rec.event_date > orig_churn_str
                ):
                    new_billing_records.append(b_rec)

            # Keep support cases opened strictly after original churn date, re-sequenced after existing
            next_seq = existing_sup_counts[cid] + 1
            for s_rec in s_gen:
                if s_rec.opened_at[:10] > orig_churn_str:
                    new_support_records.append(
                        SupportCaseRecord(
                            case_id=ids.support_case_id(cid, next_seq),
                            customer_id=cid,
                            subscription_id=s_rec.subscription_id,
                            opened_at=s_rec.opened_at,
                            resolved_at=s_rec.resolved_at,
                            category=s_rec.category,
                            severity=s_rec.severity,
                            escalated=s_rec.escalated,
                        )
                    )
                    next_seq += 1

        if new_usage_records:
            usage_df = (
                pd.concat([usage_df, usage_to_dataframe(new_usage_records)], ignore_index=True)
                .sort_values("snapshot_id", kind="mergesort")
                .reset_index(drop=True)
            )
        if new_billing_records:
            bill_df = (
                pd.concat([bill_df, billing_to_dataframe(new_billing_records)], ignore_index=True)
                .sort_values("billing_event_id", kind="mergesort")
                .reset_index(drop=True)
            )
        if new_support_records:
            sup_df = (
                pd.concat([sup_df, support_to_dataframe(new_support_records)], ignore_index=True)
                .sort_values("case_id", kind="mergesort")
                .reset_index(drop=True)
            )

    sub_df = sub_df.sort_values("subscription_id", kind="mergesort").reset_index(drop=True)

    # Determine observed churn date and type per customer from final subscription
    obs_churn_by_cid: dict[str, tuple[str | None, str | None]] = {}
    for row in sub_df.sort_values(["customer_id", "sequence_no"], kind="mergesort").itertuples(
        index=False
    ):
        cid = str(row.customer_id)
        e_val = getattr(row, "end_date", None)
        e_str = None if e_val is None or pd.isna(e_val) or str(e_val) == "" else str(e_val)
        r_val = getattr(row, "end_reason", None)
        r_str = None if r_val is None or pd.isna(r_val) or str(r_val) == "" else str(r_val)
        if r_str == "VOLUNTARY_CANCEL":
            obs_churn_by_cid[cid] = (e_str, "VOLUNTARY")
        elif r_str == "INVOLUNTARY_CANCEL":
            obs_churn_by_cid[cid] = (e_str, "INVOLUNTARY")
        else:
            obs_churn_by_cid[cid] = (None, None)

    # Build 2026 churn_outcome rows for all customers active at score_as_of
    scored_cids = sorted(str(c) for c in risk_scores["customer_id"].tolist())
    churn_2026_rows = []
    for cid in scored_cids:
        obs_dt, obs_type = obs_churn_by_cid.get(cid, (None, None))
        in_horizon = obs_dt is not None and (score_str <= obs_dt < horizon_end_str)
        churn_2026_rows.append(
            {
                "churn_id": ids.churn_outcome_id(cid, 2026),
                "customer_id": cid,
                "cycle_year": 2026,
                "prediction_date": score_str,
                "horizon_end": horizon_end_str,
                "churned": 1 if in_horizon else 0,
                "churn_date": obs_dt if in_horizon else None,
                "churn_type": obs_type if in_horizon else None,
            }
        )
    churn_2026_df = pd.DataFrame(churn_2026_rows, columns=CHURN_OUTCOME_COLUMNS)
    churn_all_df = (
        pd.concat([churn_2025_df, churn_2026_df], ignore_index=True)
        .sort_values("churn_id", kind="mergesort")
        .reset_index(drop=True)
    )

    # Build retention_outcome rows for every campaign_contact
    ret_rows = []
    for row in cc_df.itertuples(index=False):
        contact_id = str(row.contact_id)
        cid = str(row.customer_id)
        oid = str(row.offer_id)
        exp_group = str(row.experiment_group)
        status = str(row.contact_status)
        redeemed = int(row.redeemed)

        obs_dt, _ = obs_churn_by_cid.get(cid, (None, None))
        churned_in_window = (
            obs_dt is not None and (assign_str <= obs_dt < outcome_window_end_str)
        )
        retained = 0 if churned_in_window else 1
        churned_at = obs_dt if churned_in_window else None

        if (
            exp_group == "TREATMENT"
            and status == "SENT"
            and redeemed == 1
            and retained == 1
        ):
            attributed_oid: str | None = oid
        else:
            attributed_oid = None

        ret_rows.append(
            {
                "retention_id": ids.retention_outcome_id(contact_id),
                "contact_id": contact_id,
                "customer_id": cid,
                "attributed_offer_id": attributed_oid,
                "window_start": assign_str,
                "window_end": outcome_window_end_str,
                "retained": retained,
                "churned_at": churned_at,
            }
        )
    retention_df = (
        pd.DataFrame(ret_rows, columns=RETENTION_OUTCOME_COLUMNS)
        .sort_values("retention_id", kind="mergesort")
        .reset_index(drop=True)
    )

    updated_tables = dict(base_tables)
    updated_tables["customer"] = cust_df
    updated_tables["subscription"] = sub_df
    updated_tables["usage_snapshot"] = usage_df
    updated_tables["billing_event"] = bill_df
    updated_tables["support_case"] = sup_df
    updated_tables["campaign_contact"] = cc_df
    updated_tables["churn_outcome"] = churn_all_df
    updated_tables["retention_outcome"] = retention_df
    updated_tables["state_event"] = rebuild_state_events_from_tables(updated_tables)

    # Compute simulation summary metrics
    treat_mask = cc_df["experiment_group"] == "TREATMENT"
    ctrl_mask = cc_df["experiment_group"] == "CONTROL"
    treat_cids = set(cc_df.loc[treat_mask, "customer_id"].astype(str))
    ctrl_cids = set(cc_df.loc[ctrl_mask, "customer_id"].astype(str))

    ret_treat = retention_df[retention_df["customer_id"].isin(treat_cids)]
    ret_ctrl = retention_df[retention_df["customer_id"].isin(ctrl_cids)]
    ret_rate_treat = (
        float(ret_treat["retained"].astype(int).mean()) if not ret_treat.empty else 0.0
    )
    ret_rate_ctrl = (
        float(ret_ctrl["retained"].astype(int).mean()) if not ret_ctrl.empty else 0.0
    )

    sim_metrics = {
        "delivery_failed_count": int((cc_df["contact_status"] == "DELIVERY_FAILED").sum()),
        "sent_count": int((cc_df["contact_status"] == "SENT").sum()),
        "withheld_count": int((cc_df["contact_status"] == "WITHHELD").sum()),
        "responded_count": int(cc_df["responded"].astype(int).sum()),
        "redeemed_count": int(cc_df["redeemed"].astype(int).sum()),
        "saveable_count": int(sum(1 for v in saveable_by_cid.values() if v)),
        "saved_count": len(saved_cids),
        "saved_customer_ids": sorted(saved_cids),
        "retention_90d_treatment": round(ret_rate_treat, 6),
        "retention_90d_control": round(ret_rate_ctrl, 6),
    }

    return SimulationResult(
        tables=updated_tables,
        latent=latent_df,
        metrics=sim_metrics,
    )
