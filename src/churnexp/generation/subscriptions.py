"""Subscription chain and candidate plan-change generation for churnexp."""

from dataclasses import dataclass
from datetime import date, timedelta
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.generation.customers import CustomerRecord, _draw_categorical
from churnexp.rng import RngFactory

TIER_RANK: dict[str, int] = {"BASIC": 0, "STANDARD": 1, "PREMIUM": 2}


@dataclass(frozen=True)
class CandidatePlanChange:
    month_idx: int
    year: int
    month: int
    effective_date: date
    old_tier: str
    new_tier: str
    is_downgrade: bool


@dataclass(frozen=True)
class PreSimulatedSubscription:
    customer_index: int
    initial_tier: str
    changes: list[CandidatePlanChange]
    tier_by_month: list[str]
    recent_downgrade_by_month: list[bool]


@dataclass(frozen=True)
class SubscriptionRecord:
    subscription_id: str
    customer_id: str
    previous_subscription_id: str | None
    sequence_no: int
    plan_tier: str
    monthly_price_cents: int
    gross_margin_pct: float
    start_date: date
    end_date: date | None
    end_reason: str | None
    upgrades_count: int = 0
    downgrades_count: int = 0


def get_simulation_months(cfg: Config) -> list[tuple[int, int]]:
    """Return all (year, month) pairs from timeline.data_start to timeline.data_end inclusive."""
    months: list[tuple[int, int]] = []
    y, m = cfg.timeline.data_start.year, cfg.timeline.data_start.month
    end_y, end_m = cfg.timeline.data_end.year, cfg.timeline.data_end.month
    while (y, m) <= (end_y, end_m):
        months.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return months


def pre_simulate_plan_changes(
    customers: list[CustomerRecord],
    months: list[tuple[int, int]],
    cfg: Config,
    rng_factory: RngFactory,
) -> list[PreSimulatedSubscription]:
    """Simulate initial tier and candidate plan changes from 2025-01 on (independent of churn)."""
    s_cfg = cfg.generator.subscriptions
    rec_down_window = cfg.generator.churn.recent_downgrade_months

    cons_items = [
        ("BASIC", float(s_cfg.consumer_tier_probs["BASIC"])),
        ("STANDARD", float(s_cfg.consumer_tier_probs["STANDARD"])),
        ("PREMIUM", float(s_cfg.consumer_tier_probs["PREMIUM"])),
    ]
    smb_items = [
        ("BASIC", float(s_cfg.smb_tier_probs["BASIC"])),
        ("STANDARD", float(s_cfg.smb_tier_probs["STANDARD"])),
        ("PREMIUM", float(s_cfg.smb_tier_probs["PREMIUM"])),
    ]

    results: list[PreSimulatedSubscription] = []
    for c in customers:
        rng_init = rng_factory.entity_stream("subscription_init", c.index)
        tier_items = cons_items if c.segment == "CONSUMER" else smb_items
        current_tier = _draw_categorical(float(rng_init.random()), tier_items)
        initial_tier = current_tier

        changes: list[CandidatePlanChange] = []
        tier_by_month: list[str] = []
        downgrade_months: list[int] = []
        recent_downgrade_by_month: list[bool] = []

        for m_idx, (year, month) in enumerate(months):
            rng_m = rng_factory.entity_stream(f"plan_change:{year:04d}{month:02d}", c.index)
            u_change = float(rng_m.random())
            u_dir = float(rng_m.random())

            bill_date = date(year, month, c.billing_day)
            if bill_date > c.signup_date and u_change < s_cfg.monthly_plan_change_prob:
                if current_tier == "BASIC":
                    new_tier = "STANDARD"
                elif current_tier == "PREMIUM":
                    new_tier = "STANDARD"
                else:
                    new_tier = "PREMIUM" if u_dir < s_cfg.upgrade_prob else "BASIC"

                is_down = TIER_RANK[new_tier] < TIER_RANK[current_tier]
                changes.append(
                    CandidatePlanChange(
                        month_idx=m_idx,
                        year=year,
                        month=month,
                        effective_date=bill_date,
                        old_tier=current_tier,
                        new_tier=new_tier,
                        is_downgrade=is_down,
                    )
                )
                if is_down:
                    downgrade_months.append(m_idx)
                current_tier = new_tier

            tier_by_month.append(current_tier)
            has_recent_down = any(
                0 <= (m_idx - dm) < rec_down_window for dm in downgrade_months
            )
            recent_downgrade_by_month.append(has_recent_down)

        results.append(
            PreSimulatedSubscription(
                customer_index=c.index,
                initial_tier=initial_tier,
                changes=changes,
                tier_by_month=tier_by_month,
                recent_downgrade_by_month=recent_downgrade_by_month,
            )
        )

    return results


def build_customer_subscriptions(
    customer: CustomerRecord,
    pre_sub: PreSimulatedSubscription,
    churn_date: date | None,
    churn_type: str | None,
    cfg: Config,
) -> list[SubscriptionRecord]:
    """Build final subscription chain for a customer, discarding plan changes on/after churn."""
    s_cfg = cfg.generator.subscriptions
    prices = s_cfg.tier_price_cents
    margins = s_cfg.tier_gross_margin_pct

    valid_changes: list[CandidatePlanChange] = []
    inv_invoice_date = (
        churn_date - timedelta(days=cfg.generator.churn.involuntary_cancel_offset_days)
        if (churn_date is not None and churn_type == "INVOLUNTARY")
        else None
    )
    for ch in pre_sub.changes:
        if churn_date is not None:
            if ch.effective_date >= churn_date:
                continue
            if inv_invoice_date is not None and ch.effective_date >= inv_invoice_date:
                continue
        valid_changes.append(ch)

    subs: list[SubscriptionRecord] = []
    seq = 1
    curr_tier = pre_sub.initial_tier
    curr_start = customer.signup_date
    prev_sub_id: str | None = None
    upgrades = 0
    downgrades = 0

    for ch in valid_changes:
        sub_id = ids.subscription_id(customer.customer_id, seq)
        end_dt = ch.effective_date - timedelta(days=1)
        subs.append(
            SubscriptionRecord(
                subscription_id=sub_id,
                customer_id=customer.customer_id,
                previous_subscription_id=prev_sub_id,
                sequence_no=seq,
                plan_tier=curr_tier,
                monthly_price_cents=int(prices[curr_tier]),
                gross_margin_pct=float(margins[curr_tier]),
                start_date=curr_start,
                end_date=end_dt,
                end_reason="PLAN_CHANGE",
                upgrades_count=upgrades,
                downgrades_count=downgrades,
            )
        )
        prev_sub_id = sub_id
        seq += 1
        curr_tier = ch.new_tier
        curr_start = ch.effective_date
        if ch.is_downgrade:
            downgrades += 1
        else:
            upgrades += 1

    # Final subscription in chain
    final_sub_id = ids.subscription_id(customer.customer_id, seq)
    if churn_date is not None:
        final_end = churn_date
        final_reason = (
            "INVOLUNTARY_CANCEL" if churn_type == "INVOLUNTARY" else "VOLUNTARY_CANCEL"
        )
    else:
        final_end = None
        final_reason = None

    subs.append(
        SubscriptionRecord(
            subscription_id=final_sub_id,
            customer_id=customer.customer_id,
            previous_subscription_id=prev_sub_id,
            sequence_no=seq,
            plan_tier=curr_tier,
            monthly_price_cents=int(prices[curr_tier]),
            gross_margin_pct=float(margins[curr_tier]),
            start_date=curr_start,
            end_date=final_end,
            end_reason=final_reason,
            upgrades_count=upgrades,
            downgrades_count=downgrades,
        )
    )
    return subs


def subscriptions_to_dataframe(subs: list[SubscriptionRecord]) -> pd.DataFrame:
    """Convert subscription records to the canonical subscription table DataFrame."""
    rows = [
        {
            "subscription_id": s.subscription_id,
            "customer_id": s.customer_id,
            "previous_subscription_id": s.previous_subscription_id,
            "sequence_no": s.sequence_no,
            "plan_tier": s.plan_tier,
            "monthly_price_cents": s.monthly_price_cents,
            "gross_margin_pct": s.gross_margin_pct,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat() if s.end_date is not None else None,
            "end_reason": s.end_reason,
        }
        for s in subs
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "subscription_id",
            "customer_id",
            "previous_subscription_id",
            "sequence_no",
            "plan_tier",
            "monthly_price_cents",
            "gross_margin_pct",
            "start_date",
            "end_date",
            "end_reason",
        ],
    )
    return df.sort_values("subscription_id", kind="mergesort").reset_index(drop=True)

