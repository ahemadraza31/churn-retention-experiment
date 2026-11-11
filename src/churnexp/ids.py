"""Deterministic ID generators, regex patterns, and parse helpers for churnexp."""

import re
from typing import Any

ID_PATTERNS: dict[str, re.Pattern[str]] = {
    "customer": re.compile(r"^CUS-\d{6}$"),
    "subscription": re.compile(r"^SUB-CUS-\d{6}-\d{2}$"),
    "snapshot": re.compile(r"^SNAP-SUB-CUS-\d{6}-\d{2}-\d{4}-\d{2}$"),
    "offer": re.compile(r"^OFF-\d{4}-\d{6}$"),
    "churn_outcome": re.compile(r"^CHURN-CUS-\d{6}-\d{4}$"),
    "billing_event": re.compile(r"^BILL-SUB-CUS-\d{6}-\d{2}-\d{6}-\d{2}$"),
    "support_case": re.compile(r"^CASE-CUS-\d{6}-\d{4}$"),
    "campaign_contact": re.compile(r"^CMP-CUS-\d{6}-\d{4}-W\d{2}$"),
    "retention_outcome": re.compile(r"^RET-CMP-CUS-\d{6}-\d{4}-W\d{2}$"),
    "state_event": re.compile(r"^EVT-\d{9}$"),
    "eligibility_rule": re.compile(r"^ER-\d{3}$"),
}


def is_valid_id(kind: str, value: str) -> bool:
    """Check if value matches the registered regex for the given ID kind."""
    pattern = ID_PATTERNS.get(kind)
    if pattern is None:
        raise ValueError(f"Unknown ID kind: {kind!r}")
    if not isinstance(value, str):
        return False
    return pattern.match(value) is not None


def customer_id(n: int) -> str:
    """Format customer ID: CUS-000001 (1 to 999999)."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError(f"n must be an integer, got {type(n).__name__}")
    if not (1 <= n <= 999999):
        raise ValueError(f"Customer index out of range [1, 999999]: {n}")
    return f"CUS-{n:06d}"


def parse_customer_id(cid: str) -> int:
    """Parse customer ID and return integer index."""
    if not is_valid_id("customer", cid):
        raise ValueError(f"Invalid customer ID: {cid!r}")
    return int(cid[4:])


def subscription_id(cust_id: str, seq: int) -> str:
    """Format subscription ID: SUB-CUS-000001-01 (seq 1 to 99)."""
    if not is_valid_id("customer", cust_id):
        raise ValueError(f"Invalid customer ID: {cust_id!r}")
    if not isinstance(seq, int) or isinstance(seq, bool):
        raise ValueError(f"seq must be an integer, got {type(seq).__name__}")
    if not (1 <= seq <= 99):
        raise ValueError(f"Subscription sequence out of range [1, 99]: {seq}")
    return f"SUB-{cust_id}-{seq:02d}"


def parse_subscription_id(sid: str) -> tuple[str, int]:
    """Parse subscription ID into (customer_id, sequence_no)."""
    if not is_valid_id("subscription", sid):
        raise ValueError(f"Invalid subscription ID: {sid!r}")
    # SUB-CUS-000001-01
    parts = sid.split("-")
    cid = f"{parts[1]}-{parts[2]}"
    seq = int(parts[3])
    return cid, seq


def snapshot_id(sub_id: str, year: int, month: int) -> str:
    """Format usage snapshot ID: SNAP-SUB-CUS-000001-01-2026-01."""
    if not is_valid_id("subscription", sub_id):
        raise ValueError(f"Invalid subscription ID: {sub_id!r}")
    if not isinstance(year, int) or isinstance(year, bool) or not (2000 <= year <= 2099):
        raise ValueError(f"Year out of range [2000, 2099]: {year}")
    if not isinstance(month, int) or isinstance(month, bool) or not (1 <= month <= 12):
        raise ValueError(f"Month out of range [1, 12]: {month}")
    return f"SNAP-{sub_id}-{year:04d}-{month:02d}"


def offer_id(year: int, n: int) -> str:
    """Format offer ID: OFF-2026-000001 (n 1 to 999999)."""
    if not isinstance(year, int) or isinstance(year, bool) or not (2000 <= year <= 2099):
        raise ValueError(f"Year out of range [2000, 2099]: {year}")
    if not isinstance(n, int) or isinstance(n, bool) or not (1 <= n <= 999999):
        raise ValueError(f"Offer index out of range [1, 999999]: {n}")
    return f"OFF-{year:04d}-{n:06d}"


def churn_outcome_id(cust_id: str, year: int) -> str:
    """Format churn outcome ID: CHURN-CUS-000001-2026."""
    if not is_valid_id("customer", cust_id):
        raise ValueError(f"Invalid customer ID: {cust_id!r}")
    if not isinstance(year, int) or isinstance(year, bool) or not (2000 <= year <= 2099):
        raise ValueError(f"Year out of range [2000, 2099]: {year}")
    return f"CHURN-{cust_id}-{year:04d}"


def billing_event_id(sub_id: str, year: int, month: int, seq: int) -> str:
    """Format billing event ID: BILL-SUB-CUS-000001-01-202601-01 (seq 1 to 99)."""
    if not is_valid_id("subscription", sub_id):
        raise ValueError(f"Invalid subscription ID: {sub_id!r}")
    if not isinstance(year, int) or isinstance(year, bool) or not (2000 <= year <= 2099):
        raise ValueError(f"Year out of range [2000, 2099]: {year}")
    if not isinstance(month, int) or isinstance(month, bool) or not (1 <= month <= 12):
        raise ValueError(f"Month out of range [1, 12]: {month}")
    if not isinstance(seq, int) or isinstance(seq, bool) or not (1 <= seq <= 99):
        raise ValueError(f"Billing event sequence out of range [1, 99]: {seq}")
    return f"BILL-{sub_id}-{year:04d}{month:02d}-{seq:02d}"


def support_case_id(cust_id: str, n: int) -> str:
    """Format support case ID: CASE-CUS-000001-0001 (n 1 to 9999)."""
    if not is_valid_id("customer", cust_id):
        raise ValueError(f"Invalid customer ID: {cust_id!r}")
    if not isinstance(n, int) or isinstance(n, bool) or not (1 <= n <= 9999):
        raise ValueError(f"Case index out of range [1, 9999]: {n}")
    return f"CASE-{cust_id}-{n:04d}"


def campaign_contact_id(cust_id: str, year: int, wave: int | str) -> str:
    """Format campaign contact ID: CMP-CUS-000001-2026-W01."""
    if not is_valid_id("customer", cust_id):
        raise ValueError(f"Invalid customer ID: {cust_id!r}")
    if not isinstance(year, int) or isinstance(year, bool) or not (2000 <= year <= 2099):
        raise ValueError(f"Year out of range [2000, 2099]: {year}")

    if isinstance(wave, str):
        if wave.startswith("W") and wave[1:].isdigit():
            wave_num = int(wave[1:])
        elif wave.isdigit():
            wave_num = int(wave)
        else:
            raise ValueError(f"Invalid wave format: {wave!r}")
    elif isinstance(wave, int) and not isinstance(wave, bool):
        wave_num = wave
    else:
        raise ValueError(f"wave must be int or str, got {type(wave).__name__}")

    if not (1 <= wave_num <= 99):
        raise ValueError(f"Wave number out of range [1, 99]: {wave_num}")

    return f"CMP-{cust_id}-{year:04d}-W{wave_num:02d}"


def retention_outcome_id(contact_id: str) -> str:
    """Format retention outcome ID: RET-CMP-CUS-000001-2026-W01."""
    if not is_valid_id("campaign_contact", contact_id):
        raise ValueError(f"Invalid campaign contact ID: {contact_id!r}")
    return f"RET-{contact_id}"


def state_event_id(n: int) -> str:
    """Format state event ID: EVT-000000001 (1 to 999999999)."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError(f"n must be an integer, got {type(n).__name__}")
    if not (1 <= n <= 999999999):
        raise ValueError(f"Event index out of range [1, 999999999]: {n}")
    return f"EVT-{n:09d}"


def eligibility_rule_id(n: int) -> str:
    """Format eligibility rule ID: ER-001 (1 to 999)."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError(f"n must be an integer, got {type(n).__name__}")
    if not (1 <= n <= 999):
        raise ValueError(f"Rule index out of range [1, 999]: {n}")
    return f"ER-{n:03d}"
