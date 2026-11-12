"""Offer catalog and eligibility rule table builders from Config."""

import json
import pandas as pd

from churnexp import ids
from churnexp.config import Config

OFFER_COLUMNS: list[str] = [
    "offer_id",
    "offer_name",
    "offer_type",
    "discount_pct",
    "free_months",
    "duration_months",
    "max_cost_share_of_margin",
    "valid_from",
    "valid_to",
]

ELIGIBILITY_RULE_COLUMNS: list[str] = [
    "rule_id",
    "rule_code",
    "rule_type",
    "parameter_json",
    "version",
    "effective_from",
    "effective_to",
]

OFFER_ELIGIBILITY_RULE_COLUMNS: list[str] = [
    "offer_id",
    "rule_id",
]


def build_catalog(
    cfg: Config,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build `offer`, `eligibility_rule`, and `offer_eligibility_rule` DataFrames from config."""
    off_cfg = cfg.offers
    camp_cfg = cfg.campaign
    cycle_year = off_cfg.valid_from.year
    valid_from_str = off_cfg.valid_from.isoformat()
    valid_to_str = off_cfg.valid_to.isoformat()

    offer_rows = []
    for item in sorted(off_cfg.items, key=lambda x: x.number):
        oid = ids.offer_id(cycle_year, item.number)
        offer_rows.append(
            {
                "offer_id": oid,
                "offer_name": item.offer_name,
                "offer_type": item.offer_type,
                "discount_pct": item.discount_pct,
                "free_months": item.free_months,
                "duration_months": int(item.duration_months),
                "max_cost_share_of_margin": float(item.max_cost_share_of_margin),
                "valid_from": valid_from_str,
                "valid_to": valid_to_str,
            }
        )
    offer_df = (
        pd.DataFrame(offer_rows, columns=OFFER_COLUMNS)
        .sort_values("offer_id", kind="mergesort")
        .reset_index(drop=True)
    )

    rule_specs = [
        (
            1,
            "ACTIVE_SUBSCRIPTION",
            "SUBSCRIPTION",
            {"require_active": True},
        ),
        (
            2,
            "MIN_TENURE_DAYS",
            "TENURE",
            {"min_tenure_days": int(camp_cfg.min_tenure_days)},
        ),
        (
            3,
            "MARKETING_OPT_IN",
            "CONSENT",
            {"required_opt_in": 1},
        ),
        (
            4,
            "NO_UNSETTLED_INVOICE",
            "BILLING",
            {"grace_days": int(camp_cfg.unsettled_invoice_grace_days)},
        ),
        (
            5,
            "NO_OPEN_ESCALATED_SUPPORT_CASE",
            "SUPPORT",
            {"max_open_escalated": 0},
        ),
        (
            6,
            "ELIGIBLE_RISK_BAND",
            "RISK",
            {"allowed_bands": ["HIGH", "MEDIUM"]},
        ),
        (
            7,
            "OFFER_COST_WITHIN_MARGIN",
            "MARGIN",
            {"expected_margin_months": int(camp_cfg.expected_margin_months)},
        ),
    ]

    rule_rows = []
    for num, r_code, r_type, params in rule_specs:
        rid = ids.eligibility_rule_id(num)
        rule_rows.append(
            {
                "rule_id": rid,
                "rule_code": r_code,
                "rule_type": r_type,
                "parameter_json": json.dumps(params, sort_keys=True),
                "version": "1",
                "effective_from": valid_from_str,
                "effective_to": valid_to_str,
            }
        )
    eligibility_rule_df = (
        pd.DataFrame(rule_rows, columns=ELIGIBILITY_RULE_COLUMNS)
        .sort_values("rule_id", kind="mergesort")
        .reset_index(drop=True)
    )

    junction_rows = []
    for oid in offer_df["offer_id"].tolist():
        for rid in eligibility_rule_df["rule_id"].tolist():
            junction_rows.append({"offer_id": str(oid), "rule_id": str(rid)})

    offer_eligibility_rule_df = (
        pd.DataFrame(junction_rows, columns=OFFER_ELIGIBILITY_RULE_COLUMNS)
        .sort_values(["offer_id", "rule_id"], kind="mergesort")
        .reset_index(drop=True)
    )

    return offer_df, eligibility_rule_df, offer_eligibility_rule_df

