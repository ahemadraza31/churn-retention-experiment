"""Customer population and latent segment generation for churnexp."""

from dataclasses import dataclass
from datetime import date, timedelta
import pandas as pd

from churnexp import ids
from churnexp.config import Config
from churnexp.rng import RngFactory


@dataclass(frozen=True)
class CustomerRecord:
    index: int
    customer_id: str
    signup_date: date
    segment: str
    channel: str
    region: str
    usage_pattern: str
    marketing_opt_in: int
    billing_day: int
    hidden_segment: str


def _draw_categorical(u: float, items: list[tuple[str, float]]) -> str:
    cum = 0.0
    for key, prob in items[:-1]:
        cum += prob
        if u < cum:
            return key
    return items[-1][0]


def generate_customers(cfg: Config, rng_factory: RngFactory) -> list[CustomerRecord]:
    """Generate deterministic customer records and their latent segments."""
    c_cfg = cfg.generator.customers
    ch_cfg = cfg.generator.churn
    n = cfg.population.n_customers

    early_days = (c_cfg.early_signup_end - c_cfg.early_signup_start).days + 1
    late_days = (c_cfg.late_signup_end - c_cfg.late_signup_start).days + 1

    seg_items = [
        ("CONSUMER", float(c_cfg.segment_probs["CONSUMER"])),
        ("SMB", float(c_cfg.segment_probs["SMB"])),
    ]
    chan_items = [
        ("ORGANIC", float(c_cfg.channel_probs["ORGANIC"])),
        ("PAID", float(c_cfg.channel_probs["PAID"])),
        ("PARTNER", float(c_cfg.channel_probs["PARTNER"])),
        ("REFERRAL", float(c_cfg.channel_probs["REFERRAL"])),
    ]
    regions = list(c_cfg.regions)
    n_regions = len(regions)

    hidden_items = [
        ("PERSUADABLE", float(ch_cfg.hidden_segment_probs["PERSUADABLE"])),
        ("SURE_THING", float(ch_cfg.hidden_segment_probs["SURE_THING"])),
        ("LOST_CAUSE", float(ch_cfg.hidden_segment_probs["LOST_CAUSE"])),
        ("SLEEPING_DOG", float(ch_cfg.hidden_segment_probs["SLEEPING_DOG"])),
    ]

    records: list[CustomerRecord] = []
    for i in range(1, n + 1):
        cid = ids.customer_id(i)
        rng = rng_factory.entity_stream("customer", i)

        if float(rng.random()) < c_cfg.early_signup_share:
            offset = int(rng.integers(0, early_days))
            signup = c_cfg.early_signup_start + timedelta(days=offset)
        else:
            offset = int(rng.integers(0, late_days))
            signup = c_cfg.late_signup_start + timedelta(days=offset)

        segment = _draw_categorical(float(rng.random()), seg_items)
        channel = _draw_categorical(float(rng.random()), chan_items)
        region = regions[int(rng.integers(0, n_regions))]
        usage_pattern = "SEASONAL" if float(rng.random()) < c_cfg.seasonal_prob else "STEADY"
        marketing_opt_in = 1 if float(rng.random()) < c_cfg.marketing_opt_in_prob else 0
        billing_day = min(signup.day, c_cfg.max_billing_day)

        rng_lat = rng_factory.entity_stream("latent_segment", i)
        hidden_seg = _draw_categorical(float(rng_lat.random()), hidden_items)

        records.append(
            CustomerRecord(
                index=i,
                customer_id=cid,
                signup_date=signup,
                segment=segment,
                channel=channel,
                region=region,
                usage_pattern=usage_pattern,
                marketing_opt_in=marketing_opt_in,
                billing_day=billing_day,
                hidden_segment=hidden_seg,
            )
        )

    return records


def customers_to_dataframe(customers: list[CustomerRecord]) -> pd.DataFrame:
    """Convert customer records to the canonical customer table DataFrame."""
    rows = [
        {
            "customer_id": c.customer_id,
            "signup_date": c.signup_date.isoformat(),
            "segment": c.segment,
            "channel": c.channel,
            "region": c.region,
            "usage_pattern": c.usage_pattern,
            "marketing_opt_in": c.marketing_opt_in,
        }
        for c in customers
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "customer_id",
            "signup_date",
            "segment",
            "channel",
            "region",
            "usage_pattern",
            "marketing_opt_in",
        ],
    )
    return df.sort_values("customer_id", kind="mergesort").reset_index(drop=True)

