"""Deterministic injection of labelled anomalies A, B, C, and D at the end of the pipeline.

Only ADDS rows to `churn_outcome`, `campaign_contact`, and `retention_outcome` (never edits or
deletes valid rows), preserving structural and temporal validity across all 18 data-quality rules.
Does not touch `state_event` for injected rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.eligibility.engine import _extract_rule_params
from churnexp.eligibility.rules import (
    eval_er001_active_subscription,
    eval_er002_min_tenure,
    eval_er003_marketing_opt_in,
    eval_er004_no_unsettled_invoice,
    eval_er005_no_open_escalated_case,
    eval_er007_offer_margin,
    extract_customer_rule_inputs,
)
from churnexp.rng import RngFactory

ANOMALIES_GT_COLUMNS: list[str] = [
    "anomaly_id",
    "anomaly_type",
    "detector_rule_id",
    "customer_id",
    "primary_key_table",
    "primary_key_value",
    "description",
]

EXPECTED_DECISIONS_GT_COLUMNS: list[str] = [
    "customer_id",
    "as_of_date",
    "rule_id",
    "offer_id",
    "passed",
]


@dataclass(frozen=True)
class AnomalyInjectionResult:
    tables: dict[str, pd.DataFrame]
    anomalies_gt: pd.DataFrame
    expected_decisions_gt: pd.DataFrame
    counts_by_type: dict[str, int]


def _pick_seeded_candidates(
    candidates: list[str],
    n_target: int,
    stream_name: str,
    rng_factory: RngFactory,
    anomaly_label: str,
) -> list[str]:
    sorted_cands = sorted(set(candidates))
    rng = rng_factory.stream(stream_name)
    if not sorted_cands:
        if n_target > 0:
            print(
                f"WARNING: Anomaly {anomaly_label} candidate pool has 0 < {n_target} candidates"
            )
        return []
    perm = rng.permutation(len(sorted_cands))
    shuffled = [sorted_cands[int(i)] for i in perm]
    if len(shuffled) < n_target:
        print(
            f"WARNING: Anomaly {anomaly_label} candidate pool has {len(shuffled)} < {n_target} candidates"
        )
        return shuffled
    return shuffled[:n_target]


def inject_anomalies(
    tables: Mapping[str, pd.DataFrame],
    cfg: Config,
    rng_factory: RngFactory | None = None,
) -> AnomalyInjectionResult:
    """Inject N records each of anomalies A, B, C, D into a copy of `tables`."""
    if rng_factory is None:
        rng_factory = RngFactory(cfg.seed)

    n_target = int(cfg.anomalies.records_per_type)
    score_as_of = cfg.timeline.score_as_of
    score_str = score_as_of.isoformat()
    horizon_end_str = (
        score_as_of + timedelta(days=int(cfg.timeline.label_horizon_days))
    ).isoformat()
    assign_dt = cfg.campaign.assignment_date
    assign_str = assign_dt.isoformat()
    outcome_window_end_str = (
        assign_dt + timedelta(days=int(cfg.timeline.outcome_window_days))
    ).isoformat()

    churn_df = tables["churn_outcome"].copy()
    cc_df = tables["campaign_contact"].copy()
    ret_df = tables["retention_outcome"].copy()
    sub_df = tables["subscription"]
    offers_df = tables["offer"].sort_values("offer_id", kind="mergesort")
    rules_df = tables["eligibility_rule"]
    rs_df = tables["risk_score"]

    # Map customer -> observed churn date from final subscription
    obs_churn_by_cid: dict[str, str | None] = {}
    for row in sub_df.sort_values(["customer_id", "sequence_no"], kind="mergesort").itertuples(
        index=False
    ):
        cid = str(row.customer_id)
        e_val = getattr(row, "end_date", None)
        e_str = None if e_val is None or pd.isna(e_val) or str(e_val) == "" else str(e_val)
        r_val = getattr(row, "end_reason", None)
        r_str = None if r_val is None or pd.isna(r_val) or str(r_val) == "" else str(r_val)
        if r_str in ("VOLUNTARY_CANCEL", "INVOLUNTARY_CANCEL"):
            obs_churn_by_cid[cid] = e_str
        else:
            obs_churn_by_cid[cid] = None

    used_cids: set[str] = set()
    gt_anom_rows: list[dict[str, Any]] = []
    counts_by_type: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}

    # =========================================================================
    # ANOMALY A: Temporal label leakage (2025 churner given a 2026 churn_outcome)
    # =========================================================================
    cids_2026 = set(
        churn_df.loc[churn_df["cycle_year"].astype(int) == 2026, "customer_id"].astype(str)
    )
    rows_2025_pos = churn_df[
        (churn_df["cycle_year"].astype(int) == 2025)
        & (churn_df["churned"].astype(int) == 1)
        & (~churn_df["customer_id"].astype(str).isin(cids_2026))
    ].sort_values("customer_id", kind="mergesort")
    info_2025_by_cid = {
        str(r.customer_id): (str(r.churn_date), str(r.churn_type))
        for r in rows_2025_pos.itertuples(index=False)
    }
    cands_a = [cid for cid in sorted(info_2025_by_cid.keys()) if cid not in used_cids]
    picked_a = _pick_seeded_candidates(
        cands_a, n_target, "anomaly_select:A", rng_factory, "A"
    )

    added_churn_rows: list[dict[str, Any]] = []
    for idx, cid in enumerate(picked_a, start=1):
        used_cids.add(cid)
        c_date, c_type = info_2025_by_cid[cid]
        ch_id = ids.churn_outcome_id(cid, 2026)
        added_churn_rows.append(
            {
                "churn_id": ch_id,
                "customer_id": cid,
                "cycle_year": 2026,
                "prediction_date": score_str,
                "horizon_end": horizon_end_str,
                "churned": 1,
                "churn_date": c_date,
                "churn_type": c_type,
            }
        )
        gt_anom_rows.append(
            {
                "anomaly_id": f"ANOM-A-{idx:03d}",
                "anomaly_type": "A",
                "detector_rule_id": "DET-A-LABEL-BEFORE-PREDICTION",
                "customer_id": cid,
                "primary_key_table": "churn_outcome",
                "primary_key_value": ch_id,
                "description": (
                    f"Temporal label leakage: 2026 churn_outcome {ch_id} has "
                    f"churn_date={c_date} < prediction_date={score_str}"
                ),
            }
        )
    counts_by_type["A"] = len(picked_a)

    # =========================================================================
    # ANOMALY B: Offer sent to an ineligible customer
    # =========================================================================
    params_by_rule = _extract_rule_params(rules_df)
    min_tenure_days = int(params_by_rule.get("ER-002", {}).get("min_tenure_days", 90))
    grace_days = int(params_by_rule.get("ER-004", {}).get("grace_days", 7))
    expected_margin_months = int(
        params_by_rule.get("ER-007", {}).get("expected_margin_months", 6)
    )

    cust_inputs = extract_customer_rule_inputs(
        tables=tables,
        risk_scores=rs_df,
        as_of=assign_dt,
        grace_days=grace_days,
    )

    offer_specs = []
    for row in offers_df.itertuples(index=False):
        disc_val = getattr(row, "discount_pct", None)
        disc_pct = None if disc_val is None or pd.isna(disc_val) else float(disc_val)
        free_val = getattr(row, "free_months", None)
        free_m = None if free_val is None or pd.isna(free_val) else int(free_val)
        offer_specs.append(
            (
                str(row.offer_id),
                str(row.offer_type),
                disc_pct,
                free_m,
                int(row.duration_months),
                float(row.max_cost_share_of_margin),
            )
        )
    all_offer_ids = [spec[0] for spec in offer_specs]

    existing_contact_cids = set(cc_df["customer_id"].astype(str))
    # Build pools per failing rule in order ER-003, ER-004, ER-002, ER-005
    b_rule_order = ("ER-003", "ER-004", "ER-002", "ER-005")
    pools_by_rule: dict[str, list[str]] = {r: [] for r in b_rule_order}
    passing_er007_by_cid: dict[str, list[str]] = {}

    for cid in sorted(cust_inputs.keys()):
        inp = cust_inputs[cid]
        # Compute ER-007 passing offers for all scored customers (used by B and D)
        c_pass_offers: list[str] = []
        for oid, otype, disc_pct, free_m, dur_m, max_share in offer_specs:
            res7 = eval_er007_offer_margin(
                offer_id=oid,
                monthly_price_cents=inp["monthly_price_cents"],
                gross_margin_pct=inp["gross_margin_pct"],
                expected_margin_months=expected_margin_months,
                offer_type=otype,
                discount_pct=disc_pct,
                free_months=free_m,
                duration_months=dur_m,
                max_cost_share_of_margin=max_share,
            )
            if res7.passed == 1:
                c_pass_offers.append(oid)
        passing_er007_by_cid[cid] = c_pass_offers

        if cid in used_cids or cid in existing_contact_cids:
            continue
        r1 = eval_er001_active_subscription(inp["has_active_sub"])
        if r1.passed != 1:
            continue

        r2 = eval_er002_min_tenure(inp["signup_date"], assign_dt, min_tenure_days)
        r3 = eval_er003_marketing_opt_in(inp["marketing_opt_in"])
        r4 = eval_er004_no_unsettled_invoice(inp["unsettled_old_invoice_count"])
        r5 = eval_er005_no_open_escalated_case(inp["open_escalated_count"])

        rule_results = {
            "ER-002": r2.passed,
            "ER-003": r3.passed,
            "ER-004": r4.passed,
            "ER-005": r5.passed,
        }
        for r_code in b_rule_order:
            if rule_results[r_code] == 0:
                pools_by_rule[r_code].append(cid)

    rng_b = rng_factory.stream("anomaly_select:B")
    shuffled_pools: dict[str, list[str]] = {}
    for r_code in b_rule_order:
        c_list = sorted(pools_by_rule[r_code])
        if c_list:
            perm = rng_b.permutation(len(c_list))
            shuffled_pools[r_code] = [c_list[int(i)] for i in perm]
        else:
            shuffled_pools[r_code] = []

    picked_b: list[tuple[str, str]] = []
    picked_b_set: set[str] = set()
    pool_cursors: dict[str, int] = {r: 0 for r in b_rule_order}

    while len(picked_b) < n_target:
        made_progress = False
        for r_code in b_rule_order:
            if len(picked_b) >= n_target:
                break
            pool = shuffled_pools[r_code]
            cur = pool_cursors[r_code]
            while cur < len(pool) and pool[cur] in picked_b_set:
                cur += 1
            pool_cursors[r_code] = cur
            if cur < len(pool):
                chosen_cid = pool[cur]
                pool_cursors[r_code] = cur + 1
                picked_b.append((chosen_cid, r_code))
                picked_b_set.add(chosen_cid)
                made_progress = True
        if not made_progress:
            break

    if len(picked_b) < n_target:
        print(
            f"WARNING: Anomaly B candidate pool has {len(picked_b)} < {n_target} candidates"
        )

    added_cc_rows: list[dict[str, Any]] = []
    added_ret_rows: list[dict[str, Any]] = []

    for idx, (cid, violated_rule) in enumerate(picked_b, start=1):
        used_cids.add(cid)
        inp = cust_inputs[cid]
        pass_oids = passing_er007_by_cid.get(cid, [])
        offer_id = pass_oids[0] if pass_oids else all_offer_ids[0]
        contact_id = ids.campaign_contact_id(cid, 2026, 1)

        added_cc_rows.append(
            {
                "contact_id": contact_id,
                "customer_id": cid,
                "offer_id": offer_id,
                "experiment_group": "TREATMENT",
                "contact_status": "SENT",
                "assigned_at": f"{assign_str}T08:00:00",
                "sent_at": f"{assign_str}T10:00:00",
                "stratum": str(inp["risk_band"]),
                "responded": 0,
                "redeemed": 0,
            }
        )

        obs_dt = obs_churn_by_cid.get(cid)
        churned_in_win = (
            obs_dt is not None and (assign_str <= obs_dt < outcome_window_end_str)
        )
        added_ret_rows.append(
            {
                "retention_id": ids.retention_outcome_id(contact_id),
                "contact_id": contact_id,
                "customer_id": cid,
                "attributed_offer_id": None,
                "window_start": assign_str,
                "window_end": outcome_window_end_str,
                "retained": 0 if churned_in_win else 1,
                "churned_at": obs_dt if churned_in_win else None,
            }
        )

        gt_anom_rows.append(
            {
                "anomaly_id": f"ANOM-B-{idx:03d}",
                "anomaly_type": "B",
                "detector_rule_id": "DET-B-INELIGIBLE-OFFER",
                "customer_id": cid,
                "primary_key_table": "campaign_contact",
                "primary_key_value": contact_id,
                "description": (
                    f"Ineligible customer {cid} sent offer {offer_id} "
                    f"(failed {violated_rule})"
                ),
            }
        )
    counts_by_type["B"] = len(picked_b)

    # =========================================================================
    # ANOMALY C: Treatment/Control group leakage (second contact W02 in CONTROL)
    # =========================================================================
    valid_treat_sent = cc_df[
        (cc_df["experiment_group"] == "TREATMENT") & (cc_df["contact_status"] == "SENT")
    ].sort_values("customer_id", kind="mergesort")
    w01_by_cid = {
        str(r.customer_id): r for r in valid_treat_sent.itertuples(index=False)
    }
    ret_w01_by_cid = {
        str(r.customer_id): r for r in ret_df.itertuples(index=False)
    }

    cands_c = [cid for cid in sorted(w01_by_cid.keys()) if cid not in used_cids]
    picked_c = _pick_seeded_candidates(
        cands_c, n_target, "anomaly_select:C", rng_factory, "C"
    )

    for idx, cid in enumerate(picked_c, start=1):
        used_cids.add(cid)
        w01 = w01_by_cid[cid]
        r_w01 = ret_w01_by_cid[cid]
        contact_id_w02 = ids.campaign_contact_id(cid, 2026, 2)
        offer_id = str(w01.offer_id)

        added_cc_rows.append(
            {
                "contact_id": contact_id_w02,
                "customer_id": cid,
                "offer_id": offer_id,
                "experiment_group": "CONTROL",
                "contact_status": "WITHHELD",
                "assigned_at": f"{assign_str}T09:00:00",
                "sent_at": None,
                "stratum": str(w01.stratum),
                "responded": 0,
                "redeemed": 0,
            }
        )
        c_at = getattr(r_w01, "churned_at", None)
        churned_at_val = (
            None if c_at is None or pd.isna(c_at) or str(c_at) == "" else str(c_at)
        )
        added_ret_rows.append(
            {
                "retention_id": ids.retention_outcome_id(contact_id_w02),
                "contact_id": contact_id_w02,
                "customer_id": cid,
                "attributed_offer_id": None,
                "window_start": assign_str,
                "window_end": outcome_window_end_str,
                "retained": int(r_w01.retained),
                "churned_at": churned_at_val,
            }
        )
        gt_anom_rows.append(
            {
                "anomaly_id": f"ANOM-C-{idx:03d}",
                "anomaly_type": "C",
                "detector_rule_id": "DET-C-GROUP-LEAKAGE",
                "customer_id": cid,
                "primary_key_table": "campaign_contact",
                "primary_key_value": contact_id_w02,
                "description": (
                    f"Group leakage: customer {cid} has both TREATMENT (W01) and "
                    f"CONTROL ({contact_id_w02}) contacts"
                ),
            }
        )
    counts_by_type["C"] = len(picked_c)

    # =========================================================================
    # ANOMALY D: Multi-offer attribution (second TREATMENT+SENT contact W02)
    # =========================================================================
    cands_d: list[str] = []
    for cid in sorted(w01_by_cid.keys()):
        if cid in used_cids:
            continue
        w01 = w01_by_cid[cid]
        if int(w01.redeemed) != 1:
            continue
        r_w01 = ret_w01_by_cid.get(cid)
        if r_w01 is None or int(r_w01.retained) != 1:
            continue
        attr_val = getattr(r_w01, "attributed_offer_id", None)
        if attr_val is None or pd.isna(attr_val) or str(attr_val) == "":
            continue
        cands_d.append(cid)

    picked_d = _pick_seeded_candidates(
        cands_d, n_target, "anomaly_select:D", rng_factory, "D"
    )

    for idx, cid in enumerate(picked_d, start=1):
        used_cids.add(cid)
        w01 = w01_by_cid[cid]
        first_offer = str(w01.offer_id)
        # Next offer in order, wrapping around among customer's ER-007 eligible offers
        # (falls back to all offers if fewer than 2 eligible offers)
        elig_oids = passing_er007_by_cid.get(cid, [])
        cycle_oids = elig_oids if len(elig_oids) >= 2 else all_offer_ids
        if first_offer in cycle_oids:
            pos = cycle_oids.index(first_offer)
            second_offer = cycle_oids[(pos + 1) % len(cycle_oids)]
        else:
            second_offer = next((o for o in cycle_oids if o != first_offer), all_offer_ids[0])

        contact_id_w02 = ids.campaign_contact_id(cid, 2026, 2)
        added_cc_rows.append(
            {
                "contact_id": contact_id_w02,
                "customer_id": cid,
                "offer_id": second_offer,
                "experiment_group": "TREATMENT",
                "contact_status": "SENT",
                "assigned_at": f"{assign_str}T09:00:00",
                "sent_at": f"{assign_str}T10:00:00",
                "stratum": str(w01.stratum),
                "responded": 1,
                "redeemed": 1,
            }
        )
        added_ret_rows.append(
            {
                "retention_id": ids.retention_outcome_id(contact_id_w02),
                "contact_id": contact_id_w02,
                "customer_id": cid,
                "attributed_offer_id": second_offer,
                "window_start": assign_str,
                "window_end": outcome_window_end_str,
                "retained": 1,
                "churned_at": None,
            }
        )
        gt_anom_rows.append(
            {
                "anomaly_id": f"ANOM-D-{idx:03d}",
                "anomaly_type": "D",
                "detector_rule_id": "DET-D-MULTI-ATTRIBUTION",
                "customer_id": cid,
                "primary_key_table": "campaign_contact",
                "primary_key_value": contact_id_w02,
                "description": (
                    f"Multi-offer attribution: customer {cid} retained and attributed "
                    f"to both {first_offer} and {second_offer}"
                ),
            }
        )
    counts_by_type["D"] = len(picked_d)

    # Append injected rows and sort deterministically by PK
    if added_churn_rows:
        churn_df = (
            pd.concat(
                [churn_df, pd.DataFrame(added_churn_rows, columns=churn_df.columns)],
                ignore_index=True,
            )
            .sort_values("churn_id", kind="mergesort")
            .reset_index(drop=True)
        )
    if added_cc_rows:
        cc_df = (
            pd.concat(
                [cc_df, pd.DataFrame(added_cc_rows, columns=cc_df.columns)],
                ignore_index=True,
            )
            .sort_values("contact_id", kind="mergesort")
            .reset_index(drop=True)
        )
    if added_ret_rows:
        ret_df = (
            pd.concat(
                [ret_df, pd.DataFrame(added_ret_rows, columns=ret_df.columns)],
                ignore_index=True,
            )
            .sort_values("retention_id", kind="mergesort")
            .reset_index(drop=True)
        )

    out_tables = dict(tables)
    out_tables["churn_outcome"] = churn_df
    out_tables["campaign_contact"] = cc_df
    out_tables["retention_outcome"] = ret_df

    anomalies_gt_df = pd.DataFrame(gt_anom_rows, columns=ANOMALIES_GT_COLUMNS)
    rule_eval = tables.get("rule_evaluation")
    if rule_eval is not None and not rule_eval.empty:
        date_col = "as_of_date" if "as_of_date" in rule_eval.columns else "evaluation_date"
        expected_decisions_gt_df = (
            rule_eval[
                ["customer_id", date_col, "rule_id", "offer_id", "passed"]
            ]
            .rename(columns={date_col: "as_of_date"})
            .sort_values(["customer_id", "rule_id", "offer_id"], kind="mergesort")
            .reset_index(drop=True)
        )
    else:
        expected_decisions_gt_df = pd.DataFrame(
            columns=EXPECTED_DECISIONS_GT_COLUMNS
        )

    return AnomalyInjectionResult(
        tables=out_tables,
        anomalies_gt=anomalies_gt_df,
        expected_decisions_gt=expected_decisions_gt_df,
        counts_by_type=counts_by_type,
    )

