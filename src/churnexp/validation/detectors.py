"""Blind business-rule detectors operating strictly on observable database tables."""

from __future__ import annotations

import json
from typing import Any, Mapping
import pandas as pd

from churnexp.eligibility.rules import (
    RuleEvalResult,
    eval_er001_active_subscription,
    eval_er002_min_tenure,
    eval_er003_marketing_opt_in,
    eval_er004_no_unsettled_invoice,
    eval_er005_no_open_escalated_case,
    eval_er006_risk_band,
    eval_er007_offer_margin,
    extract_customer_rule_inputs,
)
from churnexp.validation.report import Finding, RuleSummary

DETECTOR_DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "DET-A-LABEL-BEFORE-PREDICTION",
        "CRITICAL",
        "Churn outcome has churned=1 with churn_date strictly before prediction_date",
    ),
    (
        "DET-B-INELIGIBLE-OFFER",
        "CRITICAL",
        "Campaign contact assigned to customer/offer failing one or more of ER-001..ER-007",
    ),
    (
        "DET-C-GROUP-LEAKAGE",
        "CRITICAL",
        "Customer assigned to both TREATMENT and CONTROL campaign contacts",
    ),
    (
        "DET-D-MULTI-ATTRIBUTION",
        "HIGH",
        "Customer has multiple retained outcomes attributed to distinct non-null offers",
    ),
]


def _is_missing_val(val: Any) -> bool:
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


def _parse_rule_thresholds(
    tables: Mapping[str, pd.DataFrame],
) -> tuple[int, int, tuple[str, ...], int]:
    min_tenure_days = 90
    grace_days = 7
    allowed_bands: tuple[str, ...] = ("HIGH", "MEDIUM")
    expected_margin_months = 6

    rules_df = tables.get("eligibility_rule")
    if rules_df is not None and not rules_df.empty:
        for row in rules_df.itertuples(index=False):
            rid = str(row.rule_id)
            p_raw = getattr(row, "parameter_json", "{}")
            try:
                params = json.loads(str(p_raw))
            except Exception:
                params = {}
            if rid == "ER-002" and "min_tenure_days" in params:
                min_tenure_days = int(params["min_tenure_days"])
            elif rid == "ER-004" and "grace_days" in params:
                grace_days = int(params["grace_days"])
            elif rid == "ER-006" and "allowed_bands" in params:
                allowed_bands = tuple(str(b) for b in params["allowed_bands"])
            elif rid == "ER-007" and "expected_margin_months" in params:
                expected_margin_months = int(params["expected_margin_months"])

    return min_tenure_days, grace_days, allowed_bands, expected_margin_months


def run_detectors(tables: Mapping[str, pd.DataFrame]) -> list[Finding]:
    """Run blind detectors DET-A through DET-D on observable tables and return sorted Findings."""
    findings: list[Finding] = []

    # ------------------------------------------------------------------
    # DET-A-LABEL-BEFORE-PREDICTION (CRITICAL)
    # ------------------------------------------------------------------
    churn_df = tables.get("churn_outcome")
    if churn_df is not None and not churn_df.empty:
        churn_sorted = churn_df.sort_values("churn_id", kind="mergesort")
        for row in churn_sorted.itertuples(index=False):
            if int(row.churned) != 1:
                continue
            c_val = getattr(row, "churn_date", None)
            if _is_missing_val(c_val):
                continue
            c_str = str(c_val)[:10]
            pred_str = str(row.prediction_date)[:10]
            # Strictly before prediction_date (churn_date == prediction_date is valid)
            if c_str < pred_str:
                ch_id = str(row.churn_id)
                cid = str(row.customer_id)
                findings.append(
                    Finding(
                        rule_id="DET-A-LABEL-BEFORE-PREDICTION",
                        severity="CRITICAL",
                        entity_type="churn_outcome",
                        entity_id=ch_id,
                        message=(
                            f"Churn outcome {ch_id} for customer {cid} has "
                            f"churn_date ({c_str}) < prediction_date ({pred_str})"
                        ),
                        evidence={
                            "customer_id": cid,
                            "churn_id": ch_id,
                            "cycle_year": int(row.cycle_year),
                            "prediction_date": pred_str,
                            "churn_date": c_str,
                        },
                    )
                )

    # ------------------------------------------------------------------
    # DET-B-INELIGIBLE-OFFER (CRITICAL)
    # ------------------------------------------------------------------
    cc_df = tables.get("campaign_contact")
    offers_df = tables.get("offer")
    rs_df = tables.get("risk_score")

    if (
        cc_df is not None
        and not cc_df.empty
        and offers_df is not None
        and not offers_df.empty
    ):
        min_tenure_days, grace_days, allowed_bands, expected_margin_months = (
            _parse_rule_thresholds(tables)
        )

        # Map offer_id -> spec
        offer_map: dict[str, dict[str, Any]] = {}
        for row in offers_df.itertuples(index=False):
            disc_val = getattr(row, "discount_pct", None)
            disc_pct = None if _is_missing_val(disc_val) else float(disc_val)
            free_val = getattr(row, "free_months", None)
            free_m = None if _is_missing_val(free_val) else int(free_val)
            offer_map[str(row.offer_id)] = {
                "offer_type": str(row.offer_type),
                "discount_pct": disc_pct,
                "free_months": free_m,
                "duration_months": int(row.duration_months),
                "max_cost_share_of_margin": float(row.max_cost_share_of_margin),
            }

        # Ensure every contacted customer appears in the risk_scores lookup frame
        if rs_df is not None and not rs_df.empty:
            aug_rs = rs_df[["customer_id", "band"]].copy()
        else:
            aug_rs = pd.DataFrame(columns=["customer_id", "band"])
        existing_rs_cids = set(aug_rs["customer_id"].astype(str))
        missing_rs_cids = sorted(
            set(cc_df["customer_id"].astype(str)) - existing_rs_cids
        )
        if missing_rs_cids:
            extra_rs = pd.DataFrame(
                [{"customer_id": c, "band": "UNSCORED"} for c in missing_rs_cids]
            )
            aug_rs = pd.concat([aug_rs, extra_rs], ignore_index=True)

        cc_sorted = cc_df.sort_values("contact_id", kind="mergesort")
        unique_assign_dates = sorted(
            set(cc_sorted["assigned_at"].astype(str).str.slice(0, 10))
        )
        inputs_by_date: dict[str, dict[str, dict[str, Any]]] = {}
        for a_date in unique_assign_dates:
            inputs_by_date[a_date] = extract_customer_rule_inputs(
                tables=tables,
                risk_scores=aug_rs,
                as_of=a_date,
                grace_days=grace_days,
            )

        for row in cc_sorted.itertuples(index=False):
            contact_id = str(row.contact_id)
            cid = str(row.customer_id)
            oid = str(row.offer_id)
            exp_group = str(row.experiment_group)
            a_date = str(row.assigned_at)[:10]

            inp = inputs_by_date[a_date].get(cid)
            if inp is None or oid not in offer_map:
                continue
            ospec = offer_map[oid]

            evals: list[RuleEvalResult] = [
                eval_er001_active_subscription(inp["has_active_sub"]),
                eval_er002_min_tenure(inp["signup_date"], a_date, min_tenure_days),
                eval_er003_marketing_opt_in(inp["marketing_opt_in"]),
                eval_er004_no_unsettled_invoice(inp["unsettled_old_invoice_count"]),
                eval_er005_no_open_escalated_case(inp["open_escalated_count"]),
                eval_er006_risk_band(inp["risk_band"], allowed_bands),
                eval_er007_offer_margin(
                    offer_id=oid,
                    monthly_price_cents=inp["monthly_price_cents"],
                    gross_margin_pct=inp["gross_margin_pct"],
                    expected_margin_months=expected_margin_months,
                    offer_type=ospec["offer_type"],
                    discount_pct=ospec["discount_pct"],
                    free_months=ospec["free_months"],
                    duration_months=ospec["duration_months"],
                    max_cost_share_of_margin=ospec["max_cost_share_of_margin"],
                ),
            ]
            failed = [ev for ev in evals if ev.passed == 0]
            if failed:
                failed_codes = ", ".join(ev.rule_id for ev in failed)
                findings.append(
                    Finding(
                        rule_id="DET-B-INELIGIBLE-OFFER",
                        severity="CRITICAL",
                        entity_type="campaign_contact",
                        entity_id=contact_id,
                        message=(
                            f"Campaign contact {contact_id} for customer {cid} "
                            f"(offer={oid}, group={exp_group}) failed eligibility: {failed_codes}"
                        ),
                        evidence={
                            "customer_id": cid,
                            "contact_id": contact_id,
                            "offer_id": oid,
                            "experiment_group": exp_group,
                            "assigned_date": a_date,
                            "failed_rules": [
                                {
                                    "rule_id": ev.rule_id,
                                    "observed_value": ev.observed_value,
                                    "threshold_value": ev.threshold_value,
                                }
                                for ev in failed
                            ],
                        },
                    )
                )

    # ------------------------------------------------------------------
    # DET-C-GROUP-LEAKAGE (CRITICAL)
    # ------------------------------------------------------------------
    if cc_df is not None and not cc_df.empty:
        cc_sorted = cc_df.sort_values("contact_id", kind="mergesort")
        for cid_key, grp in cc_sorted.groupby("customer_id", sort=True):
            cid = str(cid_key)
            groups_list = [str(g) for g in grp["experiment_group"].tolist()]
            groups_set = set(groups_list)
            if "TREATMENT" in groups_set and "CONTROL" in groups_set:
                contact_ids = [str(c) for c in grp["contact_id"].tolist()]
                findings.append(
                    Finding(
                        rule_id="DET-C-GROUP-LEAKAGE",
                        severity="CRITICAL",
                        entity_type="customer",
                        entity_id=cid,
                        message=(
                            f"Customer {cid} has campaign contacts in both "
                            f"TREATMENT and CONTROL groups: {contact_ids}"
                        ),
                        evidence={
                            "customer_id": cid,
                            "contact_ids": contact_ids,
                            "groups": groups_list,
                        },
                    )
                )

    # ------------------------------------------------------------------
    # DET-D-MULTI-ATTRIBUTION (HIGH)
    # ------------------------------------------------------------------
    ret_df = tables.get("retention_outcome")
    if ret_df is not None and not ret_df.empty:
        ret_sorted = ret_df.sort_values("retention_id", kind="mergesort")
        for cid_key, grp in ret_sorted.groupby("customer_id", sort=True):
            cid = str(cid_key)
            retained_attr_contacts: list[str] = []
            retained_attr_offers: list[str] = []
            for row in grp.itertuples(index=False):
                if int(row.retained) != 1:
                    continue
                attr_val = getattr(row, "attributed_offer_id", None)
                if _is_missing_val(attr_val):
                    continue
                retained_attr_contacts.append(str(row.contact_id))
                retained_attr_offers.append(str(attr_val))

            distinct_offers = sorted(set(retained_attr_offers))
            if len(retained_attr_offers) >= 2 and len(distinct_offers) >= 2:
                findings.append(
                    Finding(
                        rule_id="DET-D-MULTI-ATTRIBUTION",
                        severity="HIGH",
                        entity_type="customer",
                        entity_id=cid,
                        message=(
                            f"Customer {cid} has multiple retained outcomes with distinct "
                            f"attributed offers: {distinct_offers}"
                        ),
                        evidence={
                            "customer_id": cid,
                            "contact_ids": retained_attr_contacts,
                            "offers": retained_attr_offers,
                        },
                    )
                )

    return sorted(findings, key=lambda f: f.sort_key())


def summarize_detector_findings(findings: list[Finding]) -> list[RuleSummary]:
    """Build one RuleSummary line per blind detector in DETECTOR_DEFINITIONS order."""
    counts_by_rule: dict[str, int] = {}
    for f in findings:
        counts_by_rule[f.rule_id] = counts_by_rule.get(f.rule_id, 0) + 1

    summaries: list[RuleSummary] = []
    for rule_id, sev, desc in DETECTOR_DEFINITIONS:
        cnt = counts_by_rule.get(rule_id, 0)
        status = "PASS" if cnt == 0 else "FAIL"
        summaries.append(
            RuleSummary(
                rule_id=rule_id,
                severity=sev,
                status=status,
                finding_count=cnt,
                description=desc,
            )
        )
    return summaries

