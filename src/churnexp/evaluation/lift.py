"""Intention-to-Treat (ITT) lift, subgroup analysis, randomization balance, and naive comparisons."""

from __future__ import annotations

import math
from typing import Any, Mapping
import numpy as np
import pandas as pd

from churnexp.validation.report import Finding

Z_95: float = 1.959963984540054


def _round6(val: float) -> float:
    return round(float(val), 6)


def normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    return 0.5 * (1.0 + math.erf(float(z) / math.sqrt(2.0)))


def compute_two_proportion_stats(
    n_treatment: int,
    retained_treatment: int,
    n_control: int,
    retained_control: int,
) -> dict[str, Any]:
    """Compute ITT retention rates, lift, unpooled 95% CI, pooled z-test p-value, incremental saves, and NNT."""
    n_t = int(n_treatment)
    r_t = int(retained_treatment)
    n_c = int(n_control)
    r_c = int(retained_control)

    p_t = (r_t / float(n_t)) if n_t > 0 else 0.0
    p_c = (r_c / float(n_c)) if n_c > 0 else 0.0

    # If either arm is empty, lift, CI, p-value, and incremental retained are undefined (null)
    if n_t == 0 or n_c == 0:
        return {
            "n_treatment": n_t,
            "retained_treatment": r_t,
            "rate_treatment": _round6(p_t) if n_t > 0 else 0.0,
            "n_control": n_c,
            "retained_control": r_c,
            "rate_control": _round6(p_c) if n_c > 0 else 0.0,
            "absolute_lift": None,
            "absolute_lift_pp": None,
            "se_unpooled": None,
            "ci_95_low": None,
            "ci_95_high": None,
            "ci_95_low_pp": None,
            "ci_95_high_pp": None,
            "z_stat_pooled": None,
            "p_value": None,
            "relative_lift": None,
            "incremental_retained": None,
            "incremental_retained_ci_low": None,
            "incremental_retained_ci_high": None,
            "nnt": None,
        }

    lift = p_t - p_c
    lift_pp = lift * 100.0

    # Unpooled standard error for 95% confidence interval
    var_unpooled = (p_t * (1.0 - p_t) / float(n_t)) + (
        p_c * (1.0 - p_c) / float(n_c)
    )
    se_unpooled = math.sqrt(max(0.0, var_unpooled))

    ci_low = lift - Z_95 * se_unpooled
    ci_high = lift + Z_95 * se_unpooled

    # Pooled z-test for two-sided p-value
    p_pool = (r_t + r_c) / float(n_t + n_c)
    var_pool = p_pool * (1.0 - p_pool) * (1.0 / float(n_t) + 1.0 / float(n_c))
    se_pool = math.sqrt(max(0.0, var_pool))

    if se_pool > 0.0:
        z_stat = lift / se_pool
        p_value = 2.0 * (1.0 - normal_cdf(abs(z_stat)))
    else:
        z_stat = 0.0
        p_value = 1.0 if abs(lift) == 0.0 else 0.0

    rel_lift = (lift / p_c) if p_c > 0.0 else 0.0
    inc_ret = lift * float(n_t)
    inc_ci_low = ci_low * float(n_t)
    inc_ci_high = ci_high * float(n_t)
    nnt: float | None = _round6(1.0 / lift) if lift > 0.0 else None

    return {
        "n_treatment": n_t,
        "retained_treatment": r_t,
        "rate_treatment": _round6(p_t),
        "n_control": n_c,
        "retained_control": r_c,
        "rate_control": _round6(p_c),
        "absolute_lift": _round6(lift),
        "absolute_lift_pp": _round6(lift_pp),
        "se_unpooled": _round6(se_unpooled),
        "ci_95_low": _round6(ci_low),
        "ci_95_high": _round6(ci_high),
        "ci_95_low_pp": _round6(ci_low * 100.0),
        "ci_95_high_pp": _round6(ci_high * 100.0),
        "z_stat_pooled": _round6(z_stat),
        "p_value": _round6(p_value),
        "relative_lift": _round6(rel_lift),
        "incremental_retained": _round6(inc_ret),
        "incremental_retained_ci_low": _round6(inc_ci_low),
        "incremental_retained_ci_high": _round6(inc_ci_high),
        "nnt": nnt,
    }


def _compute_smd(vals_t: np.ndarray, vals_c: np.ndarray) -> tuple[float, float, float]:
    if len(vals_t) == 0 or len(vals_c) == 0:
        return 0.0, 0.0, 0.0
    mean_t = float(np.mean(vals_t))
    mean_c = float(np.mean(vals_c))
    if len(vals_t) < 2 or len(vals_c) < 2:
        return _round6(mean_t), _round6(mean_c), 0.0
    var_t = float(np.var(vals_t, ddof=1))
    var_c = float(np.var(vals_c, ddof=1))
    denom = math.sqrt(max(0.0, (var_t + var_c) / 2.0))
    smd = (abs(mean_t - mean_c) / denom) if denom > 0.0 else 0.0
    return _round6(mean_t), _round6(mean_c), _round6(smd)


def evaluate_experiment_lift(
    tables: Mapping[str, pd.DataFrame],
    detector_findings: list[Finding],
    score_as_of: str = "2026-01-01",
) -> dict[str, Any]:
    """Compute primary 90d and secondary 180d ITT lift, subgroups, balance, and naive comparisons."""
    flagged_cids: set[str] = {
        str(f.evidence["customer_id"])
        for f in detector_findings
        if "customer_id" in f.evidence and f.evidence["customer_id"]
    }

    cc_df = tables.get("campaign_contact", pd.DataFrame())
    ret_df = tables.get("retention_outcome", pd.DataFrame())
    churn_df = tables.get("churn_outcome", pd.DataFrame())
    rs_df = tables.get("risk_score", pd.DataFrame())
    feat_df = tables.get("feature_snapshot", pd.DataFrame())

    if cc_df.empty or ret_df.empty:
        empty_stats = compute_two_proportion_stats(0, 0, 0, 0)
        return {
            "unit_count": 0,
            "primary_90d": empty_stats,
            "secondary_180d": empty_stats,
            "subgroups": {"exploratory": True, "by_offer": {}, "by_stratum": {}},
            "randomization_check": {
                "stratum_arm_sizes": {},
                "covariate_balance": {},
                "any_flagged": False,
            },
            "correlation_vs_incremental": {},
        }

    # Unit = customer with exactly one campaign_contact (W01) and not flagged by any detector
    cc_unflagged = cc_df[~cc_df["customer_id"].astype(str).isin(flagged_cids)].copy()
    contact_counts = cc_unflagged.groupby("customer_id")["contact_id"].count()
    single_contact_cids = set(contact_counts[contact_counts == 1].index.astype(str))
    w01_df = cc_unflagged[
        cc_unflagged["customer_id"].astype(str).isin(single_contact_cids)
        & cc_unflagged["contact_id"].astype(str).str.endswith("-W01")
    ].copy()

    # Merge 90-day retention_outcome
    merged = w01_df.merge(
        ret_df[["contact_id", "retained", "attributed_offer_id"]],
        on="contact_id",
        how="inner",
    )
    merged["retained_90d"] = merged["retained"].astype(int)

    # Merge 180-day churn_outcome (cycle_year == 2026)
    if not churn_df.empty:
        ch_2026 = churn_df[churn_df["cycle_year"].astype(int) == 2026][
            ["customer_id", "churned"]
        ].copy()
        merged = merged.merge(ch_2026, on="customer_id", how="left")
        merged["retained_180d"] = 1 - merged["churned"].fillna(0).astype(int)
    else:
        merged["retained_180d"] = merged["retained_90d"]

    merged = merged.sort_values("customer_id", kind="mergesort").reset_index(drop=True)

    def _stats_for_slice(sub: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
        t_rows = sub[sub["experiment_group"] == "TREATMENT"]
        c_rows = sub[sub["experiment_group"] == "CONTROL"]
        s90 = compute_two_proportion_stats(
            n_treatment=len(t_rows),
            retained_treatment=int(t_rows["retained_90d"].sum()),
            n_control=len(c_rows),
            retained_control=int(c_rows["retained_90d"].sum()),
        )
        s180 = compute_two_proportion_stats(
            n_treatment=len(t_rows),
            retained_treatment=int(t_rows["retained_180d"].sum()),
            n_control=len(c_rows),
            retained_control=int(c_rows["retained_180d"].sum()),
        )
        return s90, s180

    primary_90d, secondary_180d = _stats_for_slice(merged)

    # Exploratory subgroups: by planned offer and by risk stratum
    by_offer: dict[str, Any] = {}
    for oid in sorted(merged["offer_id"].astype(str).unique()):
        o_sub = merged[merged["offer_id"].astype(str) == oid]
        o90, o180 = _stats_for_slice(o_sub)
        by_offer[oid] = {
            "exploratory": True,
            "primary_90d": o90,
            "secondary_180d": o180,
        }

    by_stratum: dict[str, Any] = {}
    strata_order = [
        s for s in ("HIGH", "MEDIUM") if s in set(merged["stratum"].astype(str))
    ] + [
        s
        for s in sorted(merged["stratum"].astype(str).unique())
        if s not in ("HIGH", "MEDIUM")
    ]
    stratum_arm_sizes: dict[str, dict[str, int]] = {}
    for strat in strata_order:
        s_sub = merged[merged["stratum"].astype(str) == strat]
        s90, s180 = _stats_for_slice(s_sub)
        by_stratum[strat] = {
            "exploratory": True,
            "primary_90d": s90,
            "secondary_180d": s180,
        }
        stratum_arm_sizes[strat] = {
            "TREATMENT": s90["n_treatment"],
            "CONTROL": s90["n_control"],
        }

    # Randomization covariate balance check
    cov_balance: dict[str, Any] = {}
    any_smd_flagged = False
    if not rs_df.empty and not feat_df.empty:
        feat_p = feat_df[feat_df["as_of_date"].astype(str) == str(score_as_of)[:10]]
        cov_df = (
            merged[["customer_id", "experiment_group"]]
            .merge(rs_df[["customer_id", "score"]], on="customer_id", how="inner")
            .merge(
                feat_p[["customer_id", "tenure_days", "monthly_price_cents"]],
                on="customer_id",
                how="inner",
            )
        )
        t_cov = cov_df[cov_df["experiment_group"] == "TREATMENT"]
        c_cov = cov_df[cov_df["experiment_group"] == "CONTROL"]
        for cov_name, col_name in [
            ("risk_score", "score"),
            ("tenure_days", "tenure_days"),
            ("monthly_price_cents", "monthly_price_cents"),
        ]:
            mt, mc, smd = _compute_smd(
                t_cov[col_name].to_numpy(dtype=np.float64),
                c_cov[col_name].to_numpy(dtype=np.float64),
            )
            is_flag = smd >= 0.10
            if is_flag:
                any_smd_flagged = True
            cov_balance[cov_name] = {
                "mean_treatment": mt,
                "mean_control": mc,
                "smd": smd,
                "flagged": is_flag,
            }

    # Correlation vs incremental comparison
    t_all = merged[merged["experiment_group"] == "TREATMENT"]
    t_redeem = t_all[t_all["redeemed"].astype(int) == 1]
    n_redeemers = len(t_redeem)
    red_ret_90 = int(t_redeem["retained_90d"].sum()) if n_redeemers > 0 else 0
    red_ret_180 = int(t_redeem["retained_180d"].sum()) if n_redeemers > 0 else 0
    red_rate_90 = (red_ret_90 / float(n_redeemers)) if n_redeemers > 0 else 0.0
    red_rate_180 = (red_ret_180 / float(n_redeemers)) if n_redeemers > 0 else 0.0

    attr_mask = merged["attributed_offer_id"].notna() & (
        merged["attributed_offer_id"].astype(str) != ""
    )
    attributed_count = int(attr_mask.sum())

    corr_vs_inc = {
        "a_treatment_all_retention_rate_90d": primary_90d["rate_treatment"],
        "a_treatment_all_retention_rate_180d": secondary_180d["rate_treatment"],
        "b_redeemers_retention_rate_90d": _round6(red_rate_90),
        "b_redeemers_retention_rate_180d": _round6(red_rate_180),
        "n_redeemers": n_redeemers,
        "retained_redeemers_90d": red_ret_90,
        "retained_redeemers_180d": red_ret_180,
        "c_control_retention_rate_90d": primary_90d["rate_control"],
        "c_control_retention_rate_180d": secondary_180d["rate_control"],
        "d_attributed_retained_customers": attributed_count,
        "e_incremental_retained_customers_90d": primary_90d["incremental_retained"],
        "e_incremental_retained_customers_180d": secondary_180d["incremental_retained"],
        "why_not_causal": (
            "Metrics (a), (b), and (d) are not causal because customers who respond and redeem "
            "are self-selected and include many customers who would have stayed without any offer, "
            "whereas only the randomized ITT comparison against the withheld control group (e) "
            "isolates true incremental saves."
        ),
    }

    return {
        "unit_count": len(merged),
        "primary_90d": primary_90d,
        "secondary_180d": secondary_180d,
        "subgroups": {
            "exploratory": True,
            "by_offer": by_offer,
            "by_stratum": by_stratum,
        },
        "randomization_check": {
            "stratum_arm_sizes": stratum_arm_sizes,
            "covariate_balance": cov_balance,
            "any_flagged": any_smd_flagged,
        },
        "correlation_vs_incremental": corr_vs_inc,
    }

