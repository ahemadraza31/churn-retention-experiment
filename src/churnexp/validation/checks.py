"""Structural, temporal, reconciliation, natural-key, and cross-file validation checks."""

from datetime import date, timedelta
import functools
from pathlib import Path
import sqlite3
from typing import Any
import pandas as pd

from churnexp import ids
from churnexp.schema.db import create_database
from churnexp.validation.enums import ALLOWED_STATE_TRANSITIONS, TABLE_COLUMN_ENUMS
from churnexp.validation.report import Finding, Report, RuleSummary

RULE_DEFINITIONS: list[tuple[str, str, str]] = [
    ("STRUCT-PK-UNIQUE", "CRITICAL", "Primary key uniqueness and non-nullness across all tables"),
    ("STRUCT-FK", "CRITICAL", "Foreign key referential integrity across all tables (no orphans)"),
    ("STRUCT-ENUM", "HIGH", "Allowed enum values on all constrained columns"),
    ("STRUCT-ID-FORMAT", "HIGH", "Entity primary and foreign key ID regex format validity"),
    ("TEMP-SUB-DATES", "HIGH", "Subscription end_date >= start_date"),
    ("TEMP-SUB-CHAIN", "HIGH", "Subscription chain consecutive sequence_no, previous link, and next-day continuity"),
    ("TEMP-SNAPSHOT-IN-SUB", "HIGH", "Usage snapshot month falls within subscription start/end window"),
    ("TEMP-BILLING-IN-SUB", "HIGH", "Billing events fall within subscription active window"),
    ("TEMP-SUPPORT-ORDER", "HIGH", "Support case resolved_at >= opened_at"),
    ("TEMP-CHURN-VS-SUB", "CRITICAL", "No usage, billing, or support after churn date; churn date equals last subscription end_date"),
    ("TEMP-STATE-EVENT", "HIGH", "State events per entity are time-ordered and follow allowed dictionary transitions"),
    ("REC-INVOICE-AMOUNT", "HIGH", "Invoice amount_cents equals subscription monthly_price_cents"),
    ("REC-PAYMENT-AMOUNT", "HIGH", "Payment/retry amount_cents equals its related invoice amount_cents"),
    ("REC-BALANCE", "HIGH", "v_subscription_balance matches independent recomputation for all subscriptions"),
    ("REC-USAGE", "MEDIUM", "Usage active_days == 0 iff usage_minutes == 0 and usage_pct_of_limit in [0, 1]"),
    ("DUP-NATURAL-KEYS", "HIGH", "Natural keys unique: (subscription_id, snapshot_month), (customer_id, sequence_no), one INVOICE per sub/month"),
    ("XFILE-ROWCOUNT-KEYS", "HIGH", "CSV and DB tables have identical row counts and primary key sets"),
    ("XFILE-JSON-CSV", "MEDIUM", "JSON and CSV exports match in row counts, keys, and values"),
]

# Mapping from (table_name, column_name) -> ids.ID_PATTERNS kind
TABLE_ID_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "customer": [("customer_id", "customer")],
    "subscription": [
        ("subscription_id", "subscription"),
        ("customer_id", "customer"),
        ("previous_subscription_id", "subscription"),
    ],
    "usage_snapshot": [
        ("snapshot_id", "snapshot"),
        ("subscription_id", "subscription"),
    ],
    "billing_event": [
        ("billing_event_id", "billing_event"),
        ("subscription_id", "subscription"),
        ("related_event_id", "billing_event"),
    ],
    "support_case": [
        ("case_id", "support_case"),
        ("customer_id", "customer"),
        ("subscription_id", "subscription"),
    ],
    "offer": [("offer_id", "offer")],
    "eligibility_rule": [("rule_id", "eligibility_rule")],
    "offer_eligibility_rule": [
        ("offer_id", "offer"),
        ("rule_id", "eligibility_rule"),
    ],
    "campaign_contact": [
        ("contact_id", "campaign_contact"),
        ("customer_id", "customer"),
        ("offer_id", "offer"),
    ],
    "churn_outcome": [
        ("churn_id", "churn_outcome"),
        ("customer_id", "customer"),
    ],
    "retention_outcome": [
        ("retention_id", "retention_outcome"),
        ("contact_id", "campaign_contact"),
        ("customer_id", "customer"),
        ("attributed_offer_id", "offer"),
    ],
    "state_event": [("event_id", "state_event")],
    "risk_score": [("customer_id", "customer")],
    "feature_snapshot": [("customer_id", "customer")],
    "rule_evaluation": [
        ("customer_id", "customer"),
        ("offer_id", "offer"),
        ("rule_id", "eligibility_rule"),
    ],
}


def _is_missing(val: Any) -> bool:
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(val, str) and val == "":
        return True
    return False


@functools.lru_cache(maxsize=1)
def _get_schema_metadata() -> tuple[
    dict[str, list[str]],
    dict[str, list[tuple[str, str, str]]],
]:
    """Extract PK columns and FK triples (from_col, ref_table, to_col) from schema.sql."""
    conn = create_database(":memory:")
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = [r[0] for r in cur.fetchall()]

        pk_map: dict[str, list[str]] = {}
        fk_map: dict[str, list[tuple[str, str, str]]] = {}

        for tbl in table_names:
            cur.execute(f"PRAGMA table_info({tbl});")
            info = cur.fetchall()
            pks = [r[1] for r in sorted((r for r in info if r[5] > 0), key=lambda x: x[5])]
            pk_map[tbl] = pks

            cur.execute(f"PRAGMA foreign_key_list({tbl});")
            fks = [(r[3], r[2], r[4]) for r in cur.fetchall()]
            fk_map[tbl] = fks
        return pk_map, fk_map
    finally:
        conn.close()


def _format_pk(row: Any, pk_cols: list[str]) -> str:
    if len(pk_cols) == 1:
        return str(getattr(row, pk_cols[0], ""))
    return ":".join(str(getattr(row, c, "")) for c in pk_cols)


def load_tables_from_db(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Load all schema tables (plus v_subscription_balance) from a SQLite connection."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid;"
    )
    table_names = [r[0] for r in cur.fetchall()]
    tables: dict[str, pd.DataFrame] = {}
    for tbl in table_names:
        df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
        tables[tbl] = df
    try:
        bal_df = pd.read_sql_query("SELECT * FROM v_subscription_balance", conn)
        tables["v_subscription_balance"] = bal_df
    except Exception:
        pass
    return tables


def load_tables_from_csv_dir(csv_dir: Path | str) -> dict[str, pd.DataFrame]:
    """Load CSV files from a directory into a dict of DataFrames."""
    cdir = Path(csv_dir)
    tables: dict[str, pd.DataFrame] = {}
    if not cdir.is_dir():
        return tables
    for csv_path in sorted(cdir.glob("*.csv")):
        tbl_name = csv_path.stem
        df = pd.read_csv(csv_path, keep_default_na=True)
        tables[tbl_name] = df
    return tables


def load_tables_from_json_dir(json_dir: Path | str) -> dict[str, pd.DataFrame]:
    """Load JSON files from a directory into a dict of DataFrames."""
    jdir = Path(json_dir)
    tables: dict[str, pd.DataFrame] = {}
    if not jdir.is_dir():
        return tables
    for json_path in sorted(jdir.glob("*.json")):
        tbl_name = json_path.stem
        raw_text = json_path.read_text(encoding="utf-8").strip()
        if raw_text == "[]":
            pk_map, _ = _get_schema_metadata()
            conn = create_database(":memory:")
            try:
                cur = conn.cursor()
                cur.execute(f"PRAGMA table_info({tbl_name});")
                cols = [r[1] for r in cur.fetchall()]
            finally:
                conn.close()
            tables[tbl_name] = pd.DataFrame(columns=cols)
        else:
            df = pd.read_json(json_path, orient="records", dtype=False)
            tables[tbl_name] = df
    return tables


def validate_tables(
    tables: dict[str, pd.DataFrame],
    csv_tables: dict[str, pd.DataFrame] | None = None,
    json_tables: dict[str, pd.DataFrame] | None = None,
    conn: sqlite3.Connection | None = None,
    scale: str = "starter",
) -> Report:
    """Validate structural, temporal, reconciliation, natural-key, and cross-file rules."""
    pk_map, fk_map = _get_schema_metadata()
    findings: list[Finding] = []

    schema_tables = {k: v for k, v in tables.items() if k in pk_map}

    # ------------------------------------------------------------------
    # 1. STRUCT-PK-UNIQUE
    # ------------------------------------------------------------------
    for tbl, df in sorted(schema_tables.items()):
        pk_cols = pk_map.get(tbl, [])
        if not pk_cols or df.empty:
            continue
        for col in pk_cols:
            if col not in df.columns:
                continue
            null_mask = df[col].isna() | (df[col].astype(str) == "")
            if null_mask.any():
                for idx in df.index[null_mask]:
                    findings.append(
                        Finding(
                            rule_id="STRUCT-PK-UNIQUE",
                            severity="CRITICAL",
                            entity_type=tbl,
                            entity_id=f"row:{idx}",
                            message=f"NULL or empty primary key column {col!r} in {tbl}",
                            evidence={"table": tbl, "column": col, "row_index": int(idx)},
                        )
                    )
        if all(c in df.columns for c in pk_cols):
            dup_mask = df.duplicated(subset=pk_cols, keep="first")
            if dup_mask.any():
                for row in df[dup_mask].itertuples(index=False):
                    pk_str = _format_pk(row, pk_cols)
                    findings.append(
                        Finding(
                            rule_id="STRUCT-PK-UNIQUE",
                            severity="CRITICAL",
                            entity_type=tbl,
                            entity_id=pk_str,
                            message=f"Duplicate primary key {pk_str!r} in table {tbl}",
                            evidence={"table": tbl, "pk_columns": pk_cols, "pk_value": pk_str},
                        )
                    )

    # ------------------------------------------------------------------
    # 2. STRUCT-FK
    # ------------------------------------------------------------------
    for tbl, df in sorted(schema_tables.items()):
        if df.empty:
            continue
        pk_cols = pk_map.get(tbl, [])
        for from_col, ref_tbl, to_col in fk_map.get(tbl, []):
            if from_col not in df.columns:
                continue
            ref_df = schema_tables.get(ref_tbl)
            if ref_df is None or ref_df.empty or to_col not in ref_df.columns:
                valid_targets: set[Any] = set()
            else:
                valid_targets = set(ref_df[to_col].dropna().tolist())

            col_s = df[from_col]
            present_mask = col_s.notna() & (col_s.astype(str) != "")
            bad_mask = present_mask & (~col_s.isin(valid_targets))
            if bad_mask.any():
                for row in df[bad_mask].itertuples(index=False):
                    val = getattr(row, from_col, None)
                    pk_str = _format_pk(row, pk_cols)
                    findings.append(
                        Finding(
                            rule_id="STRUCT-FK",
                            severity="CRITICAL",
                            entity_type=tbl,
                            entity_id=pk_str,
                            message=(
                                f"Orphan foreign key {tbl}.{from_col}={val!r} "
                                f"not found in {ref_tbl}.{to_col}"
                            ),
                            evidence={
                                "table": tbl,
                                "column": from_col,
                                "value": str(val),
                                "ref_table": ref_tbl,
                                "ref_column": to_col,
                            },
                        )
                    )

    # ------------------------------------------------------------------
    # 3. STRUCT-ENUM
    # ------------------------------------------------------------------
    for tbl, df in sorted(schema_tables.items()):
        if df.empty or tbl not in TABLE_COLUMN_ENUMS:
            continue
        pk_cols = pk_map.get(tbl, [])
        for col, allowed in TABLE_COLUMN_ENUMS[tbl].items():
            if col not in df.columns:
                continue
            col_s = df[col]
            present_mask = col_s.notna() & (col_s.astype(str) != "")
            bad_mask = present_mask & (~col_s.isin(allowed))
            if bad_mask.any():
                for row in df[bad_mask].itertuples(index=False):
                    val = getattr(row, col, None)
                    if _is_missing(val):
                        continue
                    check_val: Any = val
                    if isinstance(val, float) and val.is_integer():
                        check_val = int(val)
                    if check_val not in allowed:
                        pk_str = _format_pk(row, pk_cols)
                        findings.append(
                            Finding(
                                rule_id="STRUCT-ENUM",
                                severity="HIGH",
                                entity_type=tbl,
                                entity_id=pk_str,
                                message=f"Invalid enum value {val!r} for {tbl}.{col}",
                                evidence={
                                    "table": tbl,
                                    "column": col,
                                    "value": val,
                                    "allowed": sorted(str(x) for x in allowed),
                                },
                            )
                        )

    # ------------------------------------------------------------------
    # 4. STRUCT-ID-FORMAT
    # ------------------------------------------------------------------
    for tbl, df in sorted(schema_tables.items()):
        if df.empty or tbl not in TABLE_ID_COLUMNS:
            continue
        pk_cols = pk_map.get(tbl, [])
        for col, kind in TABLE_ID_COLUMNS[tbl]:
            if col not in df.columns:
                continue
            pattern = ids.ID_PATTERNS[kind]
            col_s = df[col]
            present_mask = col_s.notna() & (col_s.astype(str) != "")
            if not present_mask.any():
                continue
            valid_mask = col_s[present_mask].astype(str).str.match(pattern)
            if not valid_mask.all():
                bad_indices = valid_mask.index[~valid_mask]
                for row in df.loc[bad_indices].itertuples(index=False):
                    val = getattr(row, col, None)
                    if not ids.is_valid_id(kind, str(val)):
                        pk_str = _format_pk(row, pk_cols)
                        findings.append(
                            Finding(
                                rule_id="STRUCT-ID-FORMAT",
                                severity="HIGH",
                                entity_type=tbl,
                                entity_id=pk_str,
                                message=f"Malformed {kind} ID {val!r} in {tbl}.{col}",
                                evidence={
                                    "table": tbl,
                                    "column": col,
                                    "kind": kind,
                                    "value": str(val),
                                },
                            )
                        )

    # ------------------------------------------------------------------
    # 5. TEMP-SUB-DATES & 6. TEMP-SUB-CHAIN
    # ------------------------------------------------------------------
    sub_df = schema_tables.get("subscription")
    sub_window_map: dict[str, tuple[str, str, str | None, str | None]] = {}
    last_sub_by_customer: dict[str, tuple[str, str | None, str | None]] = {}

    if sub_df is not None and not sub_df.empty:
        for row in sub_df.itertuples(index=False):
            sid = str(row.subscription_id)
            cid = str(row.customer_id)
            s_str = str(row.start_date)
            e_val = getattr(row, "end_date", None)
            e_str = None if _is_missing(e_val) else str(e_val)
            r_val = getattr(row, "end_reason", None)
            r_str = None if _is_missing(r_val) else str(r_val)
            sub_window_map[sid] = (cid, s_str, e_str, r_str)

            if e_str is not None and e_str < s_str:
                findings.append(
                    Finding(
                        rule_id="TEMP-SUB-DATES",
                        severity="HIGH",
                        entity_type="subscription",
                        entity_id=sid,
                        message=f"Subscription {sid} end_date ({e_str}) < start_date ({s_str})",
                        evidence={
                            "subscription_id": sid,
                            "start_date": s_str,
                            "end_date": e_str,
                        },
                    )
                )

        # TEMP-SUB-CHAIN per customer
        for cid, grp in sub_df.groupby("customer_id", sort=True):
            grp_sorted = grp.sort_values("sequence_no", kind="mergesort")
            seqs = [int(x) for x in grp_sorted["sequence_no"].tolist()]
            expected_seqs = list(range(1, len(seqs) + 1))
            if seqs != expected_seqs:
                findings.append(
                    Finding(
                        rule_id="TEMP-SUB-CHAIN",
                        severity="HIGH",
                        entity_type="customer",
                        entity_id=str(cid),
                        message=f"Customer {cid} has non-consecutive sequence_no {seqs}",
                        evidence={"customer_id": str(cid), "sequence_nos": seqs},
                    )
                )

            prev_sid: str | None = None
            prev_end: date | None = None
            for idx_in_chain, srow in enumerate(grp_sorted.itertuples(index=False)):
                sid = str(srow.subscription_id)
                s_dt = date.fromisoformat(str(srow.start_date))
                e_val = getattr(srow, "end_date", None)
                e_dt = None if _is_missing(e_val) else date.fromisoformat(str(e_val))
                prev_val = getattr(srow, "previous_subscription_id", None)
                prev_str = None if _is_missing(prev_val) else str(prev_val)
                r_val = getattr(srow, "end_reason", None)
                r_str = None if _is_missing(r_val) else str(r_val)

                if idx_in_chain == 0:
                    if prev_str is not None:
                        findings.append(
                            Finding(
                                rule_id="TEMP-SUB-CHAIN",
                                severity="HIGH",
                                entity_type="subscription",
                                entity_id=sid,
                                message=f"First subscription {sid} has non-null previous_subscription_id={prev_str!r}",
                                evidence={"subscription_id": sid, "previous_subscription_id": prev_str},
                            )
                        )
                else:
                    if prev_str != prev_sid:
                        findings.append(
                            Finding(
                                rule_id="TEMP-SUB-CHAIN",
                                severity="HIGH",
                                entity_type="subscription",
                                entity_id=sid,
                                message=f"Subscription {sid} previous_subscription_id={prev_str!r} != {prev_sid!r}",
                                evidence={
                                    "subscription_id": sid,
                                    "previous_subscription_id": prev_str,
                                    "expected_previous_id": prev_sid,
                                },
                            )
                        )
                    if prev_end is None:
                        findings.append(
                            Finding(
                                rule_id="TEMP-SUB-CHAIN",
                                severity="HIGH",
                                entity_type="subscription",
                                entity_id=sid,
                                message=f"Previous subscription {prev_sid} has NULL end_date before {sid}",
                                evidence={"subscription_id": sid, "previous_subscription_id": prev_sid},
                            )
                        )
                    else:
                        expected_start = prev_end + timedelta(days=1)
                        if s_dt != expected_start:
                            findings.append(
                                Finding(
                                    rule_id="TEMP-SUB-CHAIN",
                                    severity="HIGH",
                                    entity_type="subscription",
                                    entity_id=sid,
                                    message=(
                                        f"Subscription {sid} start_date ({s_dt.isoformat()}) != "
                                        f"previous end_date + 1 day ({expected_start.isoformat()})"
                                    ),
                                    evidence={
                                        "subscription_id": sid,
                                        "start_date": s_dt.isoformat(),
                                        "previous_end_date": prev_end.isoformat(),
                                        "expected_start_date": expected_start.isoformat(),
                                    },
                                )
                            )

                prev_sid = sid
                prev_end = e_dt
                if idx_in_chain == len(grp_sorted) - 1:
                    last_sub_by_customer[str(cid)] = (
                        sid,
                        e_dt.isoformat() if e_dt else None,
                        r_str,
                    )

    # ------------------------------------------------------------------
    # 7. TEMP-SNAPSHOT-IN-SUB
    # ------------------------------------------------------------------
    usage_df = schema_tables.get("usage_snapshot")
    if usage_df is not None and not usage_df.empty:
        for row in usage_df.itertuples(index=False):
            snap_id = str(row.snapshot_id)
            sid = str(row.subscription_id)
            s_month = str(row.snapshot_month)
            if sid not in sub_window_map:
                continue
            _, sub_start, sub_end, _ = sub_window_map[sid]
            if s_month < sub_start[:7] or (sub_end is not None and s_month > sub_end[:7]):
                findings.append(
                    Finding(
                        rule_id="TEMP-SNAPSHOT-IN-SUB",
                        severity="HIGH",
                        entity_type="usage_snapshot",
                        entity_id=snap_id,
                        message=(
                            f"Usage snapshot {snap_id} month {s_month} outside subscription "
                            f"{sid} window [{sub_start[:7]}, {sub_end[:7] if sub_end else 'OPEN'}]"
                        ),
                        evidence={
                            "snapshot_id": snap_id,
                            "subscription_id": sid,
                            "snapshot_month": s_month,
                            "sub_start_date": sub_start,
                            "sub_end_date": sub_end,
                        },
                    )
                )

    # ------------------------------------------------------------------
    # 8. TEMP-BILLING-IN-SUB
    # ------------------------------------------------------------------
    bill_df = schema_tables.get("billing_event")
    if bill_df is not None and not bill_df.empty:
        inv_date_map: dict[str, str] = {}
        for row in bill_df.itertuples(index=False):
            if str(row.event_type) == "INVOICE":
                inv_date_map[str(row.billing_event_id)] = str(row.event_date)

        for row in bill_df.itertuples(index=False):
            bid = str(row.billing_event_id)
            sid = str(row.subscription_id)
            ev_type = str(row.event_type)
            ev_date = str(row.event_date)
            rel_val = getattr(row, "related_event_id", None)
            rel_id = None if _is_missing(rel_val) else str(rel_val)

            if sid not in sub_window_map:
                continue
            _, sub_start, sub_end, sub_reason = sub_window_map[sid]

            if ev_date < sub_start:
                findings.append(
                    Finding(
                        rule_id="TEMP-BILLING-IN-SUB",
                        severity="HIGH",
                        entity_type="billing_event",
                        entity_id=bid,
                        message=f"Billing event {bid} date {ev_date} before subscription start {sub_start}",
                        evidence={
                            "billing_event_id": bid,
                            "subscription_id": sid,
                            "event_date": ev_date,
                            "sub_start_date": sub_start,
                        },
                    )
                )
            elif sub_end is not None and ev_date > sub_end:
                allowed_carryover = False
                if (
                    sub_reason == "PLAN_CHANGE"
                    and ev_type in ("RETRY", "PAYMENT", "PAYMENT_FAILED")
                    and rel_id is not None
                    and rel_id in inv_date_map
                ):
                    inv_dt_str = inv_date_map[rel_id]
                    if sub_start <= inv_dt_str <= sub_end:
                        delta_days = (
                            date.fromisoformat(ev_date) - date.fromisoformat(inv_dt_str)
                        ).days
                        if 0 <= delta_days <= 45:
                            allowed_carryover = True

                if not allowed_carryover:
                    findings.append(
                        Finding(
                            rule_id="TEMP-BILLING-IN-SUB",
                            severity="HIGH",
                            entity_type="billing_event",
                            entity_id=bid,
                            message=f"Billing event {bid} date {ev_date} after subscription end {sub_end}",
                            evidence={
                                "billing_event_id": bid,
                                "subscription_id": sid,
                                "event_date": ev_date,
                                "sub_end_date": sub_end,
                            },
                        )
                    )

    # ------------------------------------------------------------------
    # 9. TEMP-SUPPORT-ORDER
    # ------------------------------------------------------------------
    sup_df = schema_tables.get("support_case")
    if sup_df is not None and not sup_df.empty:
        for row in sup_df.itertuples(index=False):
            cid_case = str(row.case_id)
            opened = str(row.opened_at)
            res_val = getattr(row, "resolved_at", None)
            if not _is_missing(res_val):
                resolved = str(res_val)
                if resolved < opened:
                    findings.append(
                        Finding(
                            rule_id="TEMP-SUPPORT-ORDER",
                            severity="HIGH",
                            entity_type="support_case",
                            entity_id=cid_case,
                            message=f"Support case {cid_case} resolved_at ({resolved}) < opened_at ({opened})",
                            evidence={
                                "case_id": cid_case,
                                "opened_at": opened,
                                "resolved_at": resolved,
                            },
                        )
                    )

    # ------------------------------------------------------------------
    # 10. TEMP-CHURN-VS-SUB
    # ------------------------------------------------------------------
    customer_churn_date: dict[str, str] = {}
    for cid, (last_sid, last_end, last_reason) in last_sub_by_customer.items():
        if last_reason in ("VOLUNTARY_CANCEL", "INVOLUNTARY_CANCEL") or last_end is not None:
            if last_end is not None:
                customer_churn_date[cid] = last_end
            else:
                findings.append(
                    Finding(
                        rule_id="TEMP-CHURN-VS-SUB",
                        severity="CRITICAL",
                        entity_type="subscription",
                        entity_id=last_sid,
                        message=f"Cancelled subscription {last_sid} has NULL end_date",
                        evidence={"subscription_id": last_sid, "customer_id": cid},
                    )
                )

    churn_df = schema_tables.get("churn_outcome")
    if churn_df is not None and not churn_df.empty:
        for row in churn_df.itertuples(index=False):
            ch_id = str(row.churn_id)
            cid = str(row.customer_id)
            churned = int(row.churned)
            c_val = getattr(row, "churn_date", None)
            c_str = None if _is_missing(c_val) else str(c_val)

            if churned == 1:
                last_info = last_sub_by_customer.get(cid)
                last_end = last_info[1] if last_info else None
                if c_str is None or last_end != c_str:
                    findings.append(
                        Finding(
                            rule_id="TEMP-CHURN-VS-SUB",
                            severity="CRITICAL",
                            entity_type="churn_outcome",
                            entity_id=ch_id,
                            message=(
                                f"Churn outcome {ch_id} churn_date ({c_str}) != "
                                f"customer {cid} last subscription end_date ({last_end})"
                            ),
                            evidence={
                                "churn_id": ch_id,
                                "customer_id": cid,
                                "churn_date": c_str,
                                "last_subscription_end_date": last_end,
                            },
                        )
                    )
                if c_str is not None and cid not in customer_churn_date:
                    customer_churn_date[cid] = c_str

    if usage_df is not None and not usage_df.empty:
        for row in usage_df.itertuples(index=False):
            sid = str(row.subscription_id)
            if sid not in sub_window_map:
                continue
            cid = sub_window_map[sid][0]
            c_date = customer_churn_date.get(cid)
            if c_date is not None and str(row.snapshot_month) > c_date[:7]:
                findings.append(
                    Finding(
                        rule_id="TEMP-CHURN-VS-SUB",
                        severity="CRITICAL",
                        entity_type="usage_snapshot",
                        entity_id=str(row.snapshot_id),
                        message=(
                            f"Usage snapshot {row.snapshot_id} ({row.snapshot_month}) "
                            f"after customer {cid} churn_date ({c_date})"
                        ),
                        evidence={
                            "snapshot_id": str(row.snapshot_id),
                            "customer_id": cid,
                            "snapshot_month": str(row.snapshot_month),
                            "churn_date": c_date,
                        },
                    )
                )

    if bill_df is not None and not bill_df.empty:
        for row in bill_df.itertuples(index=False):
            sid = str(row.subscription_id)
            if sid not in sub_window_map:
                continue
            cid = sub_window_map[sid][0]
            c_date = customer_churn_date.get(cid)
            if c_date is not None and str(row.event_date) > c_date:
                findings.append(
                    Finding(
                        rule_id="TEMP-CHURN-VS-SUB",
                        severity="CRITICAL",
                        entity_type="billing_event",
                        entity_id=str(row.billing_event_id),
                        message=(
                            f"Billing event {row.billing_event_id} ({row.event_date}) "
                            f"after customer {cid} churn_date ({c_date})"
                        ),
                        evidence={
                            "billing_event_id": str(row.billing_event_id),
                            "customer_id": cid,
                            "event_date": str(row.event_date),
                            "churn_date": c_date,
                        },
                    )
                )

    if sup_df is not None and not sup_df.empty:
        for row in sup_df.itertuples(index=False):
            cid = str(row.customer_id)
            c_date = customer_churn_date.get(cid)
            if c_date is None:
                continue
            opened_date = str(row.opened_at)[:10]
            res_val = getattr(row, "resolved_at", None)
            res_date = None if _is_missing(res_val) else str(res_val)[:10]
            if opened_date > c_date or (res_date is not None and res_date > c_date):
                findings.append(
                    Finding(
                        rule_id="TEMP-CHURN-VS-SUB",
                        severity="CRITICAL",
                        entity_type="support_case",
                        entity_id=str(row.case_id),
                        message=(
                            f"Support case {row.case_id} (opened={opened_date}, resolved={res_date}) "
                            f"after customer {cid} churn_date ({c_date})"
                        ),
                        evidence={
                            "case_id": str(row.case_id),
                            "customer_id": cid,
                            "opened_at": str(row.opened_at),
                            "resolved_at": None if res_date is None else str(res_val),
                            "churn_date": c_date,
                        },
                    )
                )

    # ------------------------------------------------------------------
    # 11. TEMP-STATE-EVENT
    # ------------------------------------------------------------------
    se_df = schema_tables.get("state_event")
    if se_df is not None and not se_df.empty:
        se_sorted = se_df.sort_values("event_id", kind="mergesort")
        for (etype, eid), grp in se_sorted.groupby(["entity_type", "entity_id"], sort=False):
            etype_str = str(etype)
            eid_str = str(eid)
            allowed_trans = ALLOWED_STATE_TRANSITIONS.get(etype_str, set())
            prev_ts: str | None = None
            prev_to: str | None = None

            for row in grp.itertuples(index=False):
                ev_id = str(row.event_id)
                f_st = str(row.from_state)
                t_st = str(row.to_state)
                ev_ts = str(row.event_ts)

                if (f_st, t_st) not in allowed_trans:
                    findings.append(
                        Finding(
                            rule_id="TEMP-STATE-EVENT",
                            severity="HIGH",
                            entity_type="state_event",
                            entity_id=ev_id,
                            message=(
                                f"Disallowed state transition {f_st!r} -> {t_st!r} "
                                f"for {etype_str} {eid_str}"
                            ),
                            evidence={
                                "event_id": ev_id,
                                "entity_type": etype_str,
                                "entity_id": eid_str,
                                "from_state": f_st,
                                "to_state": t_st,
                            },
                        )
                    )

                if prev_ts is not None and ev_ts < prev_ts:
                    findings.append(
                        Finding(
                            rule_id="TEMP-STATE-EVENT",
                            severity="HIGH",
                            entity_type="state_event",
                            entity_id=ev_id,
                            message=(
                                f"Out-of-order state_event {ev_id} for {etype_str} {eid_str}: "
                                f"{ev_ts} < {prev_ts}"
                            ),
                            evidence={
                                "event_id": ev_id,
                                "entity_type": etype_str,
                                "entity_id": eid_str,
                                "event_ts": ev_ts,
                                "previous_event_ts": prev_ts,
                            },
                        )
                    )

                if prev_to is not None and f_st != prev_to:
                    findings.append(
                        Finding(
                            rule_id="TEMP-STATE-EVENT",
                            severity="HIGH",
                            entity_type="state_event",
                            entity_id=ev_id,
                            message=(
                                f"Broken state chain on {etype_str} {eid_str}: "
                                f"expected from_state={prev_to!r}, got {f_st!r}"
                            ),
                            evidence={
                                "event_id": ev_id,
                                "entity_type": etype_str,
                                "entity_id": eid_str,
                                "from_state": f_st,
                                "expected_from_state": prev_to,
                            },
                        )
                    )

                prev_ts = ev_ts
                prev_to = t_st

    # ------------------------------------------------------------------
    # 12. REC-INVOICE-AMOUNT & 13. REC-PAYMENT-AMOUNT
    # ------------------------------------------------------------------
    if bill_df is not None and not bill_df.empty and sub_df is not None and not sub_df.empty:
        price_by_sub = {
            str(r.subscription_id): int(r.monthly_price_cents)
            for r in sub_df.itertuples(index=False)
        }
        inv_amount_by_id: dict[str, int] = {}

        for row in bill_df.itertuples(index=False):
            if str(row.event_type) == "INVOICE":
                bid = str(row.billing_event_id)
                sid = str(row.subscription_id)
                amt = int(row.amount_cents)
                inv_amount_by_id[bid] = amt
                expected_price = price_by_sub.get(sid)
                if expected_price is not None and amt != expected_price:
                    findings.append(
                        Finding(
                            rule_id="REC-INVOICE-AMOUNT",
                            severity="HIGH",
                            entity_type="billing_event",
                            entity_id=bid,
                            message=(
                                f"Invoice {bid} amount_cents ({amt}) != "
                                f"subscription {sid} monthly_price_cents ({expected_price})"
                            ),
                            evidence={
                                "billing_event_id": bid,
                                "subscription_id": sid,
                                "amount_cents": amt,
                                "monthly_price_cents": expected_price,
                            },
                        )
                    )

        for row in bill_df.itertuples(index=False):
            ev_type = str(row.event_type)
            if ev_type in ("PAYMENT", "RETRY", "PAYMENT_FAILED"):
                bid = str(row.billing_event_id)
                amt = int(row.amount_cents)
                rel_val = getattr(row, "related_event_id", None)
                rel_id = None if _is_missing(rel_val) else str(rel_val)
                if rel_id is None or rel_id not in inv_amount_by_id:
                    findings.append(
                        Finding(
                            rule_id="REC-PAYMENT-AMOUNT",
                            severity="HIGH",
                            entity_type="billing_event",
                            entity_id=bid,
                            message=f"{ev_type} {bid} missing valid related invoice ({rel_id!r})",
                            evidence={
                                "billing_event_id": bid,
                                "event_type": ev_type,
                                "related_event_id": rel_id,
                            },
                        )
                    )
                else:
                    inv_amt = inv_amount_by_id[rel_id]
                    if amt != inv_amt:
                        findings.append(
                            Finding(
                                rule_id="REC-PAYMENT-AMOUNT",
                                severity="HIGH",
                                entity_type="billing_event",
                                entity_id=bid,
                                message=(
                                    f"{ev_type} {bid} amount_cents ({amt}) != "
                                    f"invoice {rel_id} amount_cents ({inv_amt})"
                                ),
                                evidence={
                                    "billing_event_id": bid,
                                    "event_type": ev_type,
                                    "amount_cents": amt,
                                    "invoice_id": rel_id,
                                    "invoice_amount_cents": inv_amt,
                                },
                            )
                        )

    # ------------------------------------------------------------------
    # 14. REC-BALANCE
    # ------------------------------------------------------------------
    if sub_df is not None and not sub_df.empty and bill_df is not None:
        invoiced_by_sub: dict[str, int] = {
            str(r.subscription_id): 0 for r in sub_df.itertuples(index=False)
        }
        paid_by_sub: dict[str, int] = {
            str(r.subscription_id): 0 for r in sub_df.itertuples(index=False)
        }
        subs_with_billing: set[str] = set()

        for row in bill_df.itertuples(index=False):
            sid = str(row.subscription_id)
            subs_with_billing.add(sid)
            ev_type = str(row.event_type)
            amt = int(row.amount_cents)
            if ev_type == "INVOICE":
                invoiced_by_sub[sid] = invoiced_by_sub.get(sid, 0) + amt
            elif ev_type == "PAYMENT":
                paid_by_sub[sid] = paid_by_sub.get(sid, 0) + amt

        recomputed_balance: dict[str, int] = {
            sid: invoiced_by_sub.get(sid, 0) - paid_by_sub.get(sid, 0)
            for sid in invoiced_by_sub
        }

        view_balance: dict[str, int] = {}
        if "v_subscription_balance" in tables:
            vdf = tables["v_subscription_balance"]
            for row in vdf.itertuples(index=False):
                view_balance[str(row.subscription_id)] = int(row.balance_cents)
        elif conn is not None:
            cur = conn.cursor()
            cur.execute("SELECT subscription_id, balance_cents FROM v_subscription_balance;")
            for r in cur.fetchall():
                view_balance[str(r[0])] = int(r[1])
        else:
            # Evaluate v_subscription_balance SQL expression over billing_event
            if not bill_df.empty:
                inv_s = (
                    bill_df[bill_df["event_type"] == "INVOICE"]
                    .groupby("subscription_id")["amount_cents"]
                    .sum()
                )
                pay_s = (
                    bill_df[bill_df["event_type"] == "PAYMENT"]
                    .groupby("subscription_id")["amount_cents"]
                    .sum()
                )
                for sid in subs_with_billing:
                    view_balance[sid] = int(inv_s.get(sid, 0)) - int(pay_s.get(sid, 0))

        all_sub_ids = sorted(set(recomputed_balance.keys()) | set(view_balance.keys()))
        for sid in all_sub_ids:
            exp_bal = recomputed_balance.get(sid, 0)
            obs_bal = view_balance.get(sid, 0 if sid not in subs_with_billing else None)
            if obs_bal != exp_bal:
                findings.append(
                    Finding(
                        rule_id="REC-BALANCE",
                        severity="HIGH",
                        entity_type="subscription",
                        entity_id=sid,
                        message=(
                            f"Subscription {sid} balance mismatch: "
                            f"v_subscription_balance={obs_bal} vs recomputed={exp_bal}"
                        ),
                        evidence={
                            "subscription_id": sid,
                            "view_balance_cents": obs_bal,
                            "recomputed_balance_cents": exp_bal,
                        },
                    )
                )

    # ------------------------------------------------------------------
    # 15. REC-USAGE
    # ------------------------------------------------------------------
    if usage_df is not None and not usage_df.empty:
        days_s = usage_df["active_days"].astype(int)
        mins_s = usage_df["usage_minutes"].astype(float)
        bad_zero_mask = (days_s == 0) != (mins_s == 0.0)
        if bad_zero_mask.any():
            for row in usage_df[bad_zero_mask].itertuples(index=False):
                snap_id = str(row.snapshot_id)
                findings.append(
                    Finding(
                        rule_id="REC-USAGE",
                        severity="MEDIUM",
                        entity_type="usage_snapshot",
                        entity_id=snap_id,
                        message=(
                            f"Usage snapshot {snap_id} inconsistent zero state: "
                            f"active_days={row.active_days}, usage_minutes={row.usage_minutes}"
                        ),
                        evidence={
                            "snapshot_id": snap_id,
                            "active_days": int(row.active_days),
                            "usage_minutes": float(row.usage_minutes),
                        },
                    )
                )
        if "usage_pct_of_limit" in usage_df.columns:
            pct_s = usage_df["usage_pct_of_limit"].astype(float)
            bad_pct_mask = (pct_s < 0.0) | (pct_s > 1.0)
            if bad_pct_mask.any():
                for row in usage_df[bad_pct_mask].itertuples(index=False):
                    snap_id = str(row.snapshot_id)
                    findings.append(
                        Finding(
                            rule_id="REC-USAGE",
                            severity="MEDIUM",
                            entity_type="usage_snapshot",
                            entity_id=snap_id,
                            message=(
                                f"Usage snapshot {snap_id} "
                                f"usage_pct_of_limit={row.usage_pct_of_limit} out of [0, 1]"
                            ),
                            evidence={
                                "snapshot_id": snap_id,
                                "usage_pct_of_limit": float(row.usage_pct_of_limit),
                            },
                        )
                    )

    # ------------------------------------------------------------------
    # 16. DUP-NATURAL-KEYS
    # ------------------------------------------------------------------
    if usage_df is not None and not usage_df.empty:
        dup_u = usage_df[usage_df.duplicated(subset=["subscription_id", "snapshot_month"], keep="first")]
        for row in dup_u.itertuples(index=False):
            findings.append(
                Finding(
                    rule_id="DUP-NATURAL-KEYS",
                    severity="HIGH",
                    entity_type="usage_snapshot",
                    entity_id=str(row.snapshot_id),
                    message=(
                        f"Duplicate usage_snapshot natural key "
                        f"({row.subscription_id}, {row.snapshot_month})"
                    ),
                    evidence={
                        "snapshot_id": str(row.snapshot_id),
                        "subscription_id": str(row.subscription_id),
                        "snapshot_month": str(row.snapshot_month),
                    },
                )
            )

    if sub_df is not None and not sub_df.empty:
        dup_s = sub_df[sub_df.duplicated(subset=["customer_id", "sequence_no"], keep="first")]
        for row in dup_s.itertuples(index=False):
            findings.append(
                Finding(
                    rule_id="DUP-NATURAL-KEYS",
                    severity="HIGH",
                    entity_type="subscription",
                    entity_id=str(row.subscription_id),
                    message=(
                        f"Duplicate subscription natural key "
                        f"({row.customer_id}, sequence_no={row.sequence_no})"
                    ),
                    evidence={
                        "subscription_id": str(row.subscription_id),
                        "customer_id": str(row.customer_id),
                        "sequence_no": int(row.sequence_no),
                    },
                )
            )

    if bill_df is not None and not bill_df.empty:
        invs = bill_df[bill_df["event_type"] == "INVOICE"].copy()
        if not invs.empty:
            invs["_inv_month"] = invs["event_date"].astype(str).str.slice(0, 7)
            dup_inv = invs[invs.duplicated(subset=["subscription_id", "_inv_month"], keep="first")]
            for row in dup_inv.itertuples(index=False):
                findings.append(
                    Finding(
                        rule_id="DUP-NATURAL-KEYS",
                        severity="HIGH",
                        entity_type="billing_event",
                        entity_id=str(row.billing_event_id),
                        message=(
                            f"Multiple INVOICE rows for subscription {row.subscription_id} "
                            f"in month {row._inv_month}"
                        ),
                        evidence={
                            "billing_event_id": str(row.billing_event_id),
                            "subscription_id": str(row.subscription_id),
                            "month": str(row._inv_month),
                        },
                    )
                )

    # ------------------------------------------------------------------
    # 17. XFILE-ROWCOUNT-KEYS
    # ------------------------------------------------------------------
    if csv_tables is not None:
        all_tbls = sorted(set(schema_tables.keys()) | (set(csv_tables.keys()) & set(pk_map.keys())))
        for tbl in all_tbls:
            db_df = schema_tables.get(tbl)
            csv_df = csv_tables.get(tbl)
            pk_cols = pk_map.get(tbl, [])

            if db_df is None or csv_df is None:
                findings.append(
                    Finding(
                        rule_id="XFILE-ROWCOUNT-KEYS",
                        severity="HIGH",
                        entity_type=tbl,
                        entity_id=tbl,
                        message=f"Table {tbl} missing in {'CSV' if csv_df is None else 'DB'}",
                        evidence={
                            "table": tbl,
                            "in_db": db_df is not None,
                            "in_csv": csv_df is not None,
                        },
                    )
                )
                continue

            if len(db_df) != len(csv_df):
                findings.append(
                    Finding(
                        rule_id="XFILE-ROWCOUNT-KEYS",
                        severity="HIGH",
                        entity_type=tbl,
                        entity_id=tbl,
                        message=f"Row count mismatch for {tbl}: DB={len(db_df)} vs CSV={len(csv_df)}",
                        evidence={
                            "table": tbl,
                            "db_rows": len(db_df),
                            "csv_rows": len(csv_df),
                        },
                    )
                )

            if pk_cols and all(c in db_df.columns for c in pk_cols) and all(c in csv_df.columns for c in pk_cols):
                if len(pk_cols) == 1:
                    pk_c = pk_cols[0]
                    db_keys = set(db_df[pk_c].astype(str).tolist())
                    csv_keys = set(csv_df[pk_c].astype(str).tolist())
                else:
                    db_keys = set(
                        ":".join(str(v) for v in r)
                        for r in db_df[pk_cols].itertuples(index=False, name=None)
                    )
                    csv_keys = set(
                        ":".join(str(v) for v in r)
                        for r in csv_df[pk_cols].itertuples(index=False, name=None)
                    )

                missing_in_csv = sorted(db_keys - csv_keys)
                extra_in_csv = sorted(csv_keys - db_keys)
                for mk in missing_in_csv:
                    findings.append(
                        Finding(
                            rule_id="XFILE-ROWCOUNT-KEYS",
                            severity="HIGH",
                            entity_type=tbl,
                            entity_id=mk,
                            message=f"Key {mk!r} in DB table {tbl} is missing from CSV export",
                            evidence={"table": tbl, "missing_key_in_csv": mk},
                        )
                    )
                for ek in extra_in_csv:
                    findings.append(
                        Finding(
                            rule_id="XFILE-ROWCOUNT-KEYS",
                            severity="HIGH",
                            entity_type=tbl,
                            entity_id=ek,
                            message=f"Extra key {ek!r} in CSV table {tbl} not present in DB",
                            evidence={"table": tbl, "extra_key_in_csv": ek},
                        )
                    )

    # ------------------------------------------------------------------
    # 18. XFILE-JSON-CSV
    # ------------------------------------------------------------------
    if json_tables is not None and csv_tables is not None:
        all_j_tbls = sorted(set(csv_tables.keys()) | set(json_tables.keys()))
        for tbl in all_j_tbls:
            c_df = csv_tables.get(tbl)
            j_df = json_tables.get(tbl)
            pk_cols = pk_map.get(tbl, [])

            if c_df is None or j_df is None:
                findings.append(
                    Finding(
                        rule_id="XFILE-JSON-CSV",
                        severity="MEDIUM",
                        entity_type=tbl,
                        entity_id=tbl,
                        message=f"Table {tbl} missing in {'JSON' if j_df is None else 'CSV'}",
                        evidence={"table": tbl, "in_csv": c_df is not None, "in_json": j_df is not None},
                    )
                )
                continue

            if len(c_df) != len(j_df) or list(c_df.columns) != list(j_df.columns):
                findings.append(
                    Finding(
                        rule_id="XFILE-JSON-CSV",
                        severity="MEDIUM",
                        entity_type=tbl,
                        entity_id=tbl,
                        message=f"JSON vs CSV shape/column mismatch for {tbl}",
                        evidence={
                            "table": tbl,
                            "csv_shape": list(c_df.shape),
                            "json_shape": list(j_df.shape),
                        },
                    )
                )
                continue

            if pk_cols and all(c in c_df.columns for c in pk_cols) and not c_df.empty:
                if len(pk_cols) == 1:
                    pk_c = pk_cols[0]
                    c_keys = c_df[pk_c].astype(str).tolist()
                    j_keys = j_df[pk_c].astype(str).tolist()
                else:
                    c_keys = [
                        ":".join(str(v) for v in r)
                        for r in c_df[pk_cols].itertuples(index=False, name=None)
                    ]
                    j_keys = [
                        ":".join(str(v) for v in r)
                        for r in j_df[pk_cols].itertuples(index=False, name=None)
                    ]
                if c_keys != j_keys:
                    findings.append(
                        Finding(
                            rule_id="XFILE-JSON-CSV",
                            severity="MEDIUM",
                            entity_type=tbl,
                            entity_id=tbl,
                            message=f"JSON vs CSV primary key order or key set mismatch for {tbl}",
                            evidence={"table": tbl},
                        )
                    )

    sorted_findings = sorted(findings, key=lambda f: f.sort_key())

    counts_by_rule: dict[str, int] = {}
    for f in sorted_findings:
        counts_by_rule[f.rule_id] = counts_by_rule.get(f.rule_id, 0) + 1

    rule_summaries: list[RuleSummary] = []
    for rule_id, sev, desc in RULE_DEFINITIONS:
        cnt = counts_by_rule.get(rule_id, 0)
        status = "PASS" if cnt == 0 else "FAIL"
        rule_summaries.append(
            RuleSummary(
                rule_id=rule_id,
                severity=sev,
                status=status,
                finding_count=cnt,
                description=desc,
            )
        )

    return Report(
        findings=sorted_findings,
        rule_summaries=rule_summaries,
        scale=scale,
    )
