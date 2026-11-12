"""Allowed enum values per table/column and valid state transitions for churnexp validation."""

from typing import Union

EnumValue = Union[str, int]

# Allowed enum sets for every CHECK (... IN (...)) column in schema.sql
TABLE_COLUMN_ENUMS: dict[str, dict[str, set[EnumValue]]] = {
    "customer": {
        "segment": {"CONSUMER", "SMB"},
        "channel": {"ORGANIC", "PAID", "PARTNER", "REFERRAL"},
        "usage_pattern": {"STEADY", "SEASONAL"},
        "marketing_opt_in": {0, 1},
    },
    "subscription": {
        "plan_tier": {"BASIC", "STANDARD", "PREMIUM"},
        "end_reason": {"PLAN_CHANGE", "VOLUNTARY_CANCEL", "INVOLUNTARY_CANCEL"},
    },
    "billing_event": {
        "event_type": {
            "INVOICE",
            "PAYMENT",
            "PAYMENT_FAILED",
            "RETRY",
            "REFUND",
            "CREDIT",
        },
    },
    "support_case": {
        "category": {"BILLING", "TECHNICAL", "CANCELLATION_INQUIRY", "GENERAL"},
        "severity": {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
        "escalated": {0, 1},
    },
    "offer": {
        "offer_type": {"PERCENT_DISCOUNT", "FREE_MONTH"},
    },
    "campaign_contact": {
        "experiment_group": {"TREATMENT", "CONTROL"},
        "contact_status": {"SENT", "WITHHELD", "DELIVERY_FAILED"},
        "responded": {0, 1},
        "redeemed": {0, 1},
    },
    "churn_outcome": {
        "churned": {0, 1},
        "churn_type": {"VOLUNTARY", "INVOLUNTARY"},
    },
    "retention_outcome": {
        "retained": {0, 1},
    },
    "state_event": {
        "entity_type": {"SUBSCRIPTION", "CAMPAIGN_CONTACT", "CUSTOMER"},
    },
    "risk_score": {
        "band": {"HIGH", "MEDIUM", "LOW"},
    },
    "feature_snapshot": {
        "plan_tier": {"BASIC", "STANDARD", "PREMIUM"},
        "plan_downgrade_6m": {0, 1},
        "segment": {"CONSUMER", "SMB"},
        "channel": {"ORGANIC", "PAID", "PARTNER", "REFERRAL"},
        "is_seasonal": {0, 1},
    },
    "rule_evaluation": {
        "passed": {0, 1},
    },
}

# Allowed state transitions per entity_type from docs/03_data_dictionary.md:
# CUSTOMER: INIT -> ACTIVE -> (CHURNED | INACTIVE)
# SUBSCRIPTION: INIT -> ACTIVE -> (CANCELLED | EXPIRED)
# CAMPAIGN_CONTACT: SENT -> (RESPONDED | REDEEMED | WITHHELD)
ALLOWED_STATE_TRANSITIONS: dict[str, set[tuple[str, str]]] = {
    "CUSTOMER": {
        ("INIT", "ACTIVE"),
        ("ACTIVE", "CHURNED"),
        ("ACTIVE", "INACTIVE"),
    },
    "SUBSCRIPTION": {
        ("INIT", "ACTIVE"),
        ("ACTIVE", "CANCELLED"),
        ("ACTIVE", "EXPIRED"),
    },
    "CAMPAIGN_CONTACT": {
        ("INIT", "SENT"),
        ("INIT", "WITHHELD"),
        ("INIT", "DELIVERY_FAILED"),
        ("SENT", "RESPONDED"),
        ("SENT", "REDEEMED"),
        ("SENT", "WITHHELD"),
        ("RESPONDED", "REDEEMED"),
    },
}

