"""Read-only domain query services for Streamlit actor dashboard and APIs."""

from __future__ import annotations

import functools
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping
import pandas as pd

from churnexp.validation.checks import load_tables_from_db
from churnexp.validation.detectors import run_detectors
from churnexp.validation.report import Finding


def get_ro_connection(db_path: Path | str) -> sqlite3.Connection:
    """Open a strictly read-only SQLite connection using URI mode=ro."""
    resolved = Path(db_path).resolve()
    return sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)


def _extract_customer_id(f: Finding) -> str | None:
    """Extract customer_id from finding evidence or entity_id."""
    if "customer_id" in f.evidence and f.evidence["customer_id"]:
        return str(f.evidence["customer_id"])
    if f.entity_type == "customer":
        return str(f.entity_id)
    return None


@functools.lru_cache(maxsize=4)
def _get_cached_detector_findings(db_path_str: str, mtime: float) -> list[Finding]:
    """Cache detector findings based on database path and modification timestamp."""
    conn = get_ro_connection(db_path_str)
    try:
        tables = load_tables_from_db(conn)
    finally:
        conn.close()
    return run_detectors(tables)


def get_detector_findings_for_db(db_path: Path | str) -> list[Finding]:
    """Run blind business detectors on database tables (cached by file mtime)."""
    p = Path(db_path).resolve()
    mtime = p.stat().st_mtime if p.exists() else 0.0
    return _get_cached_detector_findings(str(p), mtime)


def list_customers(
    db_path: Path | str,
    filter: str = "all",
    limit: int | None = None,
) -> pd.DataFrame:
    """Return customer profiles filtered by one of: all, churned, treated, control, eligible, detector_flagged."""
    conn = get_ro_connection(db_path)
    try:
        base_query = (
            "SELECT customer_id, signup_date, segment, channel, region, usage_pattern, marketing_opt_in "
            "FROM customer"
        )
        filter_lower = filter.strip().lower()

        if filter_lower == "all":
            sql = f"{base_query} ORDER BY customer_id"
            params: tuple[Any, ...] = ()
        elif filter_lower == "churned":
            sql = (
                f"{base_query} "
                "WHERE customer_id IN (SELECT customer_id FROM churn_outcome WHERE churned = 1) "
                "ORDER BY customer_id"
            )
            params = ()
        elif filter_lower == "treated":
            sql = (
                f"{base_query} "
                "WHERE customer_id IN (SELECT customer_id FROM campaign_contact WHERE experiment_group = 'TREATMENT') "
                "ORDER BY customer_id"
            )
            params = ()
        elif filter_lower == "control":
            sql = (
                f"{base_query} "
                "WHERE customer_id IN (SELECT customer_id FROM campaign_contact WHERE experiment_group = 'CONTROL') "
                "ORDER BY customer_id"
            )
            params = ()
        elif filter_lower == "eligible":
            sql = (
                f"{base_query} "
                "WHERE customer_id IN (SELECT DISTINCT customer_id FROM campaign_contact) "
                "ORDER BY customer_id"
            )
            params = ()
        elif filter_lower == "detector_flagged":
            findings = get_detector_findings_for_db(db_path)
            flagged_cids = sorted({_extract_customer_id(f) for f in findings if _extract_customer_id(f)})
            if not flagged_cids:
                return pd.DataFrame(
                    columns=["customer_id", "signup_date", "segment", "channel", "region", "usage_pattern", "marketing_opt_in"]
                )
            placeholders = ",".join("?" for _ in flagged_cids)
            sql = f"{base_query} WHERE customer_id IN ({placeholders}) ORDER BY customer_id"
            params = tuple(flagged_cids)
        else:
            raise ValueError(f"Unknown customer filter: {filter!r}")

        if limit is not None and limit > 0:
            sql += f" LIMIT {int(limit)}"

        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

    return df


def customer_360(
    db_path: Path | str,
    customer_id: str,
) -> dict[str, Any]:
    """Return Customer 360 view with subscriptions, usage, billing, support, risk, rules, campaign, events, findings."""
    cid = str(customer_id).strip()
    conn = get_ro_connection(db_path)
    try:
        # 1. Profile
        prof_df = pd.read_sql_query("SELECT * FROM customer WHERE customer_id = ?", conn, params=(cid,))
        profile = prof_df.iloc[0].to_dict() if not prof_df.empty else {}

        # 2. Subscriptions
        subs_df = pd.read_sql_query(
            "SELECT * FROM subscription WHERE customer_id = ? ORDER BY sequence_no ASC",
            conn,
            params=(cid,),
        )

        # 3. Monthly Usage
        usage_df = pd.read_sql_query(
            "SELECT u.* FROM usage_snapshot u "
            "JOIN subscription s ON u.subscription_id = s.subscription_id "
            "WHERE s.customer_id = ? ORDER BY u.snapshot_month ASC",
            conn,
            params=(cid,),
        )

        # 4. Billing Events
        billing_df = pd.read_sql_query(
            "SELECT b.* FROM billing_event b "
            "JOIN subscription s ON b.subscription_id = s.subscription_id "
            "WHERE s.customer_id = ? ORDER BY b.event_date ASC",
            conn,
            params=(cid,),
        )

        # 5. Support Cases
        support_df = pd.read_sql_query(
            "SELECT * FROM support_case WHERE customer_id = ? ORDER BY opened_at ASC",
            conn,
            params=(cid,),
        )

        # 6. Risk Score & Band
        risk_df = pd.read_sql_query(
            "SELECT * FROM risk_score WHERE customer_id = ? ORDER BY as_of_date DESC",
            conn,
            params=(cid,),
        )
        risk_info = risk_df.iloc[0].to_dict() if not risk_df.empty else {}

        # 7. Rule Evaluation
        rules_df = pd.read_sql_query(
            "SELECT r.*, e.rule_code, e.rule_type FROM rule_evaluation r "
            "JOIN eligibility_rule e ON r.rule_id = e.rule_id "
            "WHERE r.customer_id = ? ORDER BY r.rule_id ASC, r.offer_id ASC",
            conn,
            params=(cid,),
        )

        # 8. Campaign Contacts
        contacts_df = pd.read_sql_query(
            "SELECT * FROM campaign_contact WHERE customer_id = ? ORDER BY contact_id ASC",
            conn,
            params=(cid,),
        )

        # 9. Retention Outcomes
        ret_df = pd.read_sql_query(
            "SELECT r.* FROM retention_outcome r "
            "JOIN campaign_contact c ON r.contact_id = c.contact_id "
            "WHERE c.customer_id = ? ORDER BY r.retention_id ASC",
            conn,
            params=(cid,),
        )

        # 10. State Events timeline
        events_df = pd.read_sql_query(
            "SELECT * FROM state_event WHERE "
            "entity_id = ? "
            "OR entity_id IN (SELECT subscription_id FROM subscription WHERE customer_id = ?) "
            "OR entity_id IN (SELECT contact_id FROM campaign_contact WHERE customer_id = ?) "
            "ORDER BY event_ts ASC, event_id ASC",
            conn,
            params=(cid, cid, cid),
        )

        # 11. Detector Findings
        all_findings = get_detector_findings_for_db(db_path)
        customer_findings = [f for f in all_findings if _extract_customer_id(f) == cid]
    finally:
        conn.close()

    return {
        "customer_id": cid,
        "profile": profile,
        "subscriptions": subs_df,
        "monthly_usage": usage_df,
        "billing_events": billing_df,
        "support_cases": support_df,
        "risk_score": risk_info,
        "risk_df": risk_df,
        "rule_evaluation": rules_df,
        "campaign_contacts": contacts_df,
        "retention_outcomes": ret_df,
        "state_events": events_df,
        "detector_findings": customer_findings,
    }


def campaign_summary(db_path: Path | str) -> dict[str, Any]:
    """Return campaign summary statistics: eligible counts by stratum and offer, arm sizes, and cost exposure."""
    conn = get_ro_connection(db_path)
    try:
        # Offer catalog
        offers_df = pd.read_sql_query("SELECT * FROM offer ORDER BY offer_id ASC", conn)

        # Contacts with stratum and subscription price
        contact_query = (
            "SELECT c.contact_id, c.customer_id, c.offer_id, c.experiment_group, c.contact_status, "
            "c.assigned_at, c.stratum, s.monthly_price_cents, s.gross_margin_pct "
            "FROM campaign_contact c "
            "LEFT JOIN subscription s ON c.customer_id = s.customer_id "
            "AND s.start_date <= c.assigned_at AND (s.end_date IS NULL OR s.end_date >= c.assigned_at)"
        )
        contacts = pd.read_sql_query(contact_query, conn)

        # Eligible counts by stratum and offer
        counts_by_stratum = (
            contacts.groupby(["stratum", "experiment_group"])["customer_id"]
            .nunique()
            .unstack(fill_value=0)
            .reset_index()
        )

        counts_by_offer = (
            contacts.groupby(["offer_id", "experiment_group"])["customer_id"]
            .nunique()
            .unstack(fill_value=0)
            .reset_index()
        )

        arm_sizes = (
            contacts.groupby("experiment_group")["customer_id"]
            .nunique()
            .to_dict()
        )

        # Offer map
        offer_map: dict[str, dict[str, Any]] = {}
        for row in offers_df.itertuples(index=False):
            offer_map[row.offer_id] = {
                "offer_type": row.offer_type,
                "discount_pct": getattr(row, "discount_pct", None),
                "duration_months": getattr(row, "duration_months", None),
                "free_months": getattr(row, "free_months", None),
                "max_cost_share_of_margin": getattr(row, "max_cost_share_of_margin", 0.25),
            }

        # Cost exposure per offer: sum of ER-007 cost formula over assigned TREATMENT contacts
        cost_exposure_per_offer: dict[str, int] = {oid: 0 for oid in offer_map}
        treat_contacts = contacts[contacts["experiment_group"] == "TREATMENT"]

        for row in treat_contacts.itertuples(index=False):
            oid = str(row.offer_id)
            if oid in offer_map:
                ospec = offer_map[oid]
                price = int(row.monthly_price_cents) if pd.notna(row.monthly_price_cents) else 0
                if ospec["offer_type"] == "PERCENT_DISCOUNT":
                    disc = float(ospec["discount_pct"]) if ospec["discount_pct"] is not None else 0.0
                    dur = int(ospec["duration_months"]) if ospec["duration_months"] is not None else 0
                    cost = int(round(disc * float(price) * dur))
                elif ospec["offer_type"] == "FREE_MONTH":
                    fm = int(ospec["free_months"]) if ospec["free_months"] is not None else 1
                    cost = int(round(fm * float(price)))
                else:
                    cost = 0
                cost_exposure_per_offer[oid] += cost

    finally:
        conn.close()

    return {
        "eligible_counts_by_stratum": counts_by_stratum,
        "eligible_counts_by_offer": counts_by_offer,
        "arm_sizes": arm_sizes,
        "offer_catalog": offers_df,
        "cost_exposure_per_offer": cost_exposure_per_offer,
        "contacts_sample": contacts,
    }


def load_report(data_dir: Path | str, name: str) -> Any | None:
    """Read JSON or Markdown report file from data_dir; return parsed JSON, text, or None if missing."""
    target_path = Path(data_dir) / name
    if not target_path.is_file():
        return None

    content = target_path.read_text(encoding="utf-8")
    if name.endswith(".json"):
        try:
            return json.loads(content)
        except Exception:
            return None
    return content
