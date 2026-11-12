"""Monthly usage snapshot generation for churnexp."""

import calendar
from dataclasses import dataclass
from datetime import date
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.generation.customers import CustomerRecord
from churnexp.generation.subscriptions import SubscriptionRecord
from churnexp.rng import RngFactory


@dataclass(frozen=True)
class UsageSnapshotRecord:
    snapshot_id: str
    subscription_id: str
    snapshot_month: str
    period_end: str
    active_days: int
    sessions: int
    usage_minutes: float
    features_used: int
    usage_pct_of_limit: float


def generate_customer_usage(
    customer: CustomerRecord,
    subs: list[SubscriptionRecord],
    months: list[tuple[int, int]],
    churn_date: date | None,
    churn_type: str | None,
    is_loud: bool,
    cfg: Config,
    rng_factory: RngFactory,
) -> list[UsageSnapshotRecord]:
    """Generate monthly usage snapshots for a customer across the given months."""
    u_cfg = cfg.generator.usage
    rng_prof = rng_factory.entity_stream("usage_profile", customer.index)
    cust_lognormal = float(rng_prof.lognormal(0.0, u_cfg.customer_lognormal_sigma))
    seasonal_start = int(rng_prof.integers(1, 13))
    off_months = {
        (seasonal_start - 1 + k) % 12 + 1
        for k in range(u_cfg.seasonal_off_months_count)
    }
    has_decoy_dip = float(rng_prof.random()) < u_cfg.decoy_dip_prob
    decoy_start_idx = int(
        rng_prof.integers(0, max(1, 18 - u_cfg.decoy_dip_months + 1))
    )

    seg_mult = u_cfg.smb_multiplier if customer.segment == "SMB" else 1.0
    data_start_year = cfg.timeline.data_start.year
    data_start_month = cfg.timeline.data_start.month

    records: list[UsageSnapshotRecord] = []
    for year, month in months:
        m_idx = (year - data_start_year) * 12 + (month - data_start_month)
        days_in_month = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)
        snap_month_str = f"{year:04d}-{month:02d}"
        period_end_str = month_end.isoformat()

        for sub in subs:
            eff_start = max(sub.start_date, month_start)
            eff_end = min(sub.end_date, month_end) if sub.end_date is not None else month_end
            if churn_date is not None:
                eff_end = min(eff_end, churn_date)
            if eff_start > eff_end:
                continue

            span_days = (eff_end - eff_start).days + 1
            frac_active = span_days / float(days_in_month)

            rng_m = rng_factory.entity_stream(
                f"usage:{year:04d}{month:02d}:s{sub.sequence_no}", customer.index
            )
            monthly_noise = float(rng_m.lognormal(0.0, u_cfg.monthly_noise_sigma))
            feat_noise = float(rng_m.normal(0.0, 0.5))

            base_min = float(u_cfg.base_minutes[sub.plan_tier])
            customer_expected_minutes = base_min * seg_mult * cust_lognormal

            seasonal_mult = (
                u_cfg.seasonal_off_multiplier
                if (customer.usage_pattern == "SEASONAL" and month in off_months)
                else 1.0
            )

            churn_decay_mult = 1.0
            if churn_date is not None and churn_type == "VOLUNTARY" and is_loud:
                months_to_churn = (churn_date.year - year) * 12 + (
                    churn_date.month - month
                )
                if months_to_churn in u_cfg.loud_decay_multipliers:
                    churn_decay_mult = float(
                        u_cfg.loud_decay_multipliers[months_to_churn]
                    )

            decoy_mult = 1.0
            if (
                churn_date is None
                and has_decoy_dip
                and decoy_start_idx <= m_idx < decoy_start_idx + u_cfg.decoy_dip_months
            ):
                decoy_mult = u_cfg.decoy_dip_multiplier

            plan_change_mult = (
                u_cfg.upgrade_usage_multiplier ** sub.upgrades_count
            ) * (u_cfg.downgrade_usage_multiplier ** sub.downgrades_count)

            raw_minutes = (
                customer_expected_minutes
                * monthly_noise
                * seasonal_mult
                * churn_decay_mult
                * decoy_mult
                * plan_change_mult
                * frac_active
            )
            minutes = round(max(0.0, raw_minutes), 2)
            limit = float(u_cfg.plan_limit_minutes[sub.plan_tier])
            pct_of_limit = round(min(1.0, minutes / limit), 4)

            if minutes == 0.0:
                active_days = 0
            else:
                raw_days = int(round(20.0 * minutes / customer_expected_minutes))
                active_days = max(1, min(days_in_month, raw_days))

            sessions = max(active_days, int(round((minutes / 22.0) * monthly_noise)))
            features_used = max(
                1, min(8, int(round(1.0 + 6.0 * pct_of_limit + feat_noise)))
            )

            records.append(
                UsageSnapshotRecord(
                    snapshot_id=ids.snapshot_id(sub.subscription_id, year, month),
                    subscription_id=sub.subscription_id,
                    snapshot_month=snap_month_str,
                    period_end=period_end_str,
                    active_days=active_days,
                    sessions=sessions,
                    usage_minutes=minutes,
                    features_used=features_used,
                    usage_pct_of_limit=pct_of_limit,
                )
            )

    return records


def usage_to_dataframe(records: list[UsageSnapshotRecord]) -> pd.DataFrame:
    """Convert usage snapshot records to DataFrame sorted by snapshot_id."""
    rows = [
        {
            "snapshot_id": r.snapshot_id,
            "subscription_id": r.subscription_id,
            "snapshot_month": r.snapshot_month,
            "period_end": r.period_end,
            "active_days": r.active_days,
            "sessions": r.sessions,
            "usage_minutes": r.usage_minutes,
            "features_used": r.features_used,
            "usage_pct_of_limit": r.usage_pct_of_limit,
        }
        for r in records
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "snapshot_id",
            "subscription_id",
            "snapshot_month",
            "period_end",
            "active_days",
            "sessions",
            "usage_minutes",
            "features_used",
            "usage_pct_of_limit",
        ],
    )
    return df.sort_values("snapshot_id", kind="mergesort").reset_index(drop=True)

