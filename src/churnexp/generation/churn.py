"""Untreated churn calibration, simulation, 2025 churn outcomes, and latent ground truth."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
import math
import numpy as np
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.generation.customers import CustomerRecord
from churnexp.generation.subscriptions import PreSimulatedSubscription
from churnexp.rng import RngFactory


@dataclass(frozen=True)
class CustomerChurnResult:
    customer_id: str
    churned: bool
    churn_month_idx: int | None
    churn_date: date | None
    churn_type: str | None
    is_loud: bool
    frailty_z: float


def simulate_untreated_churn(
    customers: list[CustomerRecord],
    pre_subs: list[PreSimulatedSubscription],
    months: list[tuple[int, int]],
    cfg: Config,
    rng_factory: RngFactory,
) -> tuple[list[CustomerChurnResult], float]:
    """Calibrate base hazard via deterministic bisection and simulate untreated churn."""
    n = len(customers)
    n_months = len(months)
    ch_cfg = cfg.generator.churn
    u_cfg = cfg.generator.usage

    tier_mult_map = ch_cfg.tier_hazard_mult
    chan_mult_map = ch_cfg.channel_hazard_mult
    short_tenure_days = ch_cfg.short_tenure_months * 30
    short_mult = ch_cfg.short_tenure_mult
    down_mult = ch_cfg.recent_downgrade_mult
    sigma = ch_cfg.frailty_sigma
    cap = ch_cfg.monthly_hazard_cap

    month_starts = [date(y, m, 1) for y, m in months]
    month_ends = [date(y, m, calendar.monthrange(y, m)[1]) for y, m in months]

    factors = np.zeros((n, n_months), dtype=np.float64)
    u_draws = np.ones((n, n_months), dtype=np.float64)
    frailties = np.zeros(n, dtype=np.float64)

    for idx, (c, psub) in enumerate(zip(customers, pre_subs)):
        rng_f = rng_factory.entity_stream("churn_frailty", c.index)
        z = float(rng_f.standard_normal())
        frailties[idx] = z
        f_mult = math.exp(sigma * z)
        c_mult = float(chan_mult_map[c.channel])

        for m_idx, (y, m) in enumerate(months):
            rng_h = rng_factory.entity_stream(f"churn_hazard:{y:04d}{m:02d}", c.index)
            u_draws[idx, m_idx] = float(rng_h.random())

            # Customer is eligible to churn in months after their signup date
            if c.signup_date < month_starts[m_idx]:
                t_mult = float(tier_mult_map[psub.tier_by_month[m_idx]])
                tenure_days = (month_ends[m_idx] - c.signup_date).days
                ten_mult = short_mult if tenure_days < short_tenure_days else 1.0
                d_mult = down_mult if psub.recent_downgrade_by_month[m_idx] else 1.0
                factors[idx, m_idx] = f_mult * t_mult * c_mult * ten_mult * d_mult

    # Deterministic bisection for base hazard
    target = cfg.churn.target_rate
    low = 0.0
    high = cap
    best_base = 0.0
    best_diff = float("inf")
    best_rate = 0.0

    n_iters = max(25, ch_cfg.bisection_iterations)
    for _ in range(n_iters):
        mid = 0.5 * (low + high)
        hazards = np.minimum(mid * factors, cap)
        churned_any = (u_draws < hazards).any(axis=1)
        rate = float(churned_any.mean())
        diff = abs(rate - target)
        if diff < best_diff:
            best_diff = diff
            best_base = mid
            best_rate = rate
        if rate < target:
            low = mid
        else:
            high = mid

    if not (cfg.churn.min_rate <= best_rate <= cfg.churn.max_rate):
        raise ValueError(
            f"Calibrated churn rate {best_rate:.4f} is outside allowed bounds "
            f"[{cfg.churn.min_rate:.4f}, {cfg.churn.max_rate:.4f}]"
        )
    if best_diff > ch_cfg.calibration_tolerance:
        raise ValueError(
            f"Calibrated churn rate {best_rate:.4f} differs from target {target:.4f} "
            f"by {best_diff:.4f} > tolerance {ch_cfg.calibration_tolerance:.4f}"
        )

    final_hazards = np.minimum(best_base * factors, cap)
    hits = u_draws < final_hazards

    results: list[CustomerChurnResult] = []
    for idx, c in enumerate(customers):
        rng_det = rng_factory.entity_stream("churn_detail", c.index)
        u_type = float(rng_det.random())
        vol_day = int(rng_det.integers(1, 29))
        u_loud = float(rng_det.random())

        row_hits = np.flatnonzero(hits[idx])
        if len(row_hits) == 0:
            results.append(
                CustomerChurnResult(
                    customer_id=c.customer_id,
                    churned=False,
                    churn_month_idx=None,
                    churn_date=None,
                    churn_type=None,
                    is_loud=False,
                    frailty_z=float(frailties[idx]),
                )
            )
            continue

        m_idx = int(row_hits[0])
        c_year, c_month = months[m_idx]
        invoice_date = date(c_year, c_month, c.billing_day)
        inv_churn_date = invoice_date + timedelta(days=ch_cfg.involuntary_cancel_offset_days)

        if (
            u_type < ch_cfg.involuntary_prob
            and inv_churn_date <= cfg.timeline.data_end
            and invoice_date >= c.signup_date
        ):
            c_type = "INVOLUNTARY"
            c_date = inv_churn_date
            is_loud = False
        else:
            c_type = "VOLUNTARY"
            c_date = date(c_year, c_month, vol_day)
            if c_date <= c.signup_date:
                c_date = min(c.signup_date + timedelta(days=1), month_ends[m_idx])
            is_loud = u_loud < u_cfg.loud_voluntary_prob

        results.append(
            CustomerChurnResult(
                customer_id=c.customer_id,
                churned=True,
                churn_month_idx=m_idx,
                churn_date=c_date,
                churn_type=c_type,
                is_loud=is_loud,
                frailty_z=float(frailties[idx]),
            )
        )

    return results, best_base


def build_churn_outcomes_2025(
    customers: list[CustomerRecord],
    churn_results: list[CustomerChurnResult],
    cfg: Config,
) -> pd.DataFrame:
    """Build 2025 training cycle churn_outcome rows for customers active on train_as_of."""
    train_as_of = cfg.timeline.train_as_of
    horizon_end = train_as_of + timedelta(days=cfg.timeline.label_horizon_days)
    pred_str = train_as_of.isoformat()
    hor_str = horizon_end.isoformat()

    rows: list[dict[str, object]] = []
    for c, res in zip(customers, churn_results):
        # Active on train_as_of iff signed up on/before train_as_of and not churned before train_as_of
        if c.signup_date > train_as_of:
            continue
        if res.churn_date is not None and res.churn_date < train_as_of:
            continue

        in_horizon = (
            res.churn_date is not None and train_as_of <= res.churn_date < horizon_end
        )
        rows.append(
            {
                "churn_id": ids.churn_outcome_id(c.customer_id, 2025),
                "customer_id": c.customer_id,
                "cycle_year": 2025,
                "prediction_date": pred_str,
                "horizon_end": hor_str,
                "churned": 1 if in_horizon else 0,
                "churn_date": res.churn_date.isoformat() if in_horizon and res.churn_date else None,
                "churn_type": res.churn_type if in_horizon else None,
            }
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "churn_id",
            "customer_id",
            "cycle_year",
            "prediction_date",
            "horizon_end",
            "churned",
            "churn_date",
            "churn_type",
        ],
    )
    return df.sort_values("churn_id", kind="mergesort").reset_index(drop=True)


def build_latent_dataframe(
    customers: list[CustomerRecord],
    churn_results: list[CustomerChurnResult],
) -> pd.DataFrame:
    """Build isolated ground-truth latent customer state DataFrame."""
    rows = [
        {
            "customer_id": c.customer_id,
            "hidden_segment": c.hidden_segment,
            "untreated_churn_date": res.churn_date.isoformat() if res.churn_date else None,
            "treated_churn_date": None,
            "true_effect_flag": None,
        }
        for c, res in zip(customers, churn_results)
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "customer_id",
            "hidden_segment",
            "untreated_churn_date",
            "treated_churn_date",
            "true_effect_flag",
        ],
    )
    return df.sort_values("customer_id", kind="mergesort").reset_index(drop=True)

