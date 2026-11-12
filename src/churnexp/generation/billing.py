"""Billing event generation (invoices, payments, failures, and retries) for churnexp."""

from dataclasses import dataclass
from datetime import date, timedelta
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.generation.customers import CustomerRecord
from churnexp.generation.subscriptions import SubscriptionRecord
from churnexp.rng import RngFactory


@dataclass(frozen=True)
class BillingEventRecord:
    billing_event_id: str
    subscription_id: str
    related_event_id: str | None
    event_type: str
    event_date: str
    due_date: str | None
    amount_cents: int
    status: str
    failure_reason: str | None


def _find_active_subscription_on_date(
    subs: list[SubscriptionRecord], target_date: date
) -> SubscriptionRecord | None:
    for sub in subs:
        if sub.start_date <= target_date and (
            sub.end_date is None or target_date <= sub.end_date
        ):
            return sub
    return None


def generate_customer_billing(
    customer: CustomerRecord,
    subs: list[SubscriptionRecord],
    months: list[tuple[int, int]],
    churn_date: date | None,
    churn_type: str | None,
    cfg: Config,
    rng_factory: RngFactory,
) -> list[BillingEventRecord]:
    """Generate billing events for a customer across the given months."""
    b_cfg = cfg.generator.billing
    reasons = list(b_cfg.failure_reasons)
    n_reasons = len(reasons)

    max_allowed_date = (
        min(churn_date, cfg.timeline.data_end)
        if churn_date is not None
        else cfg.timeline.data_end
    )
    inv_churn_invoice_date = (
        churn_date - timedelta(days=cfg.generator.churn.involuntary_cancel_offset_days)
        if (churn_date is not None and churn_type == "INVOLUNTARY")
        else None
    )

    records: list[BillingEventRecord] = []
    for year, month in months:
        bill_date = date(year, month, customer.billing_day)
        if bill_date < customer.signup_date or bill_date < cfg.timeline.data_start:
            continue
        if bill_date > max_allowed_date:
            continue

        sub = _find_active_subscription_on_date(subs, bill_date)
        if sub is None:
            continue

        rng_b = rng_factory.entity_stream(
            f"billing:{year:04d}{month:02d}", customer.index
        )
        inv_id = ids.billing_event_id(sub.subscription_id, year, month, 1)
        due_dt = bill_date + timedelta(days=b_cfg.due_days_offset)
        price = sub.monthly_price_cents

        # 1. INVOICE
        records.append(
            BillingEventRecord(
                billing_event_id=inv_id,
                subscription_id=sub.subscription_id,
                related_event_id=None,
                event_type="INVOICE",
                event_date=bill_date.isoformat(),
                due_date=due_dt.isoformat(),
                amount_cents=price,
                status="POSTED",
                failure_reason=None,
            )
        )

        is_inv_churn_month = (
            inv_churn_invoice_date is not None and bill_date == inv_churn_invoice_date
        )

        if is_inv_churn_month:
            # Involuntary churn month: PAYMENT_FAILED at +1d, failed RETRY at +4d, invoice stays unsettled
            fail_dt = bill_date + timedelta(days=b_cfg.failed_event_offset_days)
            retry_dt = bill_date + timedelta(days=b_cfg.involuntary_retry_offset_days)
            reason1 = reasons[int(rng_b.integers(0, n_reasons))]
            reason2 = reasons[int(rng_b.integers(0, n_reasons))]

            records.append(
                BillingEventRecord(
                    billing_event_id=ids.billing_event_id(
                        sub.subscription_id, year, month, 2
                    ),
                    subscription_id=sub.subscription_id,
                    related_event_id=inv_id,
                    event_type="PAYMENT_FAILED",
                    event_date=fail_dt.isoformat(),
                    due_date=None,
                    amount_cents=price,
                    status="FAILED",
                    failure_reason=reason1,
                )
            )
            records.append(
                BillingEventRecord(
                    billing_event_id=ids.billing_event_id(
                        sub.subscription_id, year, month, 3
                    ),
                    subscription_id=sub.subscription_id,
                    related_event_id=inv_id,
                    event_type="RETRY",
                    event_date=retry_dt.isoformat(),
                    due_date=None,
                    amount_cents=price,
                    status="FAILED",
                    failure_reason=reason2,
                )
            )
            continue

        # Check if previous month of involuntary churn invoice
        is_prev_inv_month = (
            inv_churn_invoice_date is not None
            and (
                (inv_churn_invoice_date.year - year) * 12
                + (inv_churn_invoice_date.month - month)
                == 1
            )
        )
        if is_prev_inv_month:
            p_fail = b_cfg.involuntary_prev_month_fail_prob
        else:
            p_fail = (
                b_cfg.failure_prob_smb
                if customer.segment == "SMB"
                else b_cfg.failure_prob_consumer
            )

        u_fail = float(rng_b.random())
        rem_days = (max_allowed_date - bill_date).days

        if u_fail < p_fail and rem_days >= b_cfg.retry_min_delay_days:
            fail_dt = bill_date + timedelta(days=b_cfg.failed_event_offset_days)
            reason = reasons[int(rng_b.integers(0, n_reasons))]
            max_retry = min(b_cfg.retry_max_delay_days, rem_days)
            if is_prev_inv_month:
                max_retry = min(max_retry, 25)
            max_retry = max(b_cfg.retry_min_delay_days, max_retry)
            retry_offset = int(
                rng_b.integers(b_cfg.retry_min_delay_days, max_retry + 1)
            )
            retry_dt = bill_date + timedelta(days=retry_offset)

            records.append(
                BillingEventRecord(
                    billing_event_id=ids.billing_event_id(
                        sub.subscription_id, year, month, 2
                    ),
                    subscription_id=sub.subscription_id,
                    related_event_id=inv_id,
                    event_type="PAYMENT_FAILED",
                    event_date=fail_dt.isoformat(),
                    due_date=None,
                    amount_cents=price,
                    status="FAILED",
                    failure_reason=reason,
                )
            )
            records.append(
                BillingEventRecord(
                    billing_event_id=ids.billing_event_id(
                        sub.subscription_id, year, month, 3
                    ),
                    subscription_id=sub.subscription_id,
                    related_event_id=inv_id,
                    event_type="RETRY",
                    event_date=retry_dt.isoformat(),
                    due_date=None,
                    amount_cents=price,
                    status="SETTLED",
                    failure_reason=None,
                )
            )
        else:
            max_pay = max(0, min(b_cfg.payment_max_delay_days, rem_days))
            pay_offset = int(rng_b.integers(0, max_pay + 1))
            pay_dt = bill_date + timedelta(days=pay_offset)
            records.append(
                BillingEventRecord(
                    billing_event_id=ids.billing_event_id(
                        sub.subscription_id, year, month, 2
                    ),
                    subscription_id=sub.subscription_id,
                    related_event_id=inv_id,
                    event_type="PAYMENT",
                    event_date=pay_dt.isoformat(),
                    due_date=None,
                    amount_cents=price,
                    status="SETTLED",
                    failure_reason=None,
                )
            )

    return records


def billing_to_dataframe(records: list[BillingEventRecord]) -> pd.DataFrame:
    """Convert billing event records to DataFrame sorted by billing_event_id."""
    rows = [
        {
            "billing_event_id": r.billing_event_id,
            "subscription_id": r.subscription_id,
            "related_event_id": r.related_event_id,
            "event_type": r.event_type,
            "event_date": r.event_date,
            "due_date": r.due_date,
            "amount_cents": r.amount_cents,
            "status": r.status,
            "failure_reason": r.failure_reason,
        }
        for r in records
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "billing_event_id",
            "subscription_id",
            "related_event_id",
            "event_type",
            "event_date",
            "due_date",
            "amount_cents",
            "status",
            "failure_reason",
        ],
    )
    return df.sort_values("billing_event_id", kind="mergesort").reset_index(drop=True)

