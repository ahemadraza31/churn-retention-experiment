"""Full untreated world orchestrator, database loader, and deterministic hashing."""

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
import hashlib
import sqlite3
from typing import Any
import pandas as pd

from churnexp.config import Config, load_config
from churnexp.generation.billing import (
    BillingEventRecord,
    billing_to_dataframe,
    generate_customer_billing,
)
from churnexp.generation.churn import (
    build_churn_outcomes_2025,
    build_latent_dataframe,
    simulate_untreated_churn,
)
from churnexp.generation.customers import (
    CustomerRecord,
    customers_to_dataframe,
    generate_customers,
)
from churnexp.generation.events import events_to_dataframe, generate_state_events
from churnexp.generation.subscriptions import (
    SubscriptionRecord,
    build_customer_subscriptions,
    get_simulation_months,
    pre_simulate_plan_changes,
    subscriptions_to_dataframe,
)
from churnexp.generation.support import (
    SupportCaseRecord,
    generate_customer_support,
    support_to_dataframe,
)
from churnexp.generation.usage import (
    UsageSnapshotRecord,
    generate_customer_usage,
    usage_to_dataframe,
)
from churnexp.rng import RngFactory

TABLE_LOAD_ORDER: list[tuple[str, str | list[str]]] = [
    ("customer", "customer_id"),
    ("subscription", "subscription_id"),
    ("usage_snapshot", "snapshot_id"),
    ("billing_event", "billing_event_id"),
    ("support_case", "case_id"),
    ("state_event", "event_id"),
    ("churn_outcome", "churn_id"),
    ("offer", "offer_id"),
    ("eligibility_rule", "rule_id"),
    ("offer_eligibility_rule", ["offer_id", "rule_id"]),
    ("feature_snapshot", ["customer_id", "as_of_date"]),
    ("risk_score", "score_id"),
    ("rule_evaluation", "evaluation_id"),
    ("campaign_contact", "contact_id"),
    ("retention_outcome", "retention_id"),
]


@dataclass(frozen=True)
class World:
    tables: dict[str, pd.DataFrame]
    latent: pd.DataFrame
    summary: dict[str, Any] = field(default_factory=dict)


def generate_customer_months(
    customer: CustomerRecord,
    subs: list[SubscriptionRecord],
    months: list[tuple[int, int]],
    churn_date_or_None: date | None,
    churn_type: str | None = None,
    is_loud: bool = False,
    cfg: Config | None = None,
    rng_factory: RngFactory | None = None,
    starting_case_seq: int = 1,
) -> tuple[list[UsageSnapshotRecord], list[BillingEventRecord], list[SupportCaseRecord]]:
    """Reusable, side-effect-free monthly generator for a single customer.

    Generates usage snapshots, billing events, and support cases across `months`.
    Designed so Milestone 7 can regenerate later months for customers saved by an offer.
    """
    if cfg is None:
        cfg = load_config("starter")
    if rng_factory is None:
        rng_factory = RngFactory(cfg.seed)

    usage_rows = generate_customer_usage(
        customer=customer,
        subs=subs,
        months=months,
        churn_date=churn_date_or_None,
        churn_type=churn_type,
        is_loud=is_loud,
        cfg=cfg,
        rng_factory=rng_factory,
    )
    billing_rows = generate_customer_billing(
        customer=customer,
        subs=subs,
        months=months,
        churn_date=churn_date_or_None,
        churn_type=churn_type,
        cfg=cfg,
        rng_factory=rng_factory,
    )
    support_rows = generate_customer_support(
        customer=customer,
        subs=subs,
        months=months,
        churn_date=churn_date_or_None,
        churn_type=churn_type,
        is_loud=is_loud,
        cfg=cfg,
        rng_factory=rng_factory,
        starting_case_seq=starting_case_seq,
    )
    return usage_rows, billing_rows, support_rows


def generate_world(cfg: Config) -> World:
    """Generate the full 18-month untreated world for all customers."""
    rng_factory = RngFactory(cfg.seed)
    months = get_simulation_months(cfg)

    customers = generate_customers(cfg, rng_factory)
    pre_subs = pre_simulate_plan_changes(customers, months, cfg, rng_factory)
    churn_results, calibrated_base = simulate_untreated_churn(
        customers, pre_subs, months, cfg, rng_factory
    )
    customers = [
        replace(c, hidden_segment=ch.hidden_segment)
        for c, ch in zip(customers, churn_results)
    ]

    all_subs: list[SubscriptionRecord] = []
    subs_by_customer: list[list[SubscriptionRecord]] = []
    all_usage: list[UsageSnapshotRecord] = []
    all_billing: list[BillingEventRecord] = []
    all_support: list[SupportCaseRecord] = []

    for c, psub, ch in zip(customers, pre_subs, churn_results):
        c_subs = build_customer_subscriptions(
            customer=c,
            pre_sub=psub,
            churn_date=ch.churn_date,
            churn_type=ch.churn_type,
            cfg=cfg,
        )
        subs_by_customer.append(c_subs)
        all_subs.extend(c_subs)

        u_rows, b_rows, s_rows = generate_customer_months(
            customer=c,
            subs=c_subs,
            months=months,
            churn_date_or_None=ch.churn_date,
            churn_type=ch.churn_type,
            is_loud=ch.is_loud,
            cfg=cfg,
            rng_factory=rng_factory,
        )
        all_usage.extend(u_rows)
        all_billing.extend(b_rows)
        all_support.extend(s_rows)

    all_events = generate_state_events(customers, subs_by_customer, churn_results)

    customer_df = customers_to_dataframe(customers)
    subscription_df = subscriptions_to_dataframe(all_subs)
    usage_df = usage_to_dataframe(all_usage)
    billing_df = billing_to_dataframe(all_billing)
    support_df = support_to_dataframe(all_support)
    state_event_df = events_to_dataframe(all_events)
    churn_outcome_df = build_churn_outcomes_2025(customers, churn_results, cfg)
    latent_df = build_latent_dataframe(customers, churn_results)

    tables = {
        "customer": customer_df,
        "subscription": subscription_df,
        "usage_snapshot": usage_df,
        "billing_event": billing_df,
        "support_case": support_df,
        "state_event": state_event_df,
        "churn_outcome": churn_outcome_df,
    }

    # Summary statistics
    n_customers = len(customers)
    n_churned = sum(1 for r in churn_results if r.churned)
    n_voluntary = sum(1 for r in churn_results if r.churn_type == "VOLUNTARY")
    n_involuntary = sum(1 for r in churn_results if r.churn_type == "INVOLUNTARY")
    n_plan_changes = sum(1 for s in all_subs if s.end_reason == "PLAN_CHANGE")

    train_as_of = cfg.timeline.train_as_of
    train_horizon_end = train_as_of + timedelta(days=cfg.timeline.label_horizon_days)
    score_as_of = cfg.timeline.score_as_of
    score_horizon_end = score_as_of + timedelta(days=cfg.timeline.label_horizon_days)

    active_train = 0
    churn_2025_horizon = 0
    active_score = 0
    churn_2026_horizon = 0

    for c, ch in zip(customers, churn_results):
        if c.signup_date <= train_as_of and (
            ch.churn_date is None or ch.churn_date >= train_as_of
        ):
            active_train += 1
            if ch.churn_date is not None and train_as_of <= ch.churn_date < train_horizon_end:
                churn_2025_horizon += 1

        if c.signup_date <= score_as_of and (
            ch.churn_date is None or ch.churn_date >= score_as_of
        ):
            active_score += 1
            if ch.churn_date is not None and score_as_of <= ch.churn_date < score_horizon_end:
                churn_2026_horizon += 1

    summary = {
        "n_customers": n_customers,
        "n_churned": n_churned,
        "overall_churn_rate": n_churned / float(n_customers) if n_customers else 0.0,
        "n_voluntary": n_voluntary,
        "n_involuntary": n_involuntary,
        "n_plan_changes": n_plan_changes,
        "active_on_train_as_of": active_train,
        "active_on_score_as_of": active_score,
        "untreated_churn_2025_horizon": churn_2025_horizon,
        "untreated_churn_2026_horizon": churn_2026_horizon,
        "calibrated_base_hazard": calibrated_base,
    }

    return World(tables=tables, latent=latent_df, summary=summary)


def load_world(world: World, conn: sqlite3.Connection) -> None:
    """Insert world tables into SQLite with foreign keys ON, parents first.

    Strictly validates that every DataFrame has no columns absent from the table schema
    and is not missing any NOT NULL or PRIMARY KEY columns.
    """
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    for table_name, pk_col in TABLE_LOAD_ORDER:
        if table_name not in world.tables:
            continue
        df = world.tables[table_name]

        cur.execute(f"PRAGMA table_info({table_name});")
        info_rows = cur.fetchall()
        db_cols = [row[1] for row in info_rows]
        db_col_set = set(db_cols)
        not_null_cols = {
            row[1] for row in info_rows if (row[3] == 1 and row[4] is None) or row[5] > 0
        }

        df_col_set = set(df.columns)
        extra_cols = df_col_set - db_col_set
        if extra_cols:
            raise ValueError(
                f"Table {table_name!r} DataFrame contains unknown columns not in schema: "
                f"{sorted(extra_cols)}"
            )

        missing_not_null = not_null_cols - df_col_set
        if missing_not_null:
            raise ValueError(
                f"Table {table_name!r} DataFrame is missing required NOT NULL columns: "
                f"{sorted(missing_not_null)}"
            )

        if df.empty:
            continue

        present_cols = [c for c in db_cols if c in df_col_set]
        sorted_df = df.sort_values(pk_col, kind="mergesort")[present_cols]
        records = sorted_df.astype(object).where(pd.notnull(sorted_df), None).values.tolist()

        cols_sql = ", ".join(present_cols)
        placeholders = ", ".join(["?"] * len(present_cols))
        sql = f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders});"
        cur.executemany(sql, records)

    conn.commit()


def _dataframe_sha256(df: pd.DataFrame, pk_col: str | list[str]) -> str:
    sorted_df = df.sort_values(pk_col, kind="mergesort")
    csv_bytes = sorted_df.to_csv(
        index=False,
        float_format="%.6f",
        lineterminator="\n",
    ).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def hash_world(world: World) -> dict[str, str]:
    """Compute deterministic SHA-256 per table and for latent ground truth."""
    hashes: dict[str, str] = {}
    for table_name, pk_col in TABLE_LOAD_ORDER:
        if table_name in world.tables:
            hashes[table_name] = _dataframe_sha256(world.tables[table_name], pk_col)
    hashes["latent"] = _dataframe_sha256(world.latent, "customer_id")
    return hashes

