"""Unit tests for deterministic ID generators, boundary validation, and parsing."""

import pytest

from churnexp.ids import (
    billing_event_id,
    campaign_contact_id,
    churn_outcome_id,
    customer_id,
    eligibility_rule_id,
    is_valid_id,
    offer_id,
    parse_customer_id,
    parse_subscription_id,
    retention_outcome_id,
    snapshot_id,
    state_event_id,
    subscription_id,
    support_case_id,
)


def test_exact_example_ids():
    """Verify all exact examples specified in the architecture."""
    cid = customer_id(1)
    assert cid == "CUS-000001"
    assert is_valid_id("customer", cid)

    sid = subscription_id(cid, 1)
    assert sid == "SUB-CUS-000001-01"
    assert is_valid_id("subscription", sid)

    snap_id = snapshot_id(sid, 2026, 1)
    assert snap_id == "SNAP-SUB-CUS-000001-01-2026-01"
    assert is_valid_id("snapshot", snap_id)

    off_id = offer_id(2026, 1)
    assert off_id == "OFF-2026-000001"
    assert is_valid_id("offer", off_id)

    churn_id = churn_outcome_id(cid, 2026)
    assert churn_id == "CHURN-CUS-000001-2026"
    assert is_valid_id("churn_outcome", churn_id)

    bill_id = billing_event_id(sid, 2026, 1, 1)
    assert bill_id == "BILL-SUB-CUS-000001-01-202601-01"
    assert is_valid_id("billing_event", bill_id)

    case_id = support_case_id(cid, 1)
    assert case_id == "CASE-CUS-000001-0001"
    assert is_valid_id("support_case", case_id)

    contact_id = campaign_contact_id(cid, 2026, 1)
    assert contact_id == "CMP-CUS-000001-2026-W01"
    assert is_valid_id("campaign_contact", contact_id)

    ret_id = retention_outcome_id(contact_id)
    assert ret_id == "RET-CMP-CUS-000001-2026-W01"
    assert is_valid_id("retention_outcome", ret_id)

    evt_id = state_event_id(1)
    assert evt_id == "EVT-000000001"
    assert is_valid_id("state_event", evt_id)

    rule_id = eligibility_rule_id(1)
    assert rule_id == "ER-001"
    assert is_valid_id("eligibility_rule", rule_id)


def test_customer_id_boundaries():
    """Customer ID valid in [1, 999999]; 0 and 1000000 rejected."""
    assert customer_id(1) == "CUS-000001"
    assert customer_id(999999) == "CUS-999999"

    with pytest.raises(ValueError):
        customer_id(0)

    with pytest.raises(ValueError):
        customer_id(-1)

    with pytest.raises(ValueError):
        customer_id(1000000)

    with pytest.raises(ValueError):
        customer_id("1")  # type: ignore

    with pytest.raises(ValueError):
        customer_id(True)  # type: ignore


def test_parse_helpers():
    """Verify parsing for customer and subscription IDs."""
    assert parse_customer_id("CUS-000001") == 1
    assert parse_customer_id("CUS-999999") == 999999
    with pytest.raises(ValueError):
        parse_customer_id("INVALID")

    assert parse_subscription_id("SUB-CUS-000001-01") == ("CUS-000001", 1)
    assert parse_subscription_id("SUB-CUS-000042-99") == ("CUS-000042", 99)
    with pytest.raises(ValueError):
        parse_subscription_id("SUB-INVALID")


def test_subscription_id_boundaries():
    """Subscription sequence valid in [1, 99]."""
    assert subscription_id("CUS-000001", 1) == "SUB-CUS-000001-01"
    assert subscription_id("CUS-000001", 99) == "SUB-CUS-000001-99"

    with pytest.raises(ValueError):
        subscription_id("CUS-000001", 0)

    with pytest.raises(ValueError):
        subscription_id("CUS-000001", 100)

    with pytest.raises(ValueError):
        subscription_id("BAD-ID", 1)


def test_other_id_boundaries():
    """Test boundary validation across remaining generators."""
    # Snapshot month
    with pytest.raises(ValueError):
        snapshot_id("SUB-CUS-000001-01", 2026, 0)
    with pytest.raises(ValueError):
        snapshot_id("SUB-CUS-000001-01", 2026, 13)

    # Offer
    assert offer_id(2026, 999999) == "OFF-2026-999999"
    with pytest.raises(ValueError):
        offer_id(2026, 0)
    with pytest.raises(ValueError):
        offer_id(2026, 1000000)

    # Support case
    assert support_case_id("CUS-000001", 9999) == "CASE-CUS-000001-9999"
    with pytest.raises(ValueError):
        support_case_id("CUS-000001", 0)
    with pytest.raises(ValueError):
        support_case_id("CUS-000001", 10000)

    # State event
    assert state_event_id(999999999) == "EVT-999999999"
    with pytest.raises(ValueError):
        state_event_id(0)
    with pytest.raises(ValueError):
        state_event_id(1000000000)

    # Eligibility rule
    assert eligibility_rule_id(999) == "ER-999"
    with pytest.raises(ValueError):
        eligibility_rule_id(0)
    with pytest.raises(ValueError):
        eligibility_rule_id(1000)


def test_id_determinism():
    """Multiple invocations produce strictly identical results."""
    for n in [1, 42, 999999]:
        assert customer_id(n) == customer_id(n)
        assert state_event_id(n) == state_event_id(n)
