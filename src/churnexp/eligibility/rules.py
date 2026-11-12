"""Pure point-in-time eligibility and margin rule evaluation functions (ER-001..ER-007)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Mapping
import pandas as pd


@dataclass(frozen=True)
class RuleEvalResult:
    rule_id: str
    offer_id: str | None
    passed: int
    observed_value: str
    threshold_value: str


def _to_date(val: date | datetime | str) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        return date.fromisoformat(val[:10])
    raise ValueError(f"Cannot parse date from {val!r}")


def compute_offer_cost_and_max_margin_cents(
    monthly_price_cents: int,
    gross_margin_pct: float,
    expected_margin_months: int,
    offer_type: str,
    discount_pct: float | None,
    free_months: int | None,
    duration_months: int,
    max_cost_share_of_margin: float,
) -> tuple[int, int, int]:
    """Compute (offer_cost_cents, expected_margin_cents, max_allowed_cost_cents) rounded to integer cents."""
    price = int(monthly_price_cents)
    margin_pct = float(gross_margin_pct)
    exp_months = int(expected_margin_months)

    if offer_type == "PERCENT_DISCOUNT":
        if discount_pct is None:
            raise ValueError("PERCENT_DISCOUNT offer requires discount_pct")
        offer_cost_cents = int(
            round(float(discount_pct) * price * int(duration_months))
        )
    elif offer_type == "FREE_MONTH":
        if free_months is None:
            raise ValueError("FREE_MONTH offer requires free_months")
        offer_cost_cents = int(round(price * int(free_months)))
    else:
        raise ValueError(f"Unknown offer_type: {offer_type!r}")

    expected_margin_cents = int(round(price * margin_pct * exp_months))
    max_allowed_cost_cents = int(
        round(float(max_cost_share_of_margin) * price * margin_pct * exp_months)
    )
    return offer_cost_cents, expected_margin_cents, max_allowed_cost_cents


def eval_er001_active_subscription(
    has_active_sub: bool,
) -> RuleEvalResult:
    """ER-001: Customer has a subscription active on assignment_date (start_date < as_of and end_date null or >= as_of)."""
    return RuleEvalResult(
        rule_id="ER-001",
        offer_id=None,
        passed=1 if has_active_sub else 0,
        observed_value="ACTIVE" if has_active_sub else "INACTIVE",
        threshold_value="ACTIVE",
    )


def eval_er002_min_tenure(
    signup_date: date | str,
    as_of: date | str,
    min_tenure_days: int = 90,
) -> RuleEvalResult:
    """ER-002: Customer tenure at as_of is at least min_tenure_days."""
    as_of_dt = _to_date(as_of)
    signup_dt = _to_date(signup_date)
    tenure_days = (as_of_dt - signup_dt).days
    passed = 1 if tenure_days >= int(min_tenure_days) else 0
    return RuleEvalResult(
        rule_id="ER-002",
        offer_id=None,
        passed=passed,
        observed_value=str(tenure_days),
        threshold_value=str(int(min_tenure_days)),
    )


def eval_er003_marketing_opt_in(
    marketing_opt_in: int,
) -> RuleEvalResult:
    """ER-003: Customer has marketing_opt_in == 1."""
    opt_val = int(marketing_opt_in)
    return RuleEvalResult(
        rule_id="ER-003",
        offer_id=None,
        passed=1 if opt_val == 1 else 0,
        observed_value=str(opt_val),
        threshold_value="1",
    )


def eval_er004_no_unsettled_invoice(
    unsettled_old_invoice_count: int,
) -> RuleEvalResult:
    """ER-004: No invoice earlier than (assignment_date - grace_days) unsettled before assignment_date."""
    cnt = int(unsettled_old_invoice_count)
    return RuleEvalResult(
        rule_id="ER-004",
        offer_id=None,
        passed=1 if cnt == 0 else 0,
        observed_value=str(cnt),
        threshold_value="0",
    )


def eval_er005_no_open_escalated_case(
    open_escalated_count: int,
) -> RuleEvalResult:
    """ER-005: No open escalated support case at assignment_date."""
    cnt = int(open_escalated_count)
    return RuleEvalResult(
        rule_id="ER-005",
        offer_id=None,
        passed=1 if cnt == 0 else 0,
        observed_value=str(cnt),
        threshold_value="0",
    )


def eval_er006_risk_band(
    risk_band: str,
    allowed_bands: tuple[str, ...] = ("HIGH", "MEDIUM"),
) -> RuleEvalResult:
    """ER-006: Customer risk_band in ('HIGH', 'MEDIUM')."""
    band_str = str(risk_band)
    return RuleEvalResult(
        rule_id="ER-006",
        offer_id=None,
        passed=1 if band_str in allowed_bands else 0,
        observed_value=band_str,
        threshold_value=",".join(allowed_bands),
    )


def eval_er007_offer_margin(
    offer_id: str,
    monthly_price_cents: int,
    gross_margin_pct: float,
    expected_margin_months: int,
    offer_type: str,
    discount_pct: float | None,
    free_months: int | None,
    duration_months: int,
    max_cost_share_of_margin: float,
) -> RuleEvalResult:
    """ER-007: Offer cost <= max_cost_share_of_margin * expected_margin (rounded to integer cents)."""
    cost_cents, _, max_cost_cents = compute_offer_cost_and_max_margin_cents(
        monthly_price_cents=monthly_price_cents,
        gross_margin_pct=gross_margin_pct,
        expected_margin_months=expected_margin_months,
        offer_type=offer_type,
        discount_pct=discount_pct,
        free_months=free_months,
        duration_months=duration_months,
        max_cost_share_of_margin=max_cost_share_of_margin,
    )
    return RuleEvalResult(
        rule_id="ER-007",
        offer_id=str(offer_id),
        passed=1 if cost_cents <= max_cost_cents else 0,
        observed_value=str(cost_cents),
        threshold_value=str(max_cost_cents),
    )


def extract_customer_rule_inputs(
    tables: Mapping[str, pd.DataFrame],
    risk_scores: pd.DataFrame,
    as_of: date | str,
    grace_days: int = 7,
) -> dict[str, dict[str, Any]]:
    """Extract leakage-safe per-customer inputs strictly prior to `as_of` for rules ER-001..ER-007."""
    as_of_dt = _to_date(as_of)
    as_of_str = as_of_dt.isoformat()
    grace_cutoff_str = (as_of_dt - timedelta(days=int(grace_days))).isoformat()

    scored_sorted = risk_scores.sort_values("customer_id", kind="mergesort")
    scored_cids = [str(c) for c in scored_sorted["customer_id"].tolist()]
    scored_cid_set = set(scored_cids)
    band_by_cid = {
        str(row.customer_id): str(row.band)
        for row in scored_sorted.itertuples(index=False)
    }

    cust_df = tables["customer"]
    signup_by_cid: dict[str, str] = {}
    optin_by_cid: dict[str, int] = {}
    for row in cust_df.itertuples(index=False):
        cid = str(row.customer_id)
        if cid in scored_cid_set:
            signup_by_cid[cid] = str(row.signup_date)
            optin_by_cid[cid] = int(row.marketing_opt_in)

    # Subscriptions strictly with start_date < as_of_str
    raw_sub_df = tables["subscription"]
    sub_prior = raw_sub_df[raw_sub_df["start_date"].astype(str) < as_of_str].sort_values(
        ["customer_id", "sequence_no"], kind="mergesort"
    )
    sub_to_cid: dict[str, str] = {}
    has_active_by_cid: dict[str, bool] = {cid: False for cid in scored_cids}
    # Store (monthly_price_cents, gross_margin_pct) of current active sub (or latest prior sub if inactive)
    sub_terms_by_cid: dict[str, tuple[int, float]] = {}

    for row in sub_prior.itertuples(index=False):
        cid = str(row.customer_id)
        sid = str(row.subscription_id)
        sub_to_cid[sid] = cid
        if cid not in scored_cid_set:
            continue
        end_val = getattr(row, "end_date", None)
        is_active = (
            end_val is None
            or pd.isna(end_val)
            or str(end_val) == ""
            or str(end_val) >= as_of_str
        )
        price = int(row.monthly_price_cents)
        margin = float(row.gross_margin_pct)
        if is_active:
            has_active_by_cid[cid] = True
            sub_terms_by_cid[cid] = (price, margin)
        elif cid not in sub_terms_by_cid:
            sub_terms_by_cid[cid] = (price, margin)

    # Billing events strictly before as_of_str
    raw_bill_df = tables["billing_event"]
    unsettled_old_by_cid: dict[str, int] = {cid: 0 for cid in scored_cids}
    if not raw_bill_df.empty:
        b_prior = raw_bill_df[raw_bill_df["event_date"].astype(str) < as_of_str]
        old_invoices: list[tuple[str, str]] = []
        settled_inv_ids: set[str] = set()

        for row in b_prior.itertuples(index=False):
            sid = str(row.subscription_id)
            cid = sub_to_cid.get(sid)
            if cid is None or cid not in scored_cid_set:
                continue
            ev_type = str(row.event_type)
            ev_date = str(row.event_date)
            status = str(row.status)
            if ev_type == "INVOICE":
                if ev_date < grace_cutoff_str:
                    old_invoices.append((str(row.billing_event_id), cid))
            elif status == "SETTLED" and ev_type in ("PAYMENT", "RETRY"):
                rel_val = getattr(row, "related_event_id", None)
                if rel_val is not None and not pd.isna(rel_val) and str(rel_val) != "":
                    settled_inv_ids.add(str(rel_val))

        for inv_id, cid in old_invoices:
            if inv_id not in settled_inv_ids:
                unsettled_old_by_cid[cid] += 1

    # Support cases strictly with opened_at < as_of_str
    raw_sup_df = tables["support_case"]
    open_esc_by_cid: dict[str, int] = {cid: 0 for cid in scored_cids}
    if not raw_sup_df.empty:
        s_prior = raw_sup_df[
            raw_sup_df["opened_at"].astype(str).str.slice(0, 10) < as_of_str
        ]
        for row in s_prior.itertuples(index=False):
            cid = str(row.customer_id)
            if cid not in scored_cid_set:
                continue
            if int(row.escalated) != 1:
                continue
            res_val = getattr(row, "resolved_at", None)
            is_open_at_as_of = (
                res_val is None
                or pd.isna(res_val)
                or str(res_val) == ""
                or str(res_val)[:10] >= as_of_str
            )
            if is_open_at_as_of:
                open_esc_by_cid[cid] += 1

    inputs: dict[str, dict[str, Any]] = {}
    for cid in scored_cids:
        price, margin = sub_terms_by_cid.get(cid, (0, 0.0))
        inputs[cid] = {
            "has_active_sub": has_active_by_cid[cid],
            "signup_date": signup_by_cid[cid],
            "marketing_opt_in": optin_by_cid[cid],
            "unsettled_old_invoice_count": unsettled_old_by_cid[cid],
            "open_escalated_count": open_esc_by_cid[cid],
            "risk_band": band_by_cid[cid],
            "monthly_price_cents": price,
            "gross_margin_pct": margin,
        }
    return inputs

