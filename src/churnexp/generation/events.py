"""Append-only state event generation for churnexp."""

from dataclasses import dataclass
import pandas as pd

from churnexp import ids
from churnexp.generation.churn import CustomerChurnResult
from churnexp.generation.customers import CustomerRecord
from churnexp.generation.subscriptions import SubscriptionRecord


@dataclass(frozen=True)
class StateEventRecord:
    event_id: str
    entity_type: str
    entity_id: str
    from_state: str
    to_state: str
    event_ts: str
    reason_code: str | None
    source: str | None


def generate_state_events(
    customers: list[CustomerRecord],
    subs_by_customer: list[list[SubscriptionRecord]],
    churn_results: list[CustomerChurnResult],
) -> list[StateEventRecord]:
    """Generate sorted state_event rows for customers and subscriptions."""
    raw: list[tuple[str, str, str, str, str, str | None, str | None]] = []

    for c, subs, ch in zip(customers, subs_by_customer, churn_results):
        # Customer activation
        raw.append(
            (
                f"{c.signup_date.isoformat()}T00:00:00",
                c.customer_id,
                "CUSTOMER",
                "INIT",
                "ACTIVE",
                "SIGNUP",
                "SYSTEM",
            )
        )
        # Customer churn transition
        if ch.churn_date is not None:
            raw.append(
                (
                    f"{ch.churn_date.isoformat()}T23:59:59",
                    c.customer_id,
                    "CUSTOMER",
                    "ACTIVE",
                    "CHURNED",
                    f"{ch.churn_type}_CANCEL" if ch.churn_type else "CHURN",
                    "SYSTEM",
                )
            )

        # Subscription transitions
        for s in subs:
            start_reason = "INITIAL_SIGNUP" if s.sequence_no == 1 else "PLAN_CHANGE"
            raw.append(
                (
                    f"{s.start_date.isoformat()}T00:00:00",
                    s.subscription_id,
                    "SUBSCRIPTION",
                    "INIT",
                    "ACTIVE",
                    start_reason,
                    "SYSTEM",
                )
            )
            if s.end_date is not None:
                to_st = "EXPIRED" if s.end_reason == "PLAN_CHANGE" else "CANCELLED"
                raw.append(
                    (
                        f"{s.end_date.isoformat()}T23:59:59",
                        s.subscription_id,
                        "SUBSCRIPTION",
                        "ACTIVE",
                        to_st,
                        s.end_reason,
                        "SYSTEM",
                    )
                )

    # Assigned in sorted (event_ts, entity_id) order
    raw.sort(key=lambda x: (x[0], x[1], x[2], x[4]))

    records: list[StateEventRecord] = []
    for seq, (event_ts, entity_id, entity_type, from_st, to_st, reason, source) in enumerate(
        raw, start=1
    ):
        records.append(
            StateEventRecord(
                event_id=ids.state_event_id(seq),
                entity_type=entity_type,
                entity_id=entity_id,
                from_state=from_st,
                to_state=to_st,
                event_ts=event_ts,
                reason_code=reason,
                source=source,
            )
        )
    return records


def events_to_dataframe(records: list[StateEventRecord]) -> pd.DataFrame:
    """Convert state event records to DataFrame sorted by event_id."""
    rows = [
        {
            "event_id": r.event_id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "from_state": r.from_state,
            "to_state": r.to_state,
            "event_ts": r.event_ts,
            "reason_code": r.reason_code,
            "source": r.source,
        }
        for r in records
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "event_id",
            "entity_type",
            "entity_id",
            "from_state",
            "to_state",
            "event_ts",
            "reason_code",
            "source",
        ],
    )
    return df.sort_values("event_id", kind="mergesort").reset_index(drop=True)

