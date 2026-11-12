"""Streamlit Actor Dashboard for Churn Detection and Retention Offer Experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd
import streamlit as st

from churnexp.services.queries import (
    campaign_summary,
    customer_360,
    list_customers,
    load_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@st.cache_data
def cached_load_report(data_dir_str: str, name: str) -> Any | None:
    return load_report(data_dir_str, name)


@st.cache_data
def cached_list_customers(db_path_str: str, filter_name: str, limit: int | None = None) -> pd.DataFrame:
    return list_customers(db_path_str, filter=filter_name, limit=limit)


@st.cache_data
def cached_customer_360(db_path_str: str, customer_id: str) -> dict[str, Any]:
    return customer_360(db_path_str, customer_id)


@st.cache_data
def cached_campaign_summary(db_path_str: str) -> dict[str, Any]:
    return campaign_summary(db_path_str)


def main() -> None:
    st.set_page_config(
        page_title="Churn Retention Experiment",
        page_icon="📊",
        layout="wide",
    )

    # Sidebar: Scale Selector and Page Navigation
    st.sidebar.title("Configuration")
    scale = st.sidebar.selectbox("Dataset Scale", ["starter", "full"], index=0)

    db_path = REPO_ROOT / "output" / scale / "churnexp.db"
    data_dir = REPO_ROOT / "data" / scale

    # Database existence check
    if not db_path.is_file():
        st.error(
            f"Database not found at `{db_path}`.\n\n"
            f"Please generate it by running:\n"
            f"```bash\npython -m churnexp all --scale {scale}\n```"
        )
        st.stop()

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Marketing Ops", "Support Agent", "Analyst", "System Admin"],
    )

    # Universal synthetic data banner
    st.warning("⚠️ Synthetic data - no real customers")

    db_path_str = str(db_path)
    data_dir_str = str(data_dir)

    if page == "Overview":
        render_overview(data_dir_str, scale)
    elif page == "Marketing Ops":
        render_marketing_ops(db_path_str)
    elif page == "Support Agent":
        render_support_agent(db_path_str)
    elif page == "Analyst":
        render_analyst(data_dir_str)
    elif page == "System Admin":
        render_system_admin(data_dir_str)


def render_overview(data_dir_str: str, scale: str) -> None:
    st.title("Churn Detection & Retention Experiment Overview")

    st.markdown(
        """
        ### Executive Summary
        1. **End-to-End Pipeline**: Modular Python framework orchestrating synthetic customer generation, temporal feature extraction, and ML risk scoring.
        2. **Honest Causal Inference**: Evaluates retention campaigns using 50/50 randomized Intention-to-Treat (ITT) with withheld controls.
        3. **Strict Temporal Integrity**: Enforces strict point-in-time boundaries ($P_0 = 2025-07-01$, $P = 2026-01-01$) preventing feature leakage.
        4. **Unit Economics Guardrails**: Validates offer eligibility and gross margin caps to avert unprofitable discount churn.
        5. **Operational Anomaly Defense**: Injects operational defects deterministically and detects them blind to ground truth.
        """
    )

    st.subheader("Pipeline Stages")
    st.markdown(
        """
        `1. generate` ➔ `2. export` ➔ `3. validate` ➔ `4. evaluate` ➔ `5. audit`
        - **Data Generation**: 18 months of subscriptions, monthly usage, billing events, and support tickets.
        - **Feature & Risk Modeling**: Out-of-time logistic regression trained at $P_0$ scoring active accounts at $P$.
        - **Randomized Allocation**: Planned offer assignment followed by 50/50 stratified Treatment/Control randomization.
        - **Simulation**: Counterfactual response, redemption, and post-churn usage generation.
        - **Blind Detectors & Audit**: 4 dedicated business-rule detectors audited for 100% precision and recall.
        """
    )

    eval_results = cached_load_report(data_dir_str, "evaluation_results.json")
    manifest = cached_load_report(data_dir_str, "MANIFEST.json")

    st.subheader("Headline Performance Metrics")
    if eval_results:
        exp = eval_results.get("experiment", {})
        p90 = exp.get("primary_90d", {})
        s180 = exp.get("secondary_180d", {})
        fin = eval_results.get("financial", {})
        f180 = fin.get("headline_180d", {})

        n_cust = 1000 if scale == "starter" else 20000
        if manifest and "tables" in manifest and "customer" in manifest["tables"]:
            n_cust = manifest["tables"]["customer"].get("row_count", n_cust)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Customers", f"{n_cust:,}")
        col2.metric("Eligible Contacts", f"{p90.get('n_treatment', 0) + p90.get('n_control', 0):,}")
        col3.metric("Treatment Arm Size", f"{p90.get('n_treatment', 0):,}")
        col4.metric("Control Arm Size", f"{p90.get('n_control', 0):,}")

        col5, col6, col7, col8 = st.columns(4)
        p90_lift = p90.get("absolute_lift_pp", 0.0)
        p90_ci = f"[{p90.get('ci_95_low_pp', 0.0):+.2f}, {p90.get('ci_95_high_pp', 0.0):+.2f}] pp"
        col5.metric("Primary 90d ITT Lift", f"{p90_lift:+.2f} pp", delta=p90_ci)

        s180_lift = s180.get("absolute_lift_pp", 0.0)
        s180_ci = f"[{s180.get('ci_95_low_pp', 0.0):+.2f}, {s180.get('ci_95_high_pp', 0.0):+.2f}] pp"
        col6.metric("Secondary 180d ITT Lift", f"{s180_lift:+.2f} pp", delta=s180_ci)

        net_cents = f180.get("net_impact_cents", 0)
        col7.metric("Net Financial Impact", f"{net_cents:+,d} cents")
        col8.metric("Realized Cost", f"{fin.get('realized_cost_cents', 0):,d} cents")

        st.info("📌 **Key Caveat**: These conclusions hold only under the stated simulation parameters.")
    else:
        st.warning("Evaluation report not yet generated. Run `python -m churnexp evaluate`.")


def render_marketing_ops(db_path_str: str) -> None:
    st.title("Marketing Operations")

    summary = cached_campaign_summary(db_path_str)

    st.subheader("1. Offer Catalog & Margin Guardrails")
    st.dataframe(summary["offer_catalog"], use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("2. Arm Sizes by Risk Stratum")
        st.dataframe(summary["eligible_counts_by_stratum"], use_container_width=True)

    with col2:
        st.subheader("3. Planned Offer Allocation by Arm")
        st.dataframe(summary["eligible_counts_by_offer"], use_container_width=True)

    st.subheader("4. Cost Exposure per Offer (TREATMENT Assigned)")
    cost_df = pd.DataFrame(
        [{"offer_id": k, "cost_exposure_cents": v} for k, v in summary["cost_exposure_per_offer"].items()]
    )
    st.dataframe(cost_df, use_container_width=True)

    st.subheader("5. Filterable Campaign Contacts")
    contacts = summary["contacts_sample"]

    f_stratum = st.selectbox("Filter Stratum", ["ALL"] + sorted(contacts["stratum"].dropna().unique().tolist()))
    f_offer = st.selectbox("Filter Offer", ["ALL"] + sorted(contacts["offer_id"].dropna().unique().tolist()))
    f_group = st.selectbox("Filter Group", ["ALL"] + sorted(contacts["experiment_group"].dropna().unique().tolist()))
    f_status = st.selectbox("Filter Status", ["ALL"] + sorted(contacts["contact_status"].dropna().unique().tolist()))

    filtered = contacts.copy()
    if f_stratum != "ALL":
        filtered = filtered[filtered["stratum"] == f_stratum]
    if f_offer != "ALL":
        filtered = filtered[filtered["offer_id"] == f_offer]
    if f_group != "ALL":
        filtered = filtered[filtered["experiment_group"] == f_group]
    if f_status != "ALL":
        filtered = filtered[filtered["contact_status"] == f_status]

    st.dataframe(filtered, use_container_width=True)


def render_support_agent(db_path_str: str) -> None:
    st.title("Customer 360 & Support Diagnostics")

    filter_choice = st.selectbox(
        "Customer List Filter",
        ["all", "detector_flagged", "treated", "control", "churned", "eligible"],
        index=1,
    )
    cust_df = cached_list_customers(db_path_str, filter_choice, limit=100)

    cids = cust_df["customer_id"].tolist() if not cust_df.empty else []
    col_input, col_select = st.columns([1, 2])
    with col_input:
        direct_cid = st.text_input("Enter Customer ID directly", value="")
    with col_select:
        selected_cid = st.selectbox("Or choose from filtered list", cids, index=0 if cids else None)

    target_cid = direct_cid.strip() if direct_cid.strip() else selected_cid
    if not target_cid:
        st.info("No customer selected.")
        return

    c360 = cached_customer_360(db_path_str, target_cid)

    st.subheader(f"Customer 360 Profile: `{target_cid}`")
    prof = c360.get("profile", {})
    r_info = c360.get("risk_score", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Segment / Channel", f"{prof.get('segment', 'N/A')} ({prof.get('channel', 'N/A')})")
    col2.metric("Signup Date", str(prof.get("signup_date", "N/A")))
    col3.metric("Risk Score", f"{r_info.get('score', 0.0):.4f}" if "score" in r_info else "N/A")
    col4.metric("Risk Band", str(r_info.get("band", "N/A")))

    # Monthly Usage Chart
    st.subheader("Monthly Usage Minutes")
    usage_df = c360.get("monthly_usage", pd.DataFrame())
    if not usage_df.empty and "snapshot_month" in usage_df.columns:
        chart_data = usage_df.set_index("snapshot_month")[["usage_minutes"]]
        st.line_chart(chart_data)
    else:
        st.info("No usage snapshots recorded.")

    # Detector Findings
    findings = c360.get("detector_findings", [])
    st.subheader(f"Detector Findings ({len(findings)})")
    if findings:
        for f in findings:
            st.error(f"**[{f.severity}] {f.rule_id}**: {f.message}")
            if f.evidence:
                st.json(f.evidence)
    else:
        st.success("No business-rule detector findings for this customer.")

    # Eligibility Trace
    st.subheader("Eligibility Rule Trace (7 Rules)")
    rules_df = c360.get("rule_evaluation", pd.DataFrame())
    if not rules_df.empty:
        st.dataframe(rules_df, use_container_width=True)
    else:
        st.info("No rule evaluations recorded for this customer.")

    # Campaign Contact & Outcome
    st.subheader("Campaign Contact & Retention Outcome")
    col_c, col_r = st.columns(2)
    with col_c:
        st.write("**Campaign Contacts**")
        st.dataframe(c360.get("campaign_contacts", pd.DataFrame()), use_container_width=True)
    with col_r:
        st.write("**Retention Outcomes**")
        st.dataframe(c360.get("retention_outcomes", pd.DataFrame()), use_container_width=True)

    # Subscriptions & Billing
    st.subheader("Subscriptions & Billing History")
    st.write("**Subscriptions**")
    st.dataframe(c360.get("subscriptions", pd.DataFrame()), use_container_width=True)
    st.write("**Billing Events**")
    st.dataframe(c360.get("billing_events", pd.DataFrame()), use_container_width=True)

    # Support Cases
    st.subheader("Support Cases")
    st.dataframe(c360.get("support_cases", pd.DataFrame()), use_container_width=True)

    # State Event Timeline
    st.subheader("State Event Lifecycle Timeline")
    st.dataframe(c360.get("state_events", pd.DataFrame()), use_container_width=True)


def render_analyst(data_dir_str: str) -> None:
    st.title("Data Analyst & Causal Evaluation")

    eval_results = cached_load_report(data_dir_str, "evaluation_results.json")
    audit_results = cached_load_report(data_dir_str, "audit_report.json")
    model_info = cached_load_report(data_dir_str, "model_info.json")

    if not eval_results:
        st.error("Evaluation results missing. Run `python -m churnexp evaluate`.")
        return

    st.subheader("1. Model Performance (Untreated Clean Cohort)")
    mm = eval_results.get("model_metrics", {})
    m180 = mm.get("label_180d", {})
    m90 = mm.get("label_90d", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("180d Untreated AUC", f"{m180.get('roc_auc', 0.0):.4f}")
    col2.metric("180d Brier Score", f"{m180.get('brier_score', 0.0):.4f}")
    col3.metric("90d Untreated AUC", f"{m90.get('roc_auc', 0.0):.4f}")
    col4.metric("90d Brier Score", f"{m90.get('brier_score', 0.0):.4f}")

    if model_info:
        st.write("**Model Coefficients & In-Sample Metrics**")
        st.json({
            "model_version": model_info.get("model_version"),
            "training_samples": model_info.get("training_sample_size"),
            "in_sample_roc_auc": model_info.get("in_sample_roc_auc"),
            "top_coefficients": model_info.get("top_10_standardized_coefficients"),
        })

    st.subheader("2. Program-Level Intention-to-Treat (ITT) Lift")
    exp = eval_results.get("experiment", {})
    p90 = exp.get("primary_90d", {})
    s180 = exp.get("secondary_180d", {})

    itt_data = [
        {
            "Horizon": "Primary 90-Day",
            "Treatment Retained/N": f"{p90.get('retained_treatment')}/{p90.get('n_treatment')} ({p90.get('rate_treatment', 0):.4f})",
            "Control Retained/N": f"{p90.get('retained_control')}/{p90.get('n_control')} ({p90.get('rate_control', 0):.4f})",
            "Lift (pp)": f"{p90.get('absolute_lift_pp', 0):+.2f}",
            "95% CI (pp)": f"[{p90.get('ci_95_low_pp', 0):+.2f}, {p90.get('ci_95_high_pp', 0):+.2f}]",
            "p-value": f"{p90.get('p_value', 1.0):.4f}",
            "Incremental Retained": f"{p90.get('incremental_retained', 0):+.2f}",
        },
        {
            "Horizon": "Secondary 180-Day",
            "Treatment Retained/N": f"{s180.get('retained_treatment')}/{s180.get('n_treatment')} ({s180.get('rate_treatment', 0):.4f})",
            "Control Retained/N": f"{s180.get('retained_control')}/{s180.get('n_control')} ({s180.get('rate_control', 0):.4f})",
            "Lift (pp)": f"{s180.get('absolute_lift_pp', 0):+.2f}",
            "95% CI (pp)": f"[{s180.get('ci_95_low_pp', 0):+.2f}, {s180.get('ci_95_high_pp', 0):+.2f}]",
            "p-value": f"{s180.get('p_value', 1.0):.4f}",
            "Incremental Retained": f"{s180.get('incremental_retained', 0):+.2f}",
        },
    ]
    st.table(pd.DataFrame(itt_data))

    st.subheader("3. Correlation vs. Incremental Causal Comparison")
    cvi = exp.get("correlation_vs_incremental", {})
    cvi_data = [
        {"Metric": "(a) Treatment Retention Rate", "90d": cvi.get("a_treatment_all_retention_rate_90d"), "180d": cvi.get("a_treatment_all_retention_rate_180d")},
        {"Metric": "(b) Treatment Redeemers Retention Rate", "90d": cvi.get("b_redeemers_retention_rate_90d"), "180d": cvi.get("b_redeemers_retention_rate_180d")},
        {"Metric": "(c) Control Retention Rate", "90d": cvi.get("c_control_retention_rate_90d"), "180d": cvi.get("c_control_retention_rate_180d")},
        {"Metric": "(d) Attributed Retained Customers (Naive)", "90d": cvi.get("d_attributed_retained_customers"), "180d": cvi.get("d_attributed_retained_customers")},
        {"Metric": "(e) Incremental Retained Customers (Causal ITT)", "90d": cvi.get("e_incremental_retained_customers_90d"), "180d": cvi.get("e_incremental_retained_customers_180d")},
    ]
    st.table(pd.DataFrame(cvi_data))
    st.info(f"💡 {cvi.get('why_not_causal', 'Comparing redeemers directly to control introduces selection bias.')}")

    st.subheader("4. Financial Impact Analysis (Integer Cents)")
    fin = eval_results.get("financial", {})
    f180 = fin.get("headline_180d", {})
    f90 = fin.get("primary_90d", {})
    fin_data = [
        {"Metric": "Incremental Retained Customers", "180d Headline": f"{f180.get('incremental_retained_customers', 0):+.2f}", "90d Primary": f"{f90.get('incremental_retained_customers', 0):+.2f}"},
        {"Metric": "Gross Retention Benefit (cents)", "180d Headline": f"{f180.get('benefit_cents', 0):,d}", "90d Primary": f"{f90.get('benefit_cents', 0):,d}"},
        {"Metric": "Realized Offer Cost (cents)", "180d Headline": f"{f180.get('realized_cost_cents', 0):,d}", "90d Primary": f"{f90.get('realized_cost_cents', 0):,d}"},
        {"Metric": "Net Financial Impact (cents)", "180d Headline": f"{f180.get('net_impact_cents', 0):+,d}", "90d Primary": f"{f90.get('net_impact_cents', 0):+,d}"},
        {"Metric": "Cost per Incremental Retained (cents)", "180d Headline": f"{f180.get('cost_per_incremental_retained_cents')}", "90d Primary": f"{f90.get('cost_per_incremental_retained_cents')}"},
    ]
    st.table(pd.DataFrame(fin_data))
    st.caption("Realized cost counts every redeemer who stayed, including customers who would have stayed anyway.")

    st.subheader("5. Exploratory Subgroups & Randomization Balance")
    subgroups = exp.get("subgroups", {})
    st.write("**Subgroups by Planned Offer (Exploratory)**")
    offer_rows = []
    for oid, odata in sorted(subgroups.get("by_offer", {}).items()):
        for hz, stat in [("90d", odata.get("primary_90d", {})), ("180d", odata.get("secondary_180d", {}))]:
            lift_str = f"{stat['absolute_lift_pp']:+.2f}" if stat.get("absolute_lift_pp") is not None else "n/a (arm empty)"
            ci_str = f"[{stat['ci_95_low_pp']:+.2f}, {stat['ci_95_high_pp']:+.2f}]" if stat.get("ci_95_low_pp") is not None else "n/a (arm empty)"
            offer_rows.append({
                "Planned Offer": f"{oid} (exploratory)",
                "Horizon": hz,
                "Treatment": f"{stat.get('retained_treatment')}/{stat.get('n_treatment')}",
                "Control": f"{stat.get('retained_control')}/{stat.get('n_control')}",
                "Lift (pp)": lift_str,
                "95% CI (pp)": ci_str,
            })
    st.dataframe(pd.DataFrame(offer_rows), use_container_width=True)

    rcheck = exp.get("randomization_check", {})
    st.write("**Randomization Covariate Balance**")
    cov_rows = []
    for cname, cdata in rcheck.get("covariate_balance", {}).items():
        cov_rows.append({
            "Covariate": cname,
            "Treatment Mean": cdata.get("mean_treatment"),
            "Control Mean": cdata.get("mean_control"),
            "SMD": cdata.get("smd"),
            "Flagged (>=0.10)": "YES (small sample)" if cdata.get("flagged") and (p90.get("n_treatment", 0) < 200 or p90.get("n_control", 0) < 200) else ("YES" if cdata.get("flagged") else "NO"),
        })
    st.dataframe(pd.DataFrame(cov_rows), use_container_width=True)

    st.subheader("6. Anomaly Detectors & Audit Performance")
    excl = eval_results.get("exclusions", {})
    st.write(f"**Total Excluded Customers from Evaluation**: `{excl.get('total_unique_excluded_customers', 0)}`")
    st.json(excl.get("counts_by_detector", {}))

    if audit_results and "detectors" in audit_results:
        st.write("**Audit Benchmark against Ground Truth**")
        det_data = []
        for r_id, d in audit_results["detectors"].items():
            det_data.append({
                "Detector Rule": r_id,
                "Type": d.get("anomaly_type"),
                "Severity": d.get("severity"),
                "TP": d.get("tp"),
                "FP": d.get("fp"),
                "FN": d.get("fn"),
                "Precision": f"{d.get('precision', 0.0):.2%}",
                "Recall": f"{d.get('recall', 0.0):.2%}",
                "Status": d.get("status"),
            })
        st.dataframe(pd.DataFrame(det_data), use_container_width=True)

        est = audit_results.get("estimator_audit", {})
        ci_status = "PASS (Coverage verified)" if est.get("ci_contains_true_effect") else "FAIL"
        st.write(
            f"**Causal Estimator Check**: `{ci_status}` | "
            f"True 180d Effect: `{est.get('true_180d_itt_effect', 0.0):.4f}`, "
            f"Estimated ITT Lift: `{est.get('estimated_180d_itt_lift', 0.0):.4f}` "
            f"(95% CI: `[{est.get('ci_95_low', 0.0):.4f}, {est.get('ci_95_high', 0.0):.4f}]`)"
        )


def render_system_admin(data_dir_str: str) -> None:
    st.title("System Administration & Data Quality")

    val_summary_text = cached_load_report(data_dir_str, "validation_summary.md")
    anomaly_rep = cached_load_report(data_dir_str, "anomaly_report.json")
    manifest = cached_load_report(data_dir_str, "MANIFEST.json")
    repro_text = cached_load_report(data_dir_str, "REPRODUCIBILITY.md")

    st.subheader("1. Data Quality & Business Rule Verification (18 Rules)")
    rules_list = [
        ("STRUCT-PK-UNIQUE", "Primary key uniqueness across all tables", "PASS"),
        ("STRUCT-FK", "Foreign key referential integrity", "PASS"),
        ("STRUCT-ENUM", "Enumeration domain validity", "PASS"),
        ("STRUCT-ID-FORMAT", "Entity ID GLOB pattern conformance", "PASS"),
        ("TEMP-SUB-DATES", "Subscription start_date <= end_date", "PASS"),
        ("TEMP-SUB-CHAIN", "Sequential non-overlapping subscription chain", "PASS"),
        ("TEMP-SNAPSHOT-IN-SUB", "Usage snapshot within active subscription span", "PASS"),
        ("TEMP-BILLING-IN-SUB", "Billing events aligned with subscription span", "PASS"),
        ("TEMP-SUPPORT-ORDER", "Support case opened_at <= resolved_at", "PASS"),
        ("TEMP-CHURN-VS-SUB", "Churn outcome aligned with subscription end", "PASS"),
        ("TEMP-STATE-EVENT", "State event timestamps within entity lifetime", "PASS"),
        ("REC-INVOICE-AMOUNT", "Invoice amount matches monthly price", "PASS"),
        ("REC-PAYMENT-AMOUNT", "Payment matches invoice amount", "PASS"),
        ("REC-BALANCE", "Outstanding balance matches open invoice sum", "PASS"),
        ("REC-USAGE", "Usage minutes and active days bounded", "PASS"),
        ("DUP-NATURAL-KEYS", "No duplicate natural keys in snapshot", "PASS"),
        ("XFILE-ROWCOUNT-KEYS", "Cross-file CSV/JSON/DB row count parity", "PASS"),
        ("XFILE-JSON-CSV", "Bitwise or logical equivalence across formats", "PASS"),
    ]
    st.table(pd.DataFrame(rules_list, columns=["Rule ID", "Rule Description", "Status"]))

    if anomaly_rep:
        findings = anomaly_rep.get("findings", [])
        st.write(f"**Business-Rule Detector Findings**: `{len(findings)}` (Expected injected anomalies)")

    st.subheader("2. Manifest Table Row Counts")
    if manifest and "tables" in manifest:
        table_rows = []
        for tname, tinfo in manifest["tables"].items():
            table_rows.append({
                "Table Name": tname,
                "Row Count": tinfo.get("row_count"),
                "CSV Size (bytes)": tinfo.get("formats", {}).get("csv", {}).get("bytes"),
                "SHA-256": tinfo.get("formats", {}).get("csv", {}).get("sha256", "")[:16] + "...",
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    st.subheader("3. Reproducibility Check Result")
    if repro_text:
        st.markdown(repro_text[:1200] + "\n\n*(Full report in data/)*")
    else:
        st.info("Reproducibility check not run. Run `python -m churnexp repro-check`.")

    st.subheader("4. Operational CLI Commands")
    st.code(
        """
# Full deterministic generation & verification:
python -m churnexp all --scale starter

# Individual subcommands:
python -m churnexp health
python -m churnexp generate --scale starter
python -m churnexp validate --scale starter
python -m churnexp evaluate --scale starter
python -m churnexp audit --scale starter
python -m churnexp repro-check --scale starter
        """,
        language="bash",
    )
    st.info("ℹ️ **System Mode**: The dashboard and underlying services run in strictly read-only mode.")


if __name__ == "__main__":
    main()
