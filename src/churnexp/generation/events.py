"""Append-only state event generation for churnexp."""

from dataclasses import dataclass
from typing import Mapping
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


def rebuild_state_events_from_tables(
    tables: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Rebuild the entire `state_event` table from final `customer`, `subscription`, and `campaign_contact` tables."""
    raw: list[tuple[str, str, str, str, str, str | None, str | None]] = []

    cust_df = tables.get("customer")
    sub_df = tables.get("subscription")
    cc_df = tables.get("campaign_contact")

    # Determine observed churn per customer from final subscription
    churn_by_cid: dict[str, tuple[str, str]] = {}
    if sub_df is not None and not sub_df.empty:
        sub_sorted = sub_df.sort_values(["customer_id", "sequence_no"], kind="mergesort")
        for row in sub_sorted.itertuples(index=False):
            cid = str(row.customer_id)
            sid = str(row.subscription_id)
            seq = int(row.sequence_no)
            s_date = str(row.start_date)
            e_val = getattr(row, "end_date", None)
            e_date = None if e_val is None or pd.isna(e_val) or str(e_val) == "" else str(e_val)
            r_val = getattr(row, "end_reason", None)
            e_reason = None if r_val is None or pd.isna(r_val) or str(r_val) == "" else str(r_val)

            start_reason = "INITIAL_SIGNUP" if seq == 1 else "PLAN_CHANGE"
            raw.append(
                (
                    f"{s_date}T00:00:00",
                    sid,
                    "SUBSCRIPTION",
                    "INIT",
                    "ACTIVE",
                    start_reason,
                    "SYSTEM",
                )
            )
            if e_date is not None:
                to_st = "EXPIRED" if e_reason == "PLAN_CHANGE" else "CANCELLED"
                raw.append(
                    (
                        f"{e_date}T23:59:59",
                        sid,
                        "SUBSCRIPTION",
                        "ACTIVE",
                        to_st,
                        e_reason,
                        "SYSTEM",
                    )
                )
                if e_reason in ("VOLUNTARY_CANCEL", "INVOLUNTARY_CANCEL"):
                    churn_by_cid[cid] = (e_date, e_reason)

    if cust_df is not None and not cust_df.empty:
        for row in cust_df.itertuples(index=False):
            cid = str(row.customer_id)
            signup_str = str(row.signup_date)
            raw.append(
                (
                    f"{signup_str}T00:00:00",
                    cid,
                    "CUSTOMER",
                    "INIT",
                    "ACTIVE",
                    "SIGNUP",
                    "SYSTEM",
                )
            )
            if cid in churn_by_cid:
                c_date, c_reason = churn_by_cid[cid]
                raw.append(
                    (
                        f"{c_date}T23:59:59",
                        cid,
                        "CUSTOMER",
                        "ACTIVE",
                        "CHURNED",
                        c_reason,
                        "SYSTEM",
                    )
                )

    if cc_df is not None and not cc_df.empty:
        for row in cc_df.itertuples(index=False):
            contact_id = str(row.contact_id)
            status = str(row.contact_status)
            assigned_at = str(row.assigned_at)
            assign_date = assigned_at[:10]
            sent_val = getattr(row, "sent_at", None)
            sent_at = (
                f"{assign_date}T10:00:00"
                if sent_val is None or pd.isna(sent_val) or str(sent_val) == ""
                else str(sent_val)
            )
            responded = int(row.responded)
            redeemed = int(row.redeemed)

            raw.append(
                (
                    assigned_at,
                    contact_id,
                    "CAMPAIGN_CONTACT",
                    "INIT",
                    "ASSIGNED",
                    "CAMPAIGN_ASSIGNED",
                    "CAMPAIGN_ENGINE",
                )
            )
            if status == "WITHHELD":
                raw.append(
                    (
                        f"{assign_date}T10:00:00",
                        contact_id,
                        "CAMPAIGN_CONTACT",
                        "ASSIGNED",
                        "WITHHELD",
                        "CONTROL_HOLDOUT",
                        "CAMPAIGN_ENGINE",
                    )
                )
            elif status == "DELIVERY_FAILED":
                raw.append(
                    (
                        sent_at,
                        contact_id,
                        "CAMPAIGN_CONTACT",
                        "ASSIGNED",
                        "DELIVERY_FAILED",
                        "DELIVERY_ERROR",
                        "CAMPAIGN_ENGINE",
                    )
                )
            elif status == "SENT":
                raw.append(
                    (
                        sent_at,
                        contact_id,
                        "CAMPAIGN_CONTACT",
                        "ASSIGNED",
                        "SENT",
                        "OFFER_SENT",
                        "CAMPAIGN_ENGINE",
                    )
                )
                if responded == 1:
                    raw.append(
                        (
                            f"{assign_date}T12:00:00",
                            contact_id,
                            "CAMPAIGN_CONTACT",
                            "SENT",
                            "RESPONDED",
                            "CUSTOMER_RESPONDED",
                            "CAMPAIGN_ENGINE",
                        )
                    )
                if redeemed == 1:
                    raw.append(
                        (
                            f"{assign_date}T14:00:00",
                            contact_id,
                            "CAMPAIGN_CONTACT",
                            "RESPONDED",
                            "REDEEMED",
                            "OFFER_REDEEMED",
                            "CAMPAIGN_ENGINE",
                        )
                    )

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
    return events_to_dataframe(records)


