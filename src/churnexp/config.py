"""Configuration loader, dataclasses, and invariant validation for churnexp."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
import yaml


@dataclass(frozen=True)
class PopulationConfig:
    n_customers: int


@dataclass(frozen=True)
class TimelineConfig:
    data_start: date
    data_end: date
    train_as_of: date
    score_as_of: date
    label_horizon_days: int
    feature_lookback_months: int
    outcome_window_days: int


@dataclass(frozen=True)
class ChurnConfig:
    target_rate: float
    min_rate: float
    max_rate: float


@dataclass(frozen=True)
class ExperimentConfig:
    treatment_share: float
    stratify_by: str


@dataclass(frozen=True)
class AnomaliesConfig:
    records_per_type: int


@dataclass(frozen=True)
class CustomersGenConfig:
    early_signup_share: float = 0.85
    early_signup_start: date = date(2023, 1, 1)
    early_signup_end: date = date(2024, 12, 31)
    late_signup_start: date = date(2025, 1, 1)
    late_signup_end: date = date(2025, 12, 15)
    segment_probs: dict[str, float] = field(
        default_factory=lambda: {"CONSUMER": 0.75, "SMB": 0.25}
    )
    channel_probs: dict[str, float] = field(
        default_factory=lambda: {
            "ORGANIC": 0.40,
            "PAID": 0.30,
            "PARTNER": 0.15,
            "REFERRAL": 0.15,
        }
    )
    regions: list[str] = field(
        default_factory=lambda: ["NA", "EU", "APAC", "LATAM"]
    )
    seasonal_prob: float = 0.12
    marketing_opt_in_prob: float = 0.82
    max_billing_day: int = 28


@dataclass(frozen=True)
class SubscriptionsGenConfig:
    consumer_tier_probs: dict[str, float] = field(
        default_factory=lambda: {"BASIC": 0.50, "STANDARD": 0.35, "PREMIUM": 0.15}
    )
    smb_tier_probs: dict[str, float] = field(
        default_factory=lambda: {"BASIC": 0.20, "STANDARD": 0.45, "PREMIUM": 0.35}
    )
    tier_price_cents: dict[str, int] = field(
        default_factory=lambda: {"BASIC": 999, "STANDARD": 1999, "PREMIUM": 3999}
    )
    tier_gross_margin_pct: dict[str, float] = field(
        default_factory=lambda: {"BASIC": 0.55, "STANDARD": 0.62, "PREMIUM": 0.70}
    )
    monthly_plan_change_prob: float = 0.012
    upgrade_prob: float = 0.55


@dataclass(frozen=True)
class ChurnGenConfig:
    frailty_sigma: float = 0.7
    tier_hazard_mult: dict[str, float] = field(
        default_factory=lambda: {"BASIC": 1.3, "STANDARD": 1.0, "PREMIUM": 0.7}
    )
    channel_hazard_mult: dict[str, float] = field(
        default_factory=lambda: {
            "PAID": 1.2,
            "REFERRAL": 0.7,
            "ORGANIC": 1.0,
            "PARTNER": 1.0,
        }
    )
    short_tenure_months: int = 6
    short_tenure_mult: float = 1.5
    recent_downgrade_months: int = 3
    recent_downgrade_mult: float = 1.6
    monthly_hazard_cap: float = 0.08
    calibration_tolerance: float = 0.005
    bisection_iterations: int = 20
    involuntary_prob: float = 0.30
    involuntary_cancel_offset_days: int = 8
    hidden_segment_probs: dict[str, float] = field(
        default_factory=lambda: {
            "PERSUADABLE": 0.25,
            "SURE_THING": 0.45,
            "LOST_CAUSE": 0.25,
            "SLEEPING_DOG": 0.05,
        }
    )


@dataclass(frozen=True)
class UsageGenConfig:
    base_minutes: dict[str, float] = field(
        default_factory=lambda: {
            "BASIC": 600.0,
            "STANDARD": 1200.0,
            "PREMIUM": 2000.0,
        }
    )
    plan_limit_minutes: dict[str, float] = field(
        default_factory=lambda: {
            "BASIC": 1500.0,
            "STANDARD": 3000.0,
            "PREMIUM": 6000.0,
        }
    )
    smb_multiplier: float = 1.5
    customer_lognormal_sigma: float = 0.35
    monthly_noise_sigma: float = 0.15
    seasonal_off_months_count: int = 3
    seasonal_off_multiplier: float = 0.25
    loud_voluntary_prob: float = 0.75
    loud_decay_multipliers: dict[int, float] = field(
        default_factory=lambda: {3: 0.90, 2: 0.75, 1: 0.55, 0: 0.35}
    )
    decoy_dip_prob: float = 0.07
    decoy_dip_months: int = 2
    decoy_dip_multiplier: float = 0.55
    upgrade_usage_multiplier: float = 1.2
    downgrade_usage_multiplier: float = 0.8


@dataclass(frozen=True)
class BillingGenConfig:
    due_days_offset: int = 7
    payment_max_delay_days: int = 3
    failure_prob_consumer: float = 0.025
    failure_prob_smb: float = 0.015
    failed_event_offset_days: int = 1
    retry_min_delay_days: int = 3
    retry_max_delay_days: int = 45
    involuntary_retry_offset_days: int = 4
    involuntary_prev_month_fail_prob: float = 0.60
    failure_reasons: list[str] = field(
        default_factory=lambda: [
            "INSUFFICIENT_FUNDS",
            "EXPIRED_CARD",
            "DO_NOT_HONOR",
            "NETWORK_ERROR",
        ]
    )


@dataclass(frozen=True)
class SupportGenConfig:
    poisson_rate_consumer: float = 0.05
    poisson_rate_smb: float = 0.07
    category_probs: dict[str, float] = field(
        default_factory=lambda: {
            "TECHNICAL": 0.45,
            "BILLING": 0.20,
            "GENERAL": 0.35,
        }
    )
    severity_probs: dict[str, float] = field(
        default_factory=lambda: {"LOW": 0.65, "MEDIUM": 0.27, "HIGH": 0.08}
    )
    loud_churn_rate_multiplier: float = 4.0
    loud_churn_window_months: int = 3
    loud_cancellation_inquiry_prob: float = 0.35
    loud_cancellation_window_months: int = 2
    decoy_cancellation_inquiry_prob: float = 0.005
    loud_high_severity_prob: float = 0.25
    involuntary_billing_case_prob: float = 0.35
    involuntary_billing_window_months: int = 2
    resolution_min_days: int = 1
    resolution_max_days: int = 10
    escalation_prob: float = 0.03
    escalation_extra_days: int = 14


@dataclass(frozen=True)
class GeneratorConfig:
    customers: CustomersGenConfig = field(default_factory=CustomersGenConfig)
    subscriptions: SubscriptionsGenConfig = field(
        default_factory=SubscriptionsGenConfig
    )
    churn: ChurnGenConfig = field(default_factory=ChurnGenConfig)
    usage: UsageGenConfig = field(default_factory=UsageGenConfig)
    billing: BillingGenConfig = field(default_factory=BillingGenConfig)
    support: SupportGenConfig = field(default_factory=SupportGenConfig)


@dataclass(frozen=True)
class Config:
    scale: str
    seed: int
    population: PopulationConfig
    timeline: TimelineConfig
    churn: ChurnConfig
    experiment: ExperimentConfig
    anomalies: AnomaliesConfig
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Cannot parse date from {value!r}")


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], Mapping) and isinstance(v, Mapping):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def validate_config(cfg: Config) -> None:
    """Validate temporal, population, rate, and experiment invariants."""
    # 1. Timeline order
    t = cfg.timeline
    if not (t.data_start < t.train_as_of < t.score_as_of < t.data_end):
        raise ValueError(
            f"Timeline order invariant violated: expected data_start ({t.data_start}) < "
            f"train_as_of ({t.train_as_of}) < score_as_of ({t.score_as_of}) < data_end ({t.data_end})"
        )

    # 2. Training label resolution before scoring date (leakage defense)
    train_label_end = t.train_as_of + timedelta(days=t.label_horizon_days)
    if train_label_end > t.score_as_of:
        raise ValueError(
            f"Temporal leakage invariant violated: training labels must be fully resolved before "
            f"scoring date. train_as_of + label_horizon_days ({train_label_end}) > score_as_of ({t.score_as_of})"
        )

    # 3. Score label horizon within data end (+ 1 day)
    score_label_end = t.score_as_of + timedelta(days=t.label_horizon_days)
    allowed_end = t.data_end + timedelta(days=1)
    if score_label_end > allowed_end:
        raise ValueError(
            f"Timeline data boundary violated: score_as_of + label_horizon_days ({score_label_end}) "
            f"must be <= data_end + 1 day ({allowed_end})"
        )

    # 4. Churn rate bounds within 0.05 to 0.20
    c = cfg.churn
    if not (0.05 <= c.min_rate <= c.target_rate <= c.max_rate <= 0.20):
        raise ValueError(
            f"Churn rate invariant violated: expected 0.05 <= min_rate <= target_rate <= max_rate <= 0.20. "
            f"Got min_rate={c.min_rate}, target_rate={c.target_rate}, max_rate={c.max_rate}"
        )

    # 5. Customer population bounds
    n = cfg.population.n_customers
    if not (1 <= n <= 999999):
        raise ValueError(
            f"Population invariant violated: expected 1 <= n_customers <= 999999, got {n}"
        )

    # 6. Experiment treatment share strictly between 0 and 1
    share = cfg.experiment.treatment_share
    if not (0.0 < share < 1.0):
        raise ValueError(
            f"Experiment invariant violated: treatment_share must be strictly between 0 and 1, got {share}"
        )

    # 7. Generator config invariants
    _validate_generator_config(cfg.generator, cfg.timeline)


def _check_prob_dist(name: str, dist: Mapping[Any, float], expected_keys: set[Any] | None = None) -> None:
    if not dist:
        raise ValueError(f"Generator probability distribution {name} must not be empty")
    if expected_keys is not None and set(dist.keys()) != expected_keys:
        raise ValueError(
            f"Generator probability distribution {name} keys mismatch: expected {expected_keys}, got {set(dist.keys())}"
        )
    for k, v in dist.items():
        if not (0.0 <= float(v) <= 1.0):
            raise ValueError(f"Generator probability {name}[{k!r}] out of [0, 1]: {v}")
    total = sum(float(v) for v in dist.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Generator probability distribution {name} must sum to 1.0, got {total}")


def _check_prob_scalar(name: str, val: float, allow_zero: bool = True, allow_one: bool = True) -> None:
    v = float(val)
    low_ok = v >= 0.0 if allow_zero else v > 0.0
    high_ok = v <= 1.0 if allow_one else v < 1.0
    if not (low_ok and high_ok):
        raise ValueError(f"Generator scalar probability {name} out of bounds [0, 1]: {val}")


def _validate_generator_config(gen: GeneratorConfig, timeline: TimelineConfig) -> None:
    # Customers
    cust = gen.customers
    _check_prob_scalar("customers.early_signup_share", cust.early_signup_share)
    _check_prob_scalar("customers.seasonal_prob", cust.seasonal_prob)
    _check_prob_scalar("customers.marketing_opt_in_prob", cust.marketing_opt_in_prob)
    if not (cust.early_signup_start <= cust.early_signup_end < cust.late_signup_start <= cust.late_signup_end <= timeline.data_end):
        raise ValueError("Generator customer signup date ranges are invalid or out of order")
    _check_prob_dist("customers.segment_probs", cust.segment_probs, {"CONSUMER", "SMB"})
    _check_prob_dist("customers.channel_probs", cust.channel_probs, {"ORGANIC", "PAID", "PARTNER", "REFERRAL"})
    if not cust.regions:
        raise ValueError("Generator customers.regions must not be empty")
    if not (1 <= cust.max_billing_day <= 28):
        raise ValueError(f"Generator customers.max_billing_day must be in 1..28, got {cust.max_billing_day}")

    # Subscriptions
    sub = gen.subscriptions
    tiers = {"BASIC", "STANDARD", "PREMIUM"}
    _check_prob_dist("subscriptions.consumer_tier_probs", sub.consumer_tier_probs, tiers)
    _check_prob_dist("subscriptions.smb_tier_probs", sub.smb_tier_probs, tiers)
    if set(sub.tier_price_cents.keys()) != tiers or any(int(p) <= 0 for p in sub.tier_price_cents.values()):
        raise ValueError("Generator subscriptions.tier_price_cents must have positive integer cents for BASIC, STANDARD, PREMIUM")
    if set(sub.tier_gross_margin_pct.keys()) != tiers or any(not (0.0 < float(m) <= 1.0) for m in sub.tier_gross_margin_pct.values()):
        raise ValueError("Generator subscriptions.tier_gross_margin_pct must be in (0, 1] for BASIC, STANDARD, PREMIUM")
    _check_prob_scalar("subscriptions.monthly_plan_change_prob", sub.monthly_plan_change_prob)
    _check_prob_scalar("subscriptions.upgrade_prob", sub.upgrade_prob)

    # Churn
    ch = gen.churn
    if ch.frailty_sigma < 0.0:
        raise ValueError("Generator churn.frailty_sigma must be non-negative")
    if set(ch.tier_hazard_mult.keys()) != tiers or any(float(v) <= 0.0 for v in ch.tier_hazard_mult.values()):
        raise ValueError("Generator churn.tier_hazard_mult must be positive for all tiers")
    if set(ch.channel_hazard_mult.keys()) != {"ORGANIC", "PAID", "PARTNER", "REFERRAL"} or any(float(v) <= 0.0 for v in ch.channel_hazard_mult.values()):
        raise ValueError("Generator churn.channel_hazard_mult must be positive for all channels")
    if ch.short_tenure_months <= 0 or ch.short_tenure_mult <= 0.0:
        raise ValueError("Generator churn short tenure parameters must be positive")
    if ch.recent_downgrade_months <= 0 or ch.recent_downgrade_mult <= 0.0:
        raise ValueError("Generator churn recent downgrade parameters must be positive")
    _check_prob_scalar("churn.monthly_hazard_cap", ch.monthly_hazard_cap, allow_zero=False)
    _check_prob_scalar("churn.calibration_tolerance", ch.calibration_tolerance, allow_zero=False)
    if ch.bisection_iterations < 5:
        raise ValueError("Generator churn.bisection_iterations must be >= 5")
    _check_prob_scalar("churn.involuntary_prob", ch.involuntary_prob)
    if ch.involuntary_cancel_offset_days <= 0:
        raise ValueError("Generator churn.involuntary_cancel_offset_days must be positive")
    _check_prob_dist(
        "churn.hidden_segment_probs",
        ch.hidden_segment_probs,
        {"PERSUADABLE", "SURE_THING", "LOST_CAUSE", "SLEEPING_DOG"},
    )

    # Usage
    usg = gen.usage
    if set(usg.base_minutes.keys()) != tiers or any(float(v) <= 0.0 for v in usg.base_minutes.values()):
        raise ValueError("Generator usage.base_minutes must be positive for all tiers")
    if set(usg.plan_limit_minutes.keys()) != tiers or any(float(usg.plan_limit_minutes[t]) < float(usg.base_minutes[t]) for t in tiers):
        raise ValueError("Generator usage.plan_limit_minutes must be >= base_minutes for all tiers")
    if usg.smb_multiplier <= 0.0 or usg.customer_lognormal_sigma < 0.0 or usg.monthly_noise_sigma < 0.0:
        raise ValueError("Generator usage multiplier/sigma parameters invalid")
    if not (1 <= usg.seasonal_off_months_count <= 11):
        raise ValueError("Generator usage.seasonal_off_months_count must be in 1..11")
    _check_prob_scalar("usage.seasonal_off_multiplier", usg.seasonal_off_multiplier, allow_zero=False)
    _check_prob_scalar("usage.loud_voluntary_prob", usg.loud_voluntary_prob)
    if set(usg.loud_decay_multipliers.keys()) != {0, 1, 2, 3} or any(not (0.0 < float(v) <= 1.0) for v in usg.loud_decay_multipliers.values()):
        raise ValueError("Generator usage.loud_decay_multipliers must cover months 0..3 with values in (0, 1]")
    _check_prob_scalar("usage.decoy_dip_prob", usg.decoy_dip_prob)
    if usg.decoy_dip_months <= 0 or not (0.0 < usg.decoy_dip_multiplier <= 1.0):
        raise ValueError("Generator usage decoy dip parameters invalid")
    if usg.upgrade_usage_multiplier <= 0.0 or usg.downgrade_usage_multiplier <= 0.0:
        raise ValueError("Generator usage plan change multipliers must be positive")

    # Billing
    bill = gen.billing
    if bill.due_days_offset < 0 or bill.payment_max_delay_days < 0:
        raise ValueError("Generator billing delay offsets must be non-negative")
    _check_prob_scalar("billing.failure_prob_consumer", bill.failure_prob_consumer)
    _check_prob_scalar("billing.failure_prob_smb", bill.failure_prob_smb)
    if bill.failed_event_offset_days <= 0 or bill.retry_min_delay_days <= 0 or bill.retry_max_delay_days < bill.retry_min_delay_days:
        raise ValueError("Generator billing retry/failure offsets invalid")
    if bill.involuntary_retry_offset_days <= 0:
        raise ValueError("Generator billing.involuntary_retry_offset_days must be positive")
    _check_prob_scalar("billing.involuntary_prev_month_fail_prob", bill.involuntary_prev_month_fail_prob)
    if not bill.failure_reasons:
        raise ValueError("Generator billing.failure_reasons must not be empty")

    # Support
    sup = gen.support
    if sup.poisson_rate_consumer < 0.0 or sup.poisson_rate_smb < 0.0:
        raise ValueError("Generator support Poisson rates must be non-negative")
    _check_prob_dist("support.category_probs", sup.category_probs, {"TECHNICAL", "BILLING", "GENERAL"})
    _check_prob_dist("support.severity_probs", sup.severity_probs, {"LOW", "MEDIUM", "HIGH"})
    if sup.loud_churn_rate_multiplier <= 0.0 or sup.loud_churn_window_months <= 0 or sup.loud_cancellation_window_months <= 0:
        raise ValueError("Generator support loud churn window/multiplier must be positive")
    _check_prob_scalar("support.loud_cancellation_inquiry_prob", sup.loud_cancellation_inquiry_prob)
    _check_prob_scalar("support.decoy_cancellation_inquiry_prob", sup.decoy_cancellation_inquiry_prob)
    _check_prob_scalar("support.loud_high_severity_prob", sup.loud_high_severity_prob)
    _check_prob_scalar("support.involuntary_billing_case_prob", sup.involuntary_billing_case_prob)
    if sup.involuntary_billing_window_months <= 0:
        raise ValueError("Generator support.involuntary_billing_window_months must be positive")
    if sup.resolution_min_days <= 0 or sup.resolution_max_days < sup.resolution_min_days or sup.escalation_extra_days < 0:
        raise ValueError("Generator support resolution day bounds invalid")
    _check_prob_scalar("support.escalation_prob", sup.escalation_prob)


def _parse_generator_config(gen_raw: Mapping[str, Any]) -> GeneratorConfig:
    c_raw = gen_raw["customers"]
    customers = CustomersGenConfig(
        early_signup_share=float(c_raw["early_signup_share"]),
        early_signup_start=_parse_date(c_raw["early_signup_start"]),
        early_signup_end=_parse_date(c_raw["early_signup_end"]),
        late_signup_start=_parse_date(c_raw["late_signup_start"]),
        late_signup_end=_parse_date(c_raw["late_signup_end"]),
        segment_probs={str(k): float(v) for k, v in c_raw["segment_probs"].items()},
        channel_probs={str(k): float(v) for k, v in c_raw["channel_probs"].items()},
        regions=[str(r) for r in c_raw["regions"]],
        seasonal_prob=float(c_raw["seasonal_prob"]),
        marketing_opt_in_prob=float(c_raw["marketing_opt_in_prob"]),
        max_billing_day=int(c_raw["max_billing_day"]),
    )

    s_raw = gen_raw["subscriptions"]
    subscriptions = SubscriptionsGenConfig(
        consumer_tier_probs={str(k): float(v) for k, v in s_raw["consumer_tier_probs"].items()},
        smb_tier_probs={str(k): float(v) for k, v in s_raw["smb_tier_probs"].items()},
        tier_price_cents={str(k): int(v) for k, v in s_raw["tier_price_cents"].items()},
        tier_gross_margin_pct={str(k): float(v) for k, v in s_raw["tier_gross_margin_pct"].items()},
        monthly_plan_change_prob=float(s_raw["monthly_plan_change_prob"]),
        upgrade_prob=float(s_raw["upgrade_prob"]),
    )

    ch_raw = gen_raw["churn"]
    churn_gen = ChurnGenConfig(
        frailty_sigma=float(ch_raw["frailty_sigma"]),
        tier_hazard_mult={str(k): float(v) for k, v in ch_raw["tier_hazard_mult"].items()},
        channel_hazard_mult={str(k): float(v) for k, v in ch_raw["channel_hazard_mult"].items()},
        short_tenure_months=int(ch_raw["short_tenure_months"]),
        short_tenure_mult=float(ch_raw["short_tenure_mult"]),
        recent_downgrade_months=int(ch_raw["recent_downgrade_months"]),
        recent_downgrade_mult=float(ch_raw["recent_downgrade_mult"]),
        monthly_hazard_cap=float(ch_raw["monthly_hazard_cap"]),
        calibration_tolerance=float(ch_raw["calibration_tolerance"]),
        bisection_iterations=int(ch_raw["bisection_iterations"]),
        involuntary_prob=float(ch_raw["involuntary_prob"]),
        involuntary_cancel_offset_days=int(ch_raw["involuntary_cancel_offset_days"]),
        hidden_segment_probs={str(k): float(v) for k, v in ch_raw["hidden_segment_probs"].items()},
    )

    u_raw = gen_raw["usage"]
    usage = UsageGenConfig(
        base_minutes={str(k): float(v) for k, v in u_raw["base_minutes"].items()},
        plan_limit_minutes={str(k): float(v) for k, v in u_raw["plan_limit_minutes"].items()},
        smb_multiplier=float(u_raw["smb_multiplier"]),
        customer_lognormal_sigma=float(u_raw["customer_lognormal_sigma"]),
        monthly_noise_sigma=float(u_raw["monthly_noise_sigma"]),
        seasonal_off_months_count=int(u_raw["seasonal_off_months_count"]),
        seasonal_off_multiplier=float(u_raw["seasonal_off_multiplier"]),
        loud_voluntary_prob=float(u_raw["loud_voluntary_prob"]),
        loud_decay_multipliers={int(k): float(v) for k, v in u_raw["loud_decay_multipliers"].items()},
        decoy_dip_prob=float(u_raw["decoy_dip_prob"]),
        decoy_dip_months=int(u_raw["decoy_dip_months"]),
        decoy_dip_multiplier=float(u_raw["decoy_dip_multiplier"]),
        upgrade_usage_multiplier=float(u_raw["upgrade_usage_multiplier"]),
        downgrade_usage_multiplier=float(u_raw["downgrade_usage_multiplier"]),
    )

    b_raw = gen_raw["billing"]
    billing = BillingGenConfig(
        due_days_offset=int(b_raw["due_days_offset"]),
        payment_max_delay_days=int(b_raw["payment_max_delay_days"]),
        failure_prob_consumer=float(b_raw["failure_prob_consumer"]),
        failure_prob_smb=float(b_raw["failure_prob_smb"]),
        failed_event_offset_days=int(b_raw["failed_event_offset_days"]),
        retry_min_delay_days=int(b_raw["retry_min_delay_days"]),
        retry_max_delay_days=int(b_raw["retry_max_delay_days"]),
        involuntary_retry_offset_days=int(b_raw["involuntary_retry_offset_days"]),
        involuntary_prev_month_fail_prob=float(b_raw["involuntary_prev_month_fail_prob"]),
        failure_reasons=[str(r) for r in b_raw["failure_reasons"]],
    )

    sup_raw = gen_raw["support"]
    support = SupportGenConfig(
        poisson_rate_consumer=float(sup_raw["poisson_rate_consumer"]),
        poisson_rate_smb=float(sup_raw["poisson_rate_smb"]),
        category_probs={str(k): float(v) for k, v in sup_raw["category_probs"].items()},
        severity_probs={str(k): float(v) for k, v in sup_raw["severity_probs"].items()},
        loud_churn_rate_multiplier=float(sup_raw["loud_churn_rate_multiplier"]),
        loud_churn_window_months=int(sup_raw["loud_churn_window_months"]),
        loud_cancellation_inquiry_prob=float(sup_raw["loud_cancellation_inquiry_prob"]),
        loud_cancellation_window_months=int(sup_raw["loud_cancellation_window_months"]),
        decoy_cancellation_inquiry_prob=float(sup_raw["decoy_cancellation_inquiry_prob"]),
        loud_high_severity_prob=float(sup_raw["loud_high_severity_prob"]),
        involuntary_billing_case_prob=float(sup_raw["involuntary_billing_case_prob"]),
        involuntary_billing_window_months=int(sup_raw["involuntary_billing_window_months"]),
        resolution_min_days=int(sup_raw["resolution_min_days"]),
        resolution_max_days=int(sup_raw["resolution_max_days"]),
        escalation_prob=float(sup_raw["escalation_prob"]),
        escalation_extra_days=int(sup_raw["escalation_extra_days"]),
    )

    return GeneratorConfig(
        customers=customers,
        subscriptions=subscriptions,
        churn=churn_gen,
        usage=usage,
        billing=billing,
        support=support,
    )


def _config_from_dict(data: Mapping[str, Any]) -> Config:
    pop = PopulationConfig(n_customers=int(data["population"]["n_customers"]))
    tl_raw = data["timeline"]
    timeline = TimelineConfig(
        data_start=_parse_date(tl_raw["data_start"]),
        data_end=_parse_date(tl_raw["data_end"]),
        train_as_of=_parse_date(tl_raw["train_as_of"]),
        score_as_of=_parse_date(tl_raw["score_as_of"]),
        label_horizon_days=int(tl_raw["label_horizon_days"]),
        feature_lookback_months=int(tl_raw["feature_lookback_months"]),
        outcome_window_days=int(tl_raw["outcome_window_days"]),
    )
    churn = ChurnConfig(
        target_rate=float(data["churn"]["target_rate"]),
        min_rate=float(data["churn"]["min_rate"]),
        max_rate=float(data["churn"]["max_rate"]),
    )
    experiment = ExperimentConfig(
        treatment_share=float(data["experiment"]["treatment_share"]),
        stratify_by=str(data["experiment"]["stratify_by"]),
    )
    anomalies = AnomaliesConfig(
        records_per_type=int(data["anomalies"]["records_per_type"])
    )
    generator = _parse_generator_config(data["generator"])

    cfg = Config(
        scale=str(data["scale"]),
        seed=int(data["seed"]),
        population=pop,
        timeline=timeline,
        churn=churn,
        experiment=experiment,
        anomalies=anomalies,
        generator=generator,
    )
    validate_config(cfg)
    return cfg


def load_config(scale: str = "starter", config_dir: Path | str | None = None) -> Config:
    """Load configuration for the requested scale (starter or full).

    'full' loads default.yaml.
    'starter' loads default.yaml and deep-merges starter.yaml overrides.
    """
    if config_dir is None:
        # Locate project root config directory relative to this file
        base_dir = Path(__file__).resolve().parent.parent.parent / "config"
    else:
        base_dir = Path(config_dir)

    default_path = base_dir / "default.yaml"
    if not default_path.is_file():
        raise FileNotFoundError(f"Default config not found at {default_path}")

    with open(default_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    scale_lower = scale.lower()
    if scale_lower == "full":
        pass
    elif scale_lower == "starter":
        starter_path = base_dir / "starter.yaml"
        if not starter_path.is_file():
            raise FileNotFoundError(f"Starter config not found at {starter_path}")
        with open(starter_path, "r", encoding="utf-8") as f:
            starter_data = yaml.safe_load(f) or {}
        data = _deep_merge(data, starter_data)
    else:
        raise ValueError(f"Unknown scale: {scale!r}. Expected 'starter' or 'full'.")

    return _config_from_dict(data)
