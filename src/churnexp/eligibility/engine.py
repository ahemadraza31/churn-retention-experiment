"""Eligibility engine producing `rule_evaluation` rows and eligible offer lists."""

from datetime import date, datetime
import json
from typing import Any, Mapping
import pandas as pd

from churnexp.eligibility.rules import (
    RuleEvalResult,
    _to_date,
    eval_er001_active_subscription,
    eval_er002_min_tenure,
    eval_er003_marketing_opt_in,
    eval_er004_no_unsettled_invoice,
    eval_er005_no_open_escalated_case,
    eval_er006_risk_band,
    eval_er007_offer_margin,
    extract_customer_rule_inputs,
)

RULE_EVALUATION_COLUMNS: list[str] = [
    "evaluation_id",
    "customer_id",
    "offer_id",
    "rule_id",
    "as_of_date",
    "passed",
    "observed_value",
    "threshold_value",
]


def format_rule_evaluation_id(seq: int) -> str:
    """Format rule_evaluation PK matching schema.sql GLOB: RE-000001."""
    if not (1 <= seq <= 999999):
        raise ValueError(f"rule_evaluation sequence out of range [1, 999999]: {seq}")
    return f"RE-{seq:06d}"


def _extract_rule_params(rules_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    params_by_rule: dict[str, dict[str, Any]] = {}
    for row in rules_df.itertuples(index=False):
        params_by_rule[str(row.rule_id)] = json.loads(str(row.parameter_json))
    return params_by_rule


def evaluate_eligibility(
    tables: Mapping[str, pd.DataFrame],
    risk_scores: pd.DataFrame,
    offers: pd.DataFrame,
    rules: pd.DataFrame,
    as_of: date | datetime | str,
) -> pd.DataFrame:
    """Evaluate ER-001..ER-007 for EVERY customer active at P (in `risk_scores`) with no short-circuit.

    Because `rule_evaluation.offer_id` is nullable in `schema.sql`, stores `offer_id = None`
    for customer-level rules `ER-001..ER-006` (6 rows/customer) and one row per offer for
    `ER-007` (3 rows/customer), totaling 9 `rule_evaluation` rows per scored customer.
    """
    if risk_scores.empty:
        return pd.DataFrame(columns=RULE_EVALUATION_COLUMNS)

    as_of_dt = _to_date(as_of)
    as_of_str = as_of_dt.isoformat()

    params_by_rule = _extract_rule_params(rules)
    min_tenure_days = int(params_by_rule.get("ER-002", {}).get("min_tenure_days", 90))
    grace_days = int(params_by_rule.get("ER-004", {}).get("grace_days", 7))
    allowed_bands = tuple(
        params_by_rule.get("ER-006", {}).get("allowed_bands", ["HIGH", "MEDIUM"])
    )
    expected_margin_months = int(
        params_by_rule.get("ER-007", {}).get("expected_margin_months", 6)
    )

    cust_inputs = extract_customer_rule_inputs(
        tables=tables,
        risk_scores=risk_scores,
        as_of=as_of_dt,
        grace_days=grace_days,
    )

    offers_sorted = offers.sort_values("offer_id", kind="mergesort")
    offer_specs = []
    for row in offers_sorted.itertuples(index=False):
        disc_val = getattr(row, "discount_pct", None)
        disc_pct = None if disc_val is None or pd.isna(disc_val) else float(disc_val)
        free_val = getattr(row, "free_months", None)
        free_m = None if free_val is None or pd.isna(free_val) else int(free_val)
        offer_specs.append(
            (
                str(row.offer_id),
                str(row.offer_type),
                disc_pct,
                free_m,
                int(row.duration_months),
                float(row.max_cost_share_of_margin),
            )
        )

    rows: list[dict[str, Any]] = []
    seq = 1
    for cid in sorted(cust_inputs.keys()):
        inp = cust_inputs[cid]
        evals: list[RuleEvalResult] = [
            eval_er001_active_subscription(inp["has_active_sub"]),
            eval_er002_min_tenure(inp["signup_date"], as_of_dt, min_tenure_days),
            eval_er003_marketing_opt_in(inp["marketing_opt_in"]),
            eval_er004_no_unsettled_invoice(inp["unsettled_old_invoice_count"]),
            eval_er005_no_open_escalated_case(inp["open_escalated_count"]),
            eval_er006_risk_band(inp["risk_band"], allowed_bands),
        ]
        for oid, otype, disc_pct, free_m, dur_m, max_share in offer_specs:
            evals.append(
                eval_er007_offer_margin(
                    offer_id=oid,
                    monthly_price_cents=inp["monthly_price_cents"],
                    gross_margin_pct=inp["gross_margin_pct"],
                    expected_margin_months=expected_margin_months,
                    offer_type=otype,
                    discount_pct=disc_pct,
                    free_months=free_m,
                    duration_months=dur_m,
                    max_cost_share_of_margin=max_share,
                )
            )

        for ev in evals:
            rows.append(
                {
                    "evaluation_id": format_rule_evaluation_id(seq),
                    "customer_id": cid,
                    "offer_id": ev.offer_id,
                    "rule_id": ev.rule_id,
                    "as_of_date": as_of_str,
                    "passed": int(ev.passed),
                    "observed_value": str(ev.observed_value),
                    "threshold_value": str(ev.threshold_value),
                }
            )
            seq += 1

    df = pd.DataFrame(rows, columns=RULE_EVALUATION_COLUMNS)
    return df.sort_values("evaluation_id", kind="mergesort").reset_index(drop=True)


def eligible_offers(
    customer_id: str,
    rule_evaluations: pd.DataFrame,
) -> list[str]:
    """Return sorted list of offer_ids passing ER-007 for `customer_id` (empty if ER-001..ER-006 failed)."""
    c_rows = rule_evaluations[rule_evaluations["customer_id"] == str(customer_id)]
    if c_rows.empty:
        return []
    cust_rules = c_rows[c_rows["rule_id"].isin(["ER-001", "ER-002", "ER-003", "ER-004", "ER-005", "ER-006"])]
    if len(cust_rules) < 6 or (cust_rules["passed"].astype(int) != 1).any():
        return []
    er007_rows = c_rows[(c_rows["rule_id"] == "ER-007") & (c_rows["passed"].astype(int) == 1)]
    return sorted(str(oid) for oid in er007_rows["offer_id"].dropna().tolist())


def get_all_eligible_customer_offers(
    rule_evaluations: pd.DataFrame,
) -> dict[str, list[str]]:
    """Compute mapping `customer_id -> sorted list of passing offer_ids` for all eligible customers."""
    if rule_evaluations.empty:
        return {}

    cust_rule_ids = {"ER-001", "ER-002", "ER-003", "ER-004", "ER-005", "ER-006"}
    passed_cust_rules_by_cid: dict[str, int] = {}
    passing_offers_by_cid: dict[str, list[str]] = {}

    for row in rule_evaluations.itertuples(index=False):
        cid = str(row.customer_id)
        rid = str(row.rule_id)
        passed = int(row.passed)
        if rid in cust_rule_ids:
            if passed == 1:
                passed_cust_rules_by_cid[cid] = passed_cust_rules_by_cid.get(cid, 0) + 1
        elif rid == "ER-007" and passed == 1:
            oid = getattr(row, "offer_id", None)
            if oid is not None and not pd.isna(oid) and str(oid) != "":
                passing_offers_by_cid.setdefault(cid, []).append(str(oid))

    eligible: dict[str, list[str]] = {}
    for cid, oids in sorted(passing_offers_by_cid.items()):
        if passed_cust_rules_by_cid.get(cid, 0) == 6 and oids:
            eligible[cid] = sorted(oids)
    return eligible

