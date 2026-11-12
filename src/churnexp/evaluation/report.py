"""End-to-end evaluation orchestrator and report writer (evaluation_results.json and evaluation_report.md)."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Mapping
import pandas as pd

from churnexp.evaluation.financial import evaluate_financial_impact
from churnexp.evaluation.lift import evaluate_experiment_lift
from churnexp.evaluation.metrics import evaluate_model_metrics
from churnexp.validation.detectors import DETECTOR_DEFINITIONS, run_detectors
from churnexp.validation.report import Finding


def _normalize_for_json(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {str(k): _normalize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize_for_json(v) for v in obj]
    return obj


def compute_exclusion_summary(detector_findings: list[Finding]) -> dict[str, Any]:
    """Summarize customers excluded per detector rule_id."""
    cids_by_rule: dict[str, set[str]] = {
        rule_id: set() for rule_id, _, _ in DETECTOR_DEFINITIONS
    }
    all_excluded: set[str] = set()
    for f in detector_findings:
        cid = f.evidence.get("customer_id")
        if cid:
            cid_str = str(cid)
            cids_by_rule.setdefault(f.rule_id, set()).add(cid_str)
            all_excluded.add(cid_str)

    counts_by_detector = {
        rule_id: len(cids_by_rule.get(rule_id, set()))
        for rule_id, _, _ in DETECTOR_DEFINITIONS
    }
    return {
        "counts_by_detector": counts_by_detector,
        "total_unique_excluded_customers": len(all_excluded),
        "excluded_customer_ids": sorted(all_excluded),
    }


def format_evaluation_markdown(results: dict[str, Any]) -> str:
    """Format full markdown evaluation report including tables and 'How to read this'."""
    scale = results["scale"]
    excl = results["exclusions"]
    mm = results["model_metrics"]
    m180 = mm["label_180d"]
    m90 = mm["label_90d"]
    h180 = m180["high_band_decision_rule"]
    h90 = m90["high_band_decision_rule"]
    minfo = mm.get("in_sample_model_info", {})

    exp = results["experiment"]
    p90 = exp["primary_90d"]
    s180 = exp["secondary_180d"]
    p90_nnt = f"{p90['nnt']:.2f}" if p90.get("nnt") is not None else "N/A"
    s180_nnt = f"{s180['nnt']:.2f}" if s180.get("nnt") is not None else "N/A"
    sub = exp["subgroups"]
    rcheck = exp["randomization_check"]
    cvi = exp["correlation_vs_incremental"]

    fin = results["financial"]
    f180 = fin["headline_180d"]
    f90 = fin["primary_90d"]

    lines: list[str] = [
        f"# Evaluation Report (`scale={scale}`)",
        "",
        "## 1. Anomaly Exclusions (Pre-Evaluation Hygiene)",
        "",
        f"- **Total Unique Excluded Customers**: `{excl['total_unique_excluded_customers']}`",
        "",
        "| Detector Rule ID | Excluded Customers |",
        "| :--- | ---: |",
    ]
    for r_id, cnt in excl["counts_by_detector"].items():
        lines.append(f"| `{r_id}` | {cnt} |")

    lines.extend(
        [
            "",
            "## 2. Churn Risk Model Performance",
            "",
            "### 2.1 In-Sample Training Summary (`P0 = 2025-07-01`, `label_type = in_sample`)",
            "",
            f"- **Model Version**: `{minfo.get('model_version', 'logreg-v1')}` (`in_sample`)",
            f"- **Training Rows ($P_0$)**: `{minfo.get('training_rows', 'N/A')}`",
            f"- **Training Positives (2025 180d)**: `{minfo.get('training_positives', 'N/A')}`",
            f"- **In-Sample ROC-AUC**: `{minfo.get('in_sample_roc_auc', 'N/A')}`",
            "",
            "#### Top 10 Standardized Logistic Regression Coefficients (by Absolute Magnitude)",
            "",
            "| Rank | Feature | Coefficient | Sign | Absolute |",
            "| ---: | :--- | ---: | :---: | ---: |",
        ]
    )
    for idx, coef in enumerate(minfo.get("top_10_coefficients", []), start=1):
        c_val = float(coef["coefficient"])
        s_val = str(coef.get("sign", "+" if c_val >= 0 else "-"))
        lines.append(
            f"| {idx} | `{coef['feature']}` | {c_val:.6f} | `{s_val}` | {abs(c_val):.6f} |"
        )

    lines.extend(
        [
            "",
            "### 2.2 Out-of-Time Evaluation on the Untreated Cohort (`P = 2026-01-01`, ADR-012)",
            "",
            "Evaluated strictly on scored customers with a 2026 churn outcome who are **not** in the `TREATMENT` arm (i.e., `CONTROL` and uncontacted customers), excluding detector-flagged customers.",
            "",
            "| Horizon Label | N | Positives | Base Rate | ROC-AUC | Brier Score | HIGH Band Precision | HIGH Band Recall | HIGH Band F1 | Precision Lift |",
            "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| **180-Day (2026 Horizon)** | {m180['n']} | {m180['positives']} | {m180['base_rate']:.4f} | {m180['roc_auc'] if m180['roc_auc'] is not None else 'N/A'} | {m180.get('brier_score', 0.0):.4f} | {h180['precision']:.4f} | {h180['recall']:.4f} | {h180['f1']:.4f} | {h180['precision_lift']:.2f}x |",
            f"| **90-Day (Outcome Window)** | {m90['n']} | {m90['positives']} | {m90['base_rate']:.4f} | {m90['roc_auc'] if m90['roc_auc'] is not None else 'N/A'} | — | {h90['precision']:.4f} | {h90['recall']:.4f} | {h90['f1']:.4f} | {h90['precision_lift']:.2f}x |",
            "",
            "## 3. Randomized Retention Experiment (Intention-to-Treat)",
            "",
            "### 3.1 Program-Level ITT Lift (Primary 90-Day & Secondary 180-Day)",
            "",
            "| Metric | Primary: 90-Day Retention | Secondary: 180-Day Retention |",
            "| :--- | ---: | ---: |",
            f"| **Treatment Retained / N** | {p90['retained_treatment']} / {p90['n_treatment']} ({p90['rate_treatment']:.4f}) | {s180['retained_treatment']} / {s180['n_treatment']} ({s180['rate_treatment']:.4f}) |",
            f"| **Control Retained / N** | {p90['retained_control']} / {p90['n_control']} ({p90['rate_control']:.4f}) | {s180['retained_control']} / {s180['n_control']} ({s180['rate_control']:.4f}) |",
            f"| **Absolute Lift (pp)** | {p90['absolute_lift_pp']:+.2f} pp ({p90['absolute_lift']:+.4f}) | {s180['absolute_lift_pp']:+.2f} pp ({s180['absolute_lift']:+.4f}) |",
            f"| **95% CI (pp, unpooled)** | [{p90['ci_95_low_pp']:+.2f}, {p90['ci_95_high_pp']:+.2f}] pp | [{s180['ci_95_low_pp']:+.2f}, {s180['ci_95_high_pp']:+.2f}] pp |",
            f"| **Two-Sided p-value (pooled z)** | {p90['p_value']:.4f} | {s180['p_value']:.4f} |",
            f"| **Relative Lift** | {p90['relative_lift'] * 100.0:+.2f}% | {s180['relative_lift'] * 100.0:+.2f}% |",
            f"| **Incremental Retained Customers** | {p90['incremental_retained']:+.2f} ([{p90['incremental_retained_ci_low']:+.2f}, {p90['incremental_retained_ci_high']:+.2f}]) | {s180['incremental_retained']:+.2f} ([{s180['incremental_retained_ci_low']:+.2f}, {s180['incremental_retained_ci_high']:+.2f}]) |",
            f"| **Number Needed to Treat (NNT)** | {p90_nnt} | {s180_nnt} |",
            "",
            "### 3.2 Exploratory Subgroup Breakdown by Planned Offer",
            "",
            "| Planned Offer | Horizon | Treatment Retained / N | Control Retained / N | Lift (pp) | 95% CI (pp) | p-value | Incremental Retained |",
            "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    def _format_subgroup_row(label: str, horizon: str, s: dict[str, Any]) -> str:
        t_n = s.get("n_treatment", 0)
        c_n = s.get("n_control", 0)
        t_ret = s.get("retained_treatment", 0)
        c_ret = s.get("retained_control", 0)
        t_rate = f"({s['rate_treatment']:.4f})" if s.get("rate_treatment") is not None else "(0.0000)"
        c_rate = f"({s['rate_control']:.4f})" if s.get("rate_control") is not None else "(0.0000)"
        t_cell = f"{t_ret}/{t_n} {t_rate}"
        c_cell = f"{c_ret}/{c_n} {c_rate}"

        if t_n == 0 or c_n == 0 or s.get("absolute_lift_pp") is None:
            lift_str = "n/a (arm empty)"
            ci_str = "n/a (arm empty)"
            p_str = "n/a (arm empty)"
            inc_str = "n/a (arm empty)"
        else:
            lift_str = f"{s['absolute_lift_pp']:+.2f}"
            ci_str = f"[{s['ci_95_low_pp']:+.2f}, {s['ci_95_high_pp']:+.2f}]"
            p_str = f"{s['p_value']:.4f}"
            inc_str = f"{s['incremental_retained']:+.2f}"

        return f"| `{label}` *(exploratory)* | {horizon} | {t_cell} | {c_cell} | {lift_str} | {ci_str} | {p_str} | {inc_str} |"

    for oid, odata in sorted(sub["by_offer"].items()):
        lines.append(_format_subgroup_row(oid, "90d", odata["primary_90d"]))
        lines.append(_format_subgroup_row(oid, "180d", odata["secondary_180d"]))

    lines.extend(
        [
            "",
            "### 3.3 Exploratory Subgroup Breakdown by Risk Stratum",
            "",
            "| Risk Stratum | Horizon | Treatment Retained / N | Control Retained / N | Lift (pp) | 95% CI (pp) | p-value | Incremental Retained |",
            "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for strat, sdata in sub["by_stratum"].items():
        lines.append(_format_subgroup_row(strat, "90d", sdata["primary_90d"]))
        lines.append(_format_subgroup_row(strat, "180d", sdata["secondary_180d"]))

    lines.extend(
        [
            "",
            "### 3.4 Randomization & Covariate Balance Check",
            "",
            "| Covariate | Treatment Mean | Control Mean | Standardized Mean Diff (SMD) | Flagged (`SMD >= 0.10`) |",
            "| :--- | ---: | ---: | ---: | :---: |",
        ]
    )
    is_small_sample = (p90.get("n_treatment", 0) < 200 or p90.get("n_control", 0) < 200)
    for cov_name, cdata in rcheck.get("covariate_balance", {}).items():
        if cdata.get("flagged"):
            flag_str = "YES (small sample)" if is_small_sample else "YES"
            smd_str = f"{cdata['smd']:.6f} *(small sample)*" if is_small_sample else f"{cdata['smd']:.6f}"
        else:
            flag_str = "NO"
            smd_str = f"{cdata['smd']:.6f}"
        lines.append(
            f"| `{cov_name}` | {cdata['mean_treatment']:.4f} | {cdata['mean_control']:.4f} | {smd_str} | `{flag_str}` |"
        )

    lines.extend(
        [
            "",
            "### 3.5 Correlation vs. Incremental Causal Comparison",
            "",
            "| Metric | 90-Day Window | 180-Day Horizon |",
            "| :--- | ---: | ---: |",
            f"| **(a) All TREATMENT Retention Rate** | {cvi['a_treatment_all_retention_rate_90d']:.4f} | {cvi['a_treatment_all_retention_rate_180d']:.4f} |",
            f"| **(b) TREATMENT Redeemers Only Retention Rate** (`n={cvi['n_redeemers']}`) | {cvi['b_redeemers_retention_rate_90d']:.4f} | {cvi['b_redeemers_retention_rate_180d']:.4f} |",
            f"| **(c) CONTROL Retention Rate** | {cvi['c_control_retention_rate_90d']:.4f} | {cvi['c_control_retention_rate_180d']:.4f} |",
            f"| **(d) Attributed Retained Customers (Naive Count)** | {cvi['d_attributed_retained_customers']} | {cvi['d_attributed_retained_customers']} |",
            f"| **(e) Incremental Retained Customers (Causal ITT Lift)** | {cvi['e_incremental_retained_customers_90d']:+.2f} | {cvi['e_incremental_retained_customers_180d']:+.2f} |",
            "",
            f"> {cvi['why_not_causal']}",
            "",
            "## 4. Financial Impact Analysis (Integer Cents)",
            "",
            f"- **Expected Margin Horizon**: `{fin['expected_margin_months']}` months",
            f"- **Average Expected 6-Month Margin per Treated Customer**: `{fin['avg_expected_margin_cents']}` cents",
            f"- **Realized Offer Cost (`redeemed=1` & `retained_90d=1`, `n={fin['redeemed_retained_90d_count']}`)**: `{fin['realized_cost_cents']}` cents",
            "",
            "| Financial Metric | Headline: 180-Day Lift Basis (6m Horizon) | Primary Endpoint: 90-Day Lift Basis |",
            "| :--- | ---: | ---: |",
            f"| **Incremental Retained Customers** | {f180['incremental_retained_customers']:+.2f} ([{f180['incremental_retained_ci_low']:+.2f}, {f180['incremental_retained_ci_high']:+.2f}]) | {f90['incremental_retained_customers']:+.2f} ([{f90['incremental_retained_ci_low']:+.2f}, {f90['incremental_retained_ci_high']:+.2f}]) |",
            f"| **Gross Retention Benefit (cents)** | {f180['benefit_cents']} ([{f180['benefit_ci_low_cents']}, {f180['benefit_ci_high_cents']}]) | {f90['benefit_cents']} ([{f90['benefit_ci_low_cents']}, {f90['benefit_ci_high_cents']}]) |",
            f"| **Realized Offer Cost (cents)** | {f180['realized_cost_cents']} | {f90['realized_cost_cents']} |",
            f"| **Net Financial Impact (cents)** | {f180['net_impact_cents']} ([{f180['net_impact_ci_low_cents']}, {f180['net_impact_ci_high_cents']}]) | {f90['net_impact_cents']} ([{f90['net_impact_ci_low_cents']}, {f90['net_impact_ci_high_cents']}]) |",
            f"| **Cost per Incremental Retained Customer (cents)** | {f180['cost_per_incremental_retained_cents'] if f180['cost_per_incremental_retained_cents'] is not None else 'N/A'} | {f90['cost_per_incremental_retained_cents'] if f90['cost_per_incremental_retained_cents'] is not None else 'N/A'} |",
            "",
            "Realized cost counts every redeemer who stayed, including customers who would have stayed anyway.",
            "",
            f"- **180-Day Financial Assessment**: {f180['plain_statement']}",
            f"- **90-Day Financial Assessment**: {f90['plain_statement']}",
            "",
            "## 5. Business reading",
            "",
        ]
    )

    # Template-built business reading
    lift_180 = s180.get("absolute_lift")
    lift_sign = "positive" if (lift_180 is not None and lift_180 > 0) else ("negative" if (lift_180 is not None and lift_180 < 0) else "neutral")
    lift_ci_low = s180.get("ci_95_low")
    lift_ci_high = s180.get("ci_95_high")
    if lift_ci_low is not None and lift_ci_high is not None:
        lift_ci_excludes_zero = (lift_ci_low > 0 and lift_ci_high > 0) or (lift_ci_low < 0 and lift_ci_high < 0)
        lift_ci_str = "excludes zero" if lift_ci_excludes_zero else "includes zero"
    else:
        lift_ci_str = "is undefined"

    net_cents = f180.get("net_impact_cents", 0)
    net_is_negative = net_cents < 0
    net_impact_str = "negative" if net_is_negative else "positive"

    net_low = f180.get("net_impact_ci_low_cents", 0)
    net_high = f180.get("net_impact_ci_high_cents", 0)
    net_ci_excludes_zero = (net_low > 0 and net_high > 0) or (net_low < 0 and net_high < 0)
    net_ci_str = "excludes zero" if net_ci_excludes_zero else "includes zero"

    cost_per_inc = f180.get("cost_per_incremental_retained_cents")
    avg_margin = fin.get("avg_expected_margin_cents", 0)
    if cost_per_inc is not None:
        econ_sentence = f"The cost per incremental retained customer is {cost_per_inc} cents versus the average 6-month margin of {avg_margin} cents."
    else:
        econ_sentence = f"The cost per incremental retained customer is not available versus the average 6-month margin of {avg_margin} cents."

    lines.extend(
        [
            f"1. **Causal Lift Sign & Confidence**: The sign of the 180-day retention lift is {lift_sign} ({s180.get('absolute_lift_pp', 0.0):+.2f} pp), and the 95% confidence interval of the 180-day lift {lift_ci_str} ([{s180.get('ci_95_low_pp', 0.0):+.2f}, {s180.get('ci_95_high_pp', 0.0):+.2f}] pp).",
            f"2. **Net Impact Assessment**: Program net impact is {net_impact_str} ({net_cents} cents), and the 95% confidence interval of net impact {net_ci_str} ([{net_low}, {net_high}] cents).",
            f"3. **Unit Economics Comparison**: {econ_sentence}",
            "4. **Simulation Caveat**: These conclusions hold only under the stated simulation parameters.",
            "",
            "## 6. How to read this",
            "",
            "1. **What Intention-to-Treat (ITT) Means**: Every eligible customer randomized into `TREATMENT` or `CONTROL` at `W01` (`2026-01-05`) is analyzed in their assigned arm regardless of whether delivery succeeded (`SENT` vs `DELIVERY_FAILED`) or whether the customer responded or redeemed. Comparing `TREATMENT` redeemers directly to `CONTROL` introduces severe selection bias because customers who open and redeem offers also have higher baseline retention propensity.",
            "2. **Denominators and Time Windows**: Model evaluation uses the unflagged untreated cohort (`CONTROL` + uncontacted customers scored at `P = 2026-01-01`). Experiment evaluation uses unflagged eligible customers assigned at `2026-01-05`. The **90-day outcome window** (`2026-01-05` to `2026-04-05`) is the **primary experiment metric** (Decision D3), while the **180-day horizon** (`2026-01-01` to `2026-06-30`) is the **secondary experiment metric** and serves as the headline financial basis because expected gross margin is evaluated over 6 months.",
            "3. **Subgroup Results are Exploratory**: Breakdowns by planned offer (`OFF-2026-000001..000003`) and risk stratum (`HIGH`, `MEDIUM`) have smaller sample sizes, wider confidence intervals, and no multiplicity adjustment; they should be read as directional and exploratory.",
            "4. **Why Out-of-Time Model AUC is Modest**: In the data-generating process, observable behavioral decay (usage drop and elevated support/cancellation inquiries) manifests only during the final ~3 months prior to a voluntary churn event. Over a 180-day prediction window (`2026-01-01` to `2026-06-30`), customers who churn in the second half of the window (`April–June 2026`) have not yet begun their behavioral decay as of `P = 2026-01-01`, diluting 180-day signal.",
            "5. **Known Limitations**:",
            "   - Single campaign wave (`2026-W01`) on synthetic data.",
            "   - Boundary plan-change exclusion: 5 customers at `P = 2026-01-01` and 12 customers at `P0 = 2025-07-01` (at full scale) are excluded from `build_features` because a plan change occurred exactly on the `as_of` date (`previous.end_date = as_of - 1 day`, `next.start_date = as_of`), and `build_features` strictly reads subscriptions with `start_date < as_of`.",
            "   - Margin-rule constraint on Free Month offer: `OFF-2026-000003` (`1 free month`, cost = 100% of 1 month's price, max allowed = `0.25 * 6 * gross_margin_pct`) is mathematically eligible only for `PREMIUM` tier subscriptions (`gross_margin_pct = 0.70`, giving `1.05 >= 1.00`), whereas `BASIC` (`0.55`) and `STANDARD` (`0.62`) fail `ER-007` for `OFF-2026-000003`.",
            "",
        ]
    )
    return "\n".join(lines)


def run_evaluation(
    tables: Mapping[str, pd.DataFrame],
    scale: str = "starter",
    output_dir: Path | str | None = None,
    assignment_date: date | str = "2026-01-05",
    score_as_of: str = "2026-01-01",
    outcome_window_days: int = 90,
    expected_margin_months: int = 6,
    model_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run blind detectors, exclude flagged customers, compute model/lift/financial metrics, and write outputs."""
    if model_info is None and output_dir is not None:
        p_info = Path(output_dir) / "model_info.json"
        if p_info.is_file():
            try:
                model_info = json.loads(p_info.read_text(encoding="utf-8"))
            except Exception:
                pass
        if model_info is None:
            # Check sibling output/<scale>/model_info.json
            repo_cand = Path(output_dir).resolve()
            for _ in range(3):
                p_cand = repo_cand / "output" / scale / "model_info.json"
                if p_cand.is_file():
                    try:
                        model_info = json.loads(p_cand.read_text(encoding="utf-8"))
                        break
                    except Exception:
                        pass
                repo_cand = repo_cand.parent

    det_findings = run_detectors(tables)
    exclusions = compute_exclusion_summary(det_findings)

    model_metrics = evaluate_model_metrics(
        tables=tables,
        detector_findings=det_findings,
        assignment_date=assignment_date,
        outcome_window_days=outcome_window_days,
        model_info=model_info,
    )
    experiment_lift = evaluate_experiment_lift(
        tables=tables,
        detector_findings=det_findings,
        score_as_of=score_as_of,
    )
    financial_impact = evaluate_financial_impact(
        tables=tables,
        detector_findings=det_findings,
        lift_results=experiment_lift,
        assignment_date=assignment_date,
        expected_margin_months=expected_margin_months,
    )

    s180 = experiment_lift["secondary_180d"]
    lift_180 = s180.get("absolute_lift")
    lift_sign = "positive" if (lift_180 is not None and lift_180 > 0) else ("negative" if (lift_180 is not None and lift_180 < 0) else "neutral")
    lift_ci_low = s180.get("ci_95_low")
    lift_ci_high = s180.get("ci_95_high")
    if lift_ci_low is not None and lift_ci_high is not None:
        lift_ci_excludes_zero = (lift_ci_low > 0 and lift_ci_high > 0) or (lift_ci_low < 0 and lift_ci_high < 0)
    else:
        lift_ci_excludes_zero = False

    f180 = financial_impact.get("headline_180d", {})
    net_cents = f180.get("net_impact_cents", 0)
    net_is_negative = net_cents < 0
    net_low = f180.get("net_impact_ci_low_cents", 0)
    net_high = f180.get("net_impact_ci_high_cents", 0)
    net_ci_excludes_zero = (net_low > 0 and net_high > 0) or (net_low < 0 and net_high < 0)
    cost_per_inc = f180.get("cost_per_incremental_retained_cents")
    avg_margin = financial_impact.get("avg_expected_margin_cents", 0)

    business_reading = {
        "lift_sign": lift_sign,
        "lift_180d_ci_excludes_zero": lift_ci_excludes_zero,
        "net_impact_is_negative": net_is_negative,
        "net_impact_ci_excludes_zero": net_ci_excludes_zero,
        "cost_per_incremental_retained_cents": cost_per_inc,
        "avg_expected_margin_cents": avg_margin,
        "caveat": "These conclusions hold only under the stated simulation parameters.",
    }

    raw_results = {
        "scale": scale,
        "exclusions": exclusions,
        "model_metrics": model_metrics,
        "experiment": experiment_lift,
        "financial": financial_impact,
        "business_reading": business_reading,
    }
    normalized = _normalize_for_json(raw_results)
    report_md = format_evaluation_markdown(normalized)

    if output_dir is not None:
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        json_path = out_p / "evaluation_results.json"
        md_path = out_p / "evaluation_report.md"
        json_path.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        md_path.write_text(
            report_md,
            encoding="utf-8",
        )

    return normalized, report_md

