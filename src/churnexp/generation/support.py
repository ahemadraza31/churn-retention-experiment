"""Support case generation for churnexp."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.generation.customers import CustomerRecord, _draw_categorical
from churnexp.generation.subscriptions import SubscriptionRecord
from churnexp.rng import RngFactory


@dataclass(frozen=True)
class SupportCaseRecord:
    case_id: str
    customer_id: str
    subscription_id: str
    opened_at: str
    resolved_at: str | None
    category: str
    severity: str
    escalated: int


def generate_customer_support(
    customer: CustomerRecord,
    subs: list[SubscriptionRecord],
    months: list[tuple[int, int]],
    churn_date: date | None,
    churn_type: str | None,
    is_loud: bool,
    cfg: Config,
    rng_factory: RngFactory,
    starting_case_seq: int = 1,
) -> list[SupportCaseRecord]:
    """Generate support cases for a customer across the given months, ordered by opened_at."""
    sup_cfg = cfg.generator.support
    cat_items = [
        ("TECHNICAL", float(sup_cfg.category_probs["TECHNICAL"])),
        ("BILLING", float(sup_cfg.category_probs["BILLING"])),
        ("GENERAL", float(sup_cfg.category_probs["GENERAL"])),
    ]
    base_sev_items = [
        ("LOW", float(sup_cfg.severity_probs["LOW"])),
        ("MEDIUM", float(sup_cfg.severity_probs["MEDIUM"])),
        ("HIGH", float(sup_cfg.severity_probs["HIGH"])),
    ]
    loud_high = float(sup_cfg.loud_high_severity_prob)
    rem_sev = max(0.0, 1.0 - loud_high)
    loud_sev_items = [
        ("LOW", round(rem_sev * (2.0 / 3.0), 6)),
        ("MEDIUM", round(rem_sev * (1.0 / 3.0), 6)),
        ("HIGH", loud_high),
    ]

    raw_cases: list[tuple[str, str, str | None, str, str, int]] = []

    for year, month in months:
        days_in_month = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)

        months_to_churn = (
            (churn_date.year - year) * 12 + (churn_date.month - month)
            if churn_date is not None
            else 999
        )

        for sub in subs:
            eff_start = max(sub.start_date, month_start)
            eff_end = (
                min(sub.end_date, month_end) if sub.end_date is not None else month_end
            )
            if churn_date is not None:
                eff_end = min(eff_end, churn_date)
            if eff_start > eff_end:
                continue

            span_days = (eff_end - eff_start).days + 1
            frac_active = span_days / float(days_in_month)

            rng_s = rng_factory.entity_stream(
                f"support:{year:04d}{month:02d}:s{sub.sequence_no}", customer.index
            )

            is_loud_window = (
                churn_date is not None
                and churn_type == "VOLUNTARY"
                and is_loud
                and 0 <= months_to_churn <= sup_cfg.loud_churn_window_months
            )

            base_rate = (
                sup_cfg.poisson_rate_smb
                if customer.segment == "SMB"
                else sup_cfg.poisson_rate_consumer
            ) * frac_active
            lam = (
                base_rate * sup_cfg.loud_churn_rate_multiplier
                if is_loud_window
                else base_rate
            )

            count = int(rng_s.poisson(lam))
            sev_items = loud_sev_items if is_loud_window else base_sev_items

            pending_categories_and_sev: list[tuple[str, str]] = []
            for _ in range(count):
                cat = _draw_categorical(float(rng_s.random()), cat_items)
                sev = _draw_categorical(float(rng_s.random()), sev_items)
                pending_categories_and_sev.append((cat, sev))

            # Cancellation inquiry cases (loud voluntary churners vs baseline decoy)
            if (
                churn_date is not None
                and churn_type == "VOLUNTARY"
                and is_loud
                and 1 <= months_to_churn <= sup_cfg.loud_cancellation_window_months
            ):
                if float(rng_s.random()) < sup_cfg.loud_cancellation_inquiry_prob:
                    sev = _draw_categorical(float(rng_s.random()), loud_sev_items)
                    pending_categories_and_sev.append(("CANCELLATION_INQUIRY", sev))
            else:
                if (
                    float(rng_s.random())
                    < sup_cfg.decoy_cancellation_inquiry_prob * frac_active
                ):
                    sev = _draw_categorical(float(rng_s.random()), base_sev_items)
                    pending_categories_and_sev.append(("CANCELLATION_INQUIRY", sev))

            # Involuntary churner billing cases in the 2 months before churn
            if (
                churn_date is not None
                and churn_type == "INVOLUNTARY"
                and 1 <= months_to_churn <= sup_cfg.involuntary_billing_window_months
            ):
                if float(rng_s.random()) < sup_cfg.involuntary_billing_case_prob:
                    sev = _draw_categorical(float(rng_s.random()), base_sev_items)
                    pending_categories_and_sev.append(("BILLING", sev))

            for cat, sev in pending_categories_and_sev:
                day_offset = int(rng_s.integers(0, span_days))
                open_dt = eff_start + timedelta(days=day_offset)
                hh = int(rng_s.integers(0, 24))
                mm = int(rng_s.integers(0, 60))
                ss = int(rng_s.integers(0, 60))
                opened_at = f"{open_dt.isoformat()}T{hh:02d}:{mm:02d}:{ss:02d}"

                escalated = 1 if float(rng_s.random()) < sup_cfg.escalation_prob else 0
                raw_res = int(round(float(rng_s.lognormal(1.2, 0.6))))
                res_days = max(
                    sup_cfg.resolution_min_days,
                    min(sup_cfg.resolution_max_days, raw_res),
                )
                if escalated == 1:
                    res_days += sup_cfg.escalation_extra_days

                resolve_dt = open_dt + timedelta(days=res_days)
                if churn_date is not None and resolve_dt > churn_date:
                    resolve_dt = churn_date

                if resolve_dt > cfg.timeline.data_end:
                    resolved_at = None
                else:
                    resolved_at = f"{resolve_dt.isoformat()}T{hh:02d}:{mm:02d}:{ss:02d}"

                raw_cases.append(
                    (sub.subscription_id, opened_at, resolved_at, cat, sev, escalated)
                )

    raw_cases.sort(key=lambda x: (x[1], x[0], x[3], x[4]))
    records: list[SupportCaseRecord] = []
    for idx, (sub_id, opened_at, resolved_at, cat, sev, esc) in enumerate(
        raw_cases, start=starting_case_seq
    ):
        records.append(
            SupportCaseRecord(
                case_id=ids.support_case_id(customer.customer_id, idx),
                customer_id=customer.customer_id,
                subscription_id=sub_id,
                opened_at=opened_at,
                resolved_at=resolved_at,
                category=cat,
                severity=sev,
                escalated=esc,
            )
        )
    return records


def support_to_dataframe(records: list[SupportCaseRecord]) -> pd.DataFrame:
    """Convert support case records to DataFrame sorted by case_id."""
    rows = [
        {
            "case_id": r.case_id,
            "customer_id": r.customer_id,
            "subscription_id": r.subscription_id,
            "opened_at": r.opened_at,
            "resolved_at": r.resolved_at,
            "category": r.category,
            "severity": r.severity,
            "escalated": r.escalated,
        }
        for r in records
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "case_id",
            "customer_id",
            "subscription_id",
            "opened_at",
            "resolved_at",
            "category",
            "severity",
            "escalated",
        ],
    )
    return df.sort_values("case_id", kind="mergesort").reset_index(drop=True)

