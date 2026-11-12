"""Leakage-safe point-in-time feature builder for churnexp (ADR-004)."""

import calendar
from datetime import date, datetime
from typing import Any, Mapping
import pandas as pd

TIER_RANK: dict[str, int] = {"BASIC": 0, "STANDARD": 1, "PREMIUM": 2}

FEATURE_SNAPSHOT_COLUMNS: list[str] = [
    "customer_id",
    "as_of_date",
    "window_start",
    "window_end",
    "usage_minutes_3m",
    "usage_minutes_prev3m",
    "usage_ratio_3m_vs_prev3m",
    "last_month_active_days",
    "usage_slope_6m",
    "sessions_6m",
    "failed_payments_6m",
    "days_since_last_failed_payment",
    "outstanding_balance_cents",
    "support_cases_6m",
    "high_severity_cases_6m",
    "cancellation_inquiries_6m",
    "tenure_days",
    "plan_tier",
    "monthly_price_cents",
    "plan_downgrade_6m",
    "segment",
    "channel",
    "is_seasonal",
]


def _to_date(val: date | datetime | str) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        return date.fromisoformat(val[:10])
    raise ValueError(f"Cannot parse date from {val!r}")


def _subtract_months(d: date, months: int) -> date:
    total_months = (d.year * 12 + (d.month - 1)) - months
    year, month_zero = divmod(total_months, 12)
    month = month_zero + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def _window_month_strings(as_of_dt: date, lookback_months: int) -> list[str]:
    """Return the `lookback_months` full YYYY-MM strings ending strictly before `as_of_dt`."""
    # A month (y, m) is a full month before as_of_dt if its period_end < as_of_dt
    # Start from the month before as_of_dt if as_of_dt is not after month end
    cur_y, cur_m = as_of_dt.year, as_of_dt.month
    days_in_cur = calendar.monthrange(cur_y, cur_m)[1]
    if as_of_dt <= date(cur_y, cur_m, days_in_cur):
        # Current month is not strictly before as_of_dt
        total_end = cur_y * 12 + (cur_m - 1) - 1
    else:
        total_end = cur_y * 12 + (cur_m - 1)

    months: list[str] = []
    for offset in range(lookback_months - 1, -1, -1):
        tm = total_end - offset
        y, m0 = divmod(tm, 12)
        months.append(f"{y:04d}-{m0 + 1:02d}")
    return months


def _compute_normalized_slope(values: list[float]) -> float:
    """Least-squares slope of monthly minutes divided by their mean (0.0 if < 3 months or mean == 0)."""
    k = len(values)
    if k < 3:
        return 0.0
    mean_y = sum(values) / float(k)
    if mean_y == 0.0:
        return 0.0
    mean_x = (k - 1) / 2.0
    num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(k))
    if den == 0.0:
        return 0.0
    slope = num / den
    return round(slope / mean_y, 6)


def build_features(
    tables: Mapping[str, pd.DataFrame],
    as_of: date | str,
    lookback_months: int = 6,
) -> pd.DataFrame:
    """Build point-in-time `feature_snapshot` rows for customers active on `as_of`.

    Strictly enforces ADR-004 temporal isolation:
    - Subscriptions: reads only rows with `start_date < as_of`. The only use of `end_date`
      is to determine whether the subscription is active on `as_of` (`end_date` is NULL or `>= as_of`).
    - Usage snapshots: reads only rows with `period_end < as_of`.
    - Billing events: reads only rows with `event_date < as_of`.
    - Support cases: reads only rows with `opened_at < as_of`.
    """
    as_of_dt = _to_date(as_of)
    as_of_str = as_of_dt.isoformat()
    window_start_dt = _subtract_months(as_of_dt, lookback_months)
    window_start_str = window_start_dt.isoformat()
    window_end_str = as_of_str

    window_months = _window_month_strings(as_of_dt, lookback_months)
    half = lookback_months // 2
    prev3_set = set(window_months[:half])
    last3_set = set(window_months[half:])
    window_month_set = set(window_months)
    last_month_str = window_months[-1] if window_months else ""

    cust_df = tables["customer"]
    raw_sub_df = tables["subscription"]
    raw_usage_df = tables["usage_snapshot"]
    raw_bill_df = tables["billing_event"]
    raw_sup_df = tables["support_case"]

    # 1. Filter subscriptions strictly to start_date < as_of_str
    #    Only allowed use of end_date is deciding whether subscription is active at as_of.
    if raw_sub_df.empty:
        return pd.DataFrame(columns=FEATURE_SNAPSHOT_COLUMNS)

    sub_prior = raw_sub_df[raw_sub_df["start_date"].astype(str) < as_of_str].copy()
    if sub_prior.empty:
        return pd.DataFrame(columns=FEATURE_SNAPSHOT_COLUMNS)

    end_col = sub_prior["end_date"]
    is_active_mask = end_col.isna() | (end_col.astype(str) == "") | (end_col.astype(str) >= as_of_str)
    sub_prior["is_active_at_as_of"] = is_active_mask
    # Drop end_date and end_reason immediately so no downstream logic can inspect future end dates
    sub_prior = sub_prior.drop(columns=["end_date", "end_reason"], errors="ignore")

    active_subs = sub_prior[sub_prior["is_active_at_as_of"]].sort_values(
        ["customer_id", "sequence_no"], kind="mergesort"
    )
    if active_subs.empty:
        return pd.DataFrame(columns=FEATURE_SNAPSHOT_COLUMNS)

    # Active subscription per customer (latest sequence_no active on as_of)
    active_sub_by_cid: dict[str, tuple[str, int]] = {}
    for row in active_subs.itertuples(index=False):
        active_sub_by_cid[str(row.customer_id)] = (
            str(row.plan_tier),
            int(row.monthly_price_cents),
        )

    active_cids = sorted(active_sub_by_cid.keys())
    active_cid_set = set(active_cids)

    # Map subscription_id -> customer_id and compute plan_downgrade_6m
    sub_to_cid: dict[str, str] = {}
    downgrade_6m_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}

    sub_prior_sorted = sub_prior.sort_values(["customer_id", "sequence_no"], kind="mergesort")
    prev_tier_by_cid: dict[str, str] = {}
    for row in sub_prior_sorted.itertuples(index=False):
        cid = str(row.customer_id)
        sid = str(row.subscription_id)
        tier = str(row.plan_tier)
        s_date = str(row.start_date)
        sub_to_cid[sid] = cid

        if cid in prev_tier_by_cid:
            prev_tier = prev_tier_by_cid[cid]
            if (
                window_start_str <= s_date < as_of_str
                and TIER_RANK.get(tier, 0) < TIER_RANK.get(prev_tier, 0)
            ):
                if cid in downgrade_6m_by_cid:
                    downgrade_6m_by_cid[cid] = 1
        prev_tier_by_cid[cid] = tier

    # 2. Filter usage_snapshot strictly to period_end < as_of_str
    usage_by_cid_month: dict[str, dict[str, tuple[float, int, int]]] = {
        cid: {} for cid in active_cids
    }
    if not raw_usage_df.empty:
        u_prior = raw_usage_df[raw_usage_df["period_end"].astype(str) < as_of_str]
        for row in u_prior.itertuples(index=False):
            sid = str(row.subscription_id)
            cid = sub_to_cid.get(sid)
            if cid is None or cid not in active_cid_set:
                continue
            s_month = str(row.snapshot_month)
            if s_month not in window_month_set:
                continue
            mins = float(row.usage_minutes)
            days = int(row.active_days)
            sess = int(row.sessions)
            prev_m, prev_d, prev_s = usage_by_cid_month[cid].get(s_month, (0.0, 0, 0))
            usage_by_cid_month[cid][s_month] = (prev_m + mins, prev_d + days, prev_s + sess)

    # 3. Filter billing_event strictly to event_date < as_of_str
    failed_6m_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}
    last_fail_date_by_cid: dict[str, str] = {}
    invoiced_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}
    settled_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}

    if not raw_bill_df.empty:
        b_prior = raw_bill_df[raw_bill_df["event_date"].astype(str) < as_of_str]
        for row in b_prior.itertuples(index=False):
            sid = str(row.subscription_id)
            cid = sub_to_cid.get(sid)
            if cid is None or cid not in active_cid_set:
                continue
            ev_type = str(row.event_type)
            ev_date = str(row.event_date)
            status = str(row.status)
            amt = int(row.amount_cents)

            if ev_type == "INVOICE":
                invoiced_by_cid[cid] += amt
            elif status == "SETTLED" and ev_type in ("PAYMENT", "RETRY"):
                settled_by_cid[cid] += amt
            elif ev_type == "PAYMENT_FAILED":
                if window_start_str <= ev_date < as_of_str:
                    failed_6m_by_cid[cid] += 1
                prev_dt = last_fail_date_by_cid.get(cid)
                if prev_dt is None or ev_date > prev_dt:
                    last_fail_date_by_cid[cid] = ev_date

    # 4. Filter support_case strictly to opened_at < as_of_str
    #    Note: opened_at is ISO timestamp YYYY-MM-DDTHH:MM:SS; opened_at[:10] < as_of_str
    #    is strictly before as_of_date (midnight 00:00:00 of as_of_date).
    cases_6m_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}
    high_sev_6m_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}
    cancel_inq_6m_by_cid: dict[str, int] = {cid: 0 for cid in active_cids}

    if not raw_sup_df.empty:
        # Drop resolved_at immediately so post-as_of resolution dates are never read
        sup_cols = [c for c in raw_sup_df.columns if c != "resolved_at"]
        s_prior = raw_sup_df[sup_cols]
        s_prior = s_prior[s_prior["opened_at"].astype(str).str.slice(0, 10) < as_of_str]
        for row in s_prior.itertuples(index=False):
            cid = str(row.customer_id)
            if cid not in active_cid_set:
                continue
            open_dt_str = str(row.opened_at)[:10]
            if window_start_str <= open_dt_str < as_of_str:
                cases_6m_by_cid[cid] += 1
                if str(row.severity) in ("HIGH", "CRITICAL"):
                    high_sev_6m_by_cid[cid] += 1
                if str(row.category) == "CANCELLATION_INQUIRY":
                    cancel_inq_6m_by_cid[cid] += 1

    # 5. Customer attributes
    cust_info_by_cid: dict[str, tuple[date, str, str, int]] = {}
    for row in cust_df.itertuples(index=False):
        cid = str(row.customer_id)
        if cid in active_cid_set:
            s_dt = _to_date(str(row.signup_date))
            seg = str(row.segment)
            chan = str(row.channel)
            is_seas = 1 if str(row.usage_pattern) == "SEASONAL" else 0
            cust_info_by_cid[cid] = (s_dt, seg, chan, is_seas)

    # 6. Assemble feature_snapshot rows
    rows: list[dict[str, Any]] = []
    for cid in active_cids:
        if cid not in cust_info_by_cid:
            continue
        signup_dt, segment, channel, is_seasonal = cust_info_by_cid[cid]
        plan_tier, monthly_price_cents = active_sub_by_cid[cid]
        tenure_days = (as_of_dt - signup_dt).days

        c_usage = usage_by_cid_month[cid]
        # Months before a customer's first snapshot are excluded, not zero-filled
        observed_months = [m for m in window_months if m in c_usage]
        if observed_months:
            first_m = observed_months[0]
            active_window_months = [m for m in window_months if m >= first_m]
            monthly_mins_series = [
                round(c_usage.get(m, (0.0, 0, 0))[0], 6) for m in active_window_months
            ]
        else:
            active_window_months = []
            monthly_mins_series = []

        mins_3m = round(
            sum(c_usage[m][0] for m in last3_set if m in c_usage), 6
        )
        mins_prev3m = round(
            sum(c_usage[m][0] for m in prev3_set if m in c_usage), 6
        )

        if len(active_window_months) < lookback_months or mins_prev3m == 0.0:
            usage_ratio = 1.0
        else:
            usage_ratio = round(mins_3m / mins_prev3m, 6)

        last_active_days = int(c_usage[last_month_str][1]) if last_month_str in c_usage else 0
        if last_active_days > 0 and last_month_str:
            y_last, m_last = int(last_month_str[:4]), int(last_month_str[5:7])
            max_m_days = calendar.monthrange(y_last, m_last)[1]
            last_active_days = min(max_m_days, last_active_days)

        usage_slope = _compute_normalized_slope(monthly_mins_series)
        sessions_6m = int(sum(v[2] for v in c_usage.values()))

        failed_6m = failed_6m_by_cid[cid]
        if cid in last_fail_date_by_cid:
            days_since_fail: int | None = (
                as_of_dt - date.fromisoformat(last_fail_date_by_cid[cid])
            ).days
        else:
            days_since_fail = None

        balance_cents = int(invoiced_by_cid[cid] - settled_by_cid[cid])

        rows.append(
            {
                "customer_id": cid,
                "as_of_date": as_of_str,
                "window_start": window_start_str,
                "window_end": window_end_str,
                "usage_minutes_3m": mins_3m,
                "usage_minutes_prev3m": mins_prev3m,
                "usage_ratio_3m_vs_prev3m": usage_ratio,
                "last_month_active_days": last_active_days,
                "usage_slope_6m": usage_slope,
                "sessions_6m": sessions_6m,
                "failed_payments_6m": failed_6m,
                "days_since_last_failed_payment": days_since_fail,
                "outstanding_balance_cents": balance_cents,
                "support_cases_6m": cases_6m_by_cid[cid],
                "high_severity_cases_6m": high_sev_6m_by_cid[cid],
                "cancellation_inquiries_6m": cancel_inq_6m_by_cid[cid],
                "tenure_days": tenure_days,
                "plan_tier": plan_tier,
                "monthly_price_cents": monthly_price_cents,
                "plan_downgrade_6m": downgrade_6m_by_cid[cid],
                "segment": segment,
                "channel": channel,
                "is_seasonal": is_seasonal,
            }
        )

    df = pd.DataFrame(rows, columns=FEATURE_SNAPSHOT_COLUMNS)
    return df.sort_values(["customer_id", "as_of_date"], kind="mergesort").reset_index(
        drop=True
    )

