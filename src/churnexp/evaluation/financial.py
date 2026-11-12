"""Financial impact evaluation in integer cents (realized offer cost vs incremental margin)."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping
import pandas as pd

from churnexp.eligibility.rules import compute_offer_cost_and_max_margin_cents
from churnexp.validation.report import Finding


def _lookup_customer_sub_terms(
    sub_df: pd.DataFrame,
    as_of_str: str,
) -> dict[str, tuple[int, float]]:
    """Return customer_id -> (monthly_price_cents, gross_margin_pct) active on or prior to as_of_str."""
    if sub_df.empty:
        return {}
    sub_prior = sub_df[sub_df["start_date"].astype(str) <= as_of_str].sort_values(
        ["customer_id", "sequence_no"], kind="mergesort"
    )
    terms: dict[str, tuple[int, float]] = {}
    for row in sub_prior.itertuples(index=False):
        cid = str(row.customer_id)
        e_val = getattr(row, "end_date", None)
        is_active = (
            e_val is None
            or pd.isna(e_val)
            or str(e_val) == ""
            or str(e_val)[:10] >= as_of_str
        )
        price = int(row.monthly_price_cents)
        margin = float(row.gross_margin_pct)
        if is_active:
            terms[cid] = (price, margin)
        elif cid not in terms:
            terms[cid] = (price, margin)
    return terms


def _compute_horizon_financials(
    horizon_label: str,
    lift_stats: dict[str, Any],
    realized_cost_cents: int,
    avg_expected_margin_cents: int,
) -> dict[str, Any]:
    n_t = int(lift_stats["n_treatment"])
    lift = float(lift_stats["absolute_lift"])
    ci_low = float(lift_stats["ci_95_low"])
    ci_high = float(lift_stats["ci_95_high"])

    inc_ret = lift * float(n_t)
    inc_low = ci_low * float(n_t)
    inc_high = ci_high * float(n_t)

    benefit_cents = int(round(inc_ret * float(avg_expected_margin_cents)))
    benefit_low_cents = int(round(inc_low * float(avg_expected_margin_cents)))
    benefit_high_cents = int(round(inc_high * float(avg_expected_margin_cents)))

    net_cents = benefit_cents - int(realized_cost_cents)
    net_low_cents = benefit_low_cents - int(realized_cost_cents)
    net_high_cents = benefit_high_cents - int(realized_cost_cents)

    cost_per_inc_cents: int | None = (
        int(round(float(realized_cost_cents) / inc_ret)) if inc_ret > 0.0 else None
    )

    is_negative = net_cents < 0
    ci_includes_zero = net_low_cents <= 0 <= net_high_cents

    if is_negative and ci_includes_zero:
        statement = (
            f"For the {horizon_label} horizon, point-estimate net financial impact is negative "
            f"({net_cents} cents) and the 95% confidence interval [{net_low_cents}, {net_high_cents}] "
            f"cents includes zero."
        )
    elif is_negative:
        statement = (
            f"For the {horizon_label} horizon, net financial impact is negative ({net_cents} cents; "
            f"95% CI [{net_low_cents}, {net_high_cents}] cents)."
        )
    elif ci_includes_zero:
        statement = (
            f"For the {horizon_label} horizon, point-estimate net financial impact is positive "
            f"({net_cents} cents), but the 95% confidence interval [{net_low_cents}, {net_high_cents}] "
            f"cents includes zero."
        )
    else:
        statement = (
            f"For the {horizon_label} horizon, net financial impact is positive ({net_cents} cents) "
            f"and the 95% confidence interval [{net_low_cents}, {net_high_cents}] cents excludes zero."
        )

    return {
        "horizon": horizon_label,
        "incremental_retained_customers": round(inc_ret, 6),
        "incremental_retained_ci_low": round(inc_low, 6),
        "incremental_retained_ci_high": round(inc_high, 6),
        "avg_expected_margin_cents": int(avg_expected_margin_cents),
        "realized_cost_cents": int(realized_cost_cents),
        "benefit_cents": benefit_cents,
        "benefit_ci_low_cents": benefit_low_cents,
        "benefit_ci_high_cents": benefit_high_cents,
        "net_impact_cents": net_cents,
        "net_impact_ci_low_cents": net_low_cents,
        "net_impact_ci_high_cents": net_high_cents,
        "cost_per_incremental_retained_cents": cost_per_inc_cents,
        "is_negative": is_negative,
        "ci_includes_zero": ci_includes_zero,
        "plain_statement": statement,
    }


def evaluate_financial_impact(
    tables: Mapping[str, pd.DataFrame],
    detector_findings: list[Finding],
    lift_results: dict[str, Any],
    assignment_date: date | str = "2026-01-05",
    expected_margin_months: int = 6,
) -> dict[str, Any]:
    """Compute realized offer cost, average expected margin, benefit, and net financial impact."""
    flagged_cids: set[str] = {
        str(f.evidence["customer_id"])
        for f in detector_findings
        if "customer_id" in f.evidence and f.evidence["customer_id"]
    }

    as_of_str = (
        assignment_date.isoformat()
        if isinstance(assignment_date, date)
        else str(assignment_date)[:10]
    )

    cc_df = tables.get("campaign_contact", pd.DataFrame())
    ret_df = tables.get("retention_outcome", pd.DataFrame())
    sub_df = tables.get("subscription", pd.DataFrame())
    offers_df = tables.get("offer", pd.DataFrame())

    offer_specs: dict[str, dict[str, Any]] = {}
    if not offers_df.empty:
        for row in offers_df.itertuples(index=False):
            disc_val = getattr(row, "discount_pct", None)
            disc_pct = (
                None
                if disc_val is None or pd.isna(disc_val) or str(disc_val) == ""
                else float(disc_val)
            )
            free_val = getattr(row, "free_months", None)
            free_m = (
                None
                if free_val is None or pd.isna(free_val) or str(free_val) == ""
                else int(free_val)
            )
            offer_specs[str(row.offer_id)] = {
                "offer_type": str(row.offer_type),
                "discount_pct": disc_pct,
                "free_months": free_m,
                "duration_months": int(row.duration_months),
                "max_cost_share_of_margin": float(row.max_cost_share_of_margin),
            }

    sub_terms = _lookup_customer_sub_terms(sub_df, as_of_str)

    if cc_df.empty or ret_df.empty:
        zero_fin_180 = _compute_horizon_financials(
            "180d", lift_results["secondary_180d"], 0, 0
        )
        zero_fin_90 = _compute_horizon_financials(
            "90d", lift_results["primary_90d"], 0, 0
        )
        return {
            "expected_margin_months": int(expected_margin_months),
            "realized_cost_cents": 0,
            "avg_expected_margin_cents": 0,
            "redeemed_retained_90d_count": 0,
            "headline_180d": zero_fin_180,
            "primary_90d": zero_fin_90,
        }

    cc_unflagged = cc_df[~cc_df["customer_id"].astype(str).isin(flagged_cids)].copy()
    contact_counts = cc_unflagged.groupby("customer_id")["contact_id"].count()
    single_contact_cids = set(contact_counts[contact_counts == 1].index.astype(str))
    w01_treat = cc_unflagged[
        cc_unflagged["customer_id"].astype(str).isin(single_contact_cids)
        & cc_unflagged["contact_id"].astype(str).str.endswith("-W01")
        & (cc_unflagged["experiment_group"] == "TREATMENT")
    ].merge(
        ret_df[["contact_id", "retained"]],
        on="contact_id",
        how="inner",
    )

    realized_cost_cents = 0
    redeemed_retained_count = 0
    expected_margins: list[float] = []

    for row in w01_treat.itertuples(index=False):
        cid = str(row.customer_id)
        oid = str(row.offer_id)
        price, margin_pct = sub_terms.get(cid, (0, 0.0))
        expected_margins.append(
            float(price) * float(margin_pct) * int(expected_margin_months)
        )

        if int(row.redeemed) == 1 and int(row.retained) == 1 and oid in offer_specs:
            ospec = offer_specs[oid]
            cost_cents, _, _ = compute_offer_cost_and_max_margin_cents(
                monthly_price_cents=price,
                gross_margin_pct=margin_pct,
                expected_margin_months=int(expected_margin_months),
                offer_type=ospec["offer_type"],
                discount_pct=ospec["discount_pct"],
                free_months=ospec["free_months"],
                duration_months=ospec["duration_months"],
                max_cost_share_of_margin=ospec["max_cost_share_of_margin"],
            )
            realized_cost_cents += int(cost_cents)
            redeemed_retained_count += 1

    avg_expected_margin_cents = (
        int(round(sum(expected_margins) / float(len(expected_margins))))
        if expected_margins
        else 0
    )

    headline_180d = _compute_horizon_financials(
        horizon_label="180d",
        lift_stats=lift_results["secondary_180d"],
        realized_cost_cents=realized_cost_cents,
        avg_expected_margin_cents=avg_expected_margin_cents,
    )
    primary_90d = _compute_horizon_financials(
        horizon_label="90d",
        lift_stats=lift_results["primary_90d"],
        realized_cost_cents=realized_cost_cents,
        avg_expected_margin_cents=avg_expected_margin_cents,
    )

    return {
        "expected_margin_months": int(expected_margin_months),
        "realized_cost_cents": int(realized_cost_cents),
        "avg_expected_margin_cents": int(avg_expected_margin_cents),
        "redeemed_retained_90d_count": redeemed_retained_count,
        "headline_180d": headline_180d,
        "primary_90d": primary_90d,
    }

