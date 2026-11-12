"""Ground truth audit against blind detectors and true causal treatment effects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
import pandas as pd

from churnexp.evaluation.report import run_evaluation
from churnexp.validation.checks import load_tables_from_db
from churnexp.validation.detectors import DETECTOR_DEFINITIONS, run_detectors
from churnexp.validation.report import Finding

DETECTOR_TO_ANOMALY_TYPE: dict[str, str] = {
    "DET-A-LABEL-BEFORE-PREDICTION": "A",
    "DET-B-INELIGIBLE-OFFER": "B",
    "DET-C-GROUP-LEAKAGE": "C",
    "DET-D-MULTI-ATTRIBUTION": "D",
}


def _extract_customer_id_from_finding(
    finding: Finding,
    tables: Mapping[str, pd.DataFrame],
) -> str | None:
    """Resolve finding entity_id or evidence to customer_id."""
    if finding.evidence and "customer_id" in finding.evidence:
        return str(finding.evidence["customer_id"])

    rid = finding.rule_id
    eid = str(finding.entity_id)

    if rid == "DET-A-LABEL-BEFORE-PREDICTION":
        churn_df = tables.get("churn_outcome")
        if churn_df is not None and not churn_df.empty:
            sub = churn_df[churn_df["churn_id"].astype(str) == eid]
            if not sub.empty:
                return str(sub.iloc[0]["customer_id"])
    elif rid in ("DET-B-INELIGIBLE-OFFER", "DET-C-GROUP-LEAKAGE"):
        cc_df = tables.get("campaign_contact")
        if cc_df is not None and not cc_df.empty:
            sub = cc_df[cc_df["contact_id"].astype(str) == eid]
            if not sub.empty:
                return str(sub.iloc[0]["customer_id"])
    elif rid == "DET-D-MULTI-ATTRIBUTION":
        if eid.startswith("CUS-"):
            return eid
        ret_df = tables.get("retention_outcome")
        if ret_df is not None and not ret_df.empty:
            sub = ret_df[ret_df["retention_id"].astype(str) == eid]
            if not sub.empty:
                return str(sub.iloc[0]["customer_id"])

    if eid.startswith("CUS-"):
        return eid

    return None


def run_audit(
    tables: Mapping[str, pd.DataFrame],
    gt_dir: Path,
    output_dir: Path | None = None,
    scale: str = "starter",
) -> tuple[dict[str, Any], str, bool]:
    """Execute ground truth audit against detectors and causal effects.

    Returns:
        tuple of (audit_dict, markdown_report, passed_bool)
    """
    findings = run_detectors(tables)

    anomalies_csv = gt_dir / "anomalies.csv"
    latent_csv = gt_dir / "latent_customer_state.csv"

    if not anomalies_csv.exists():
        raise FileNotFoundError(f"Missing ground truth anomalies file: {anomalies_csv}")
    if not latent_csv.exists():
        raise FileNotFoundError(f"Missing ground truth latent file: {latent_csv}")

    anomalies_gt = pd.read_csv(anomalies_csv)
    latent_df = pd.read_csv(latent_csv)

    # -------------------------------------------------------------------------
    # 1. Detector Scoring (TP, FP, FN, Precision, Recall per detector)
    # -------------------------------------------------------------------------
    detector_scores: dict[str, dict[str, Any]] = {}
    all_flagged_cids: set[str] = set()

    all_perfect = True
    total_gt = 0
    total_det = 0
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for rule_id, severity, desc in DETECTOR_DEFINITIONS:
        atype = DETECTOR_TO_ANOMALY_TYPE.get(rule_id, "")
        gt_sub = anomalies_gt[
            (anomalies_gt["detector_rule_id"] == rule_id)
            | (anomalies_gt["anomaly_type"] == atype)
        ]
        gt_cids = set(gt_sub["customer_id"].astype(str))

        rule_findings = [f for f in findings if f.rule_id == rule_id]
        det_cids: set[str] = set()
        for f in rule_findings:
            cid = _extract_customer_id_from_finding(f, tables)
            if cid is not None:
                det_cids.add(cid)
                all_flagged_cids.add(cid)

        tp_set = det_cids & gt_cids
        fp_set = det_cids - gt_cids
        fn_set = gt_cids - det_cids

        tp = len(tp_set)
        fp = len(fp_set)
        fn = len(fn_set)

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if not gt_cids else 0.0)
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0

        is_perfect = (precision == 1.0 and recall == 1.0)
        if not is_perfect:
            all_perfect = False

        total_gt += len(gt_cids)
        total_det += len(det_cids)
        total_tp += tp
        total_fp += fp
        total_fn += fn

        detector_scores[rule_id] = {
            "rule_id": rule_id,
            "anomaly_type": atype,
            "severity": severity,
            "description": desc,
            "ground_truth_count": len(gt_cids),
            "detected_count": len(det_cids),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": float(precision),
            "recall": float(recall),
            "status": "PASS" if is_perfect else "FAIL",
            "missed_customer_ids": sorted(fn_set),
            "false_positive_customer_ids": sorted(fp_set),
        }

    overall_prec = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 1.0

    # -------------------------------------------------------------------------
    # 2. Estimator Check (True 180-day ITT Effect vs Evaluation 95% CI)
    # -------------------------------------------------------------------------
    eval_results_file = output_dir / "evaluation_results.json" if output_dir else None
    if eval_results_file is not None and eval_results_file.exists():
        eval_results = json.loads(eval_results_file.read_text(encoding="utf-8"))
    else:
        # Run evaluation in memory or into output_dir
        eval_results, _ = run_evaluation(
            tables=tables,
            output_dir=output_dir,
            scale=scale,
        )

    # Identify unflagged W01 treatment customers
    cc_df = tables.get("campaign_contact", pd.DataFrame())
    if not cc_df.empty:
        w01_treat_mask = (
            (cc_df["experiment_group"].astype(str) == "TREATMENT")
            & (cc_df["contact_id"].astype(str).str.endswith("-W01"))
            & (~cc_df["customer_id"].astype(str).isin(all_flagged_cids))
        )
        unflagged_treat_cids = sorted(
            cc_df.loc[w01_treat_mask, "customer_id"].astype(str).unique()
        )
    else:
        unflagged_treat_cids = []

    n_unflagged_treat = len(unflagged_treat_cids)

    # Map customer_id -> true_effect_flag in latent DataFrame
    latent_by_cid: dict[str, int] = {}
    for row in latent_df.itertuples(index=False):
        cid = str(row.customer_id)
        flag_val = getattr(row, "true_effect_flag", 0)
        try:
            if pd.isna(flag_val):
                flag_int = 0
            else:
                flag_int = int(flag_val)
        except (TypeError, ValueError):
            flag_int = 0
        latent_by_cid[cid] = flag_int

    saved_count = sum(
        1 for c in unflagged_treat_cids if latent_by_cid.get(c, 0) == 1
    )

    true_180d_itt_effect = (
        (saved_count / n_unflagged_treat) if n_unflagged_treat > 0 else 0.0
    )

    sec_180d = eval_results.get("experiment", {}).get("secondary_180d", {})
    est_lift = float(sec_180d.get("absolute_lift", 0.0))
    ci_low = float(sec_180d.get("ci_95_low", 0.0))
    ci_high = float(sec_180d.get("ci_95_high", 0.0))

    ci_contains_true = bool(ci_low <= true_180d_itt_effect <= ci_high)

    # -------------------------------------------------------------------------
    # 3. Build Structured Audit Result
    # -------------------------------------------------------------------------
    audit_results: dict[str, Any] = {
        "scale": scale,
        "overall_status": "PASS" if all_perfect else "FAIL",
        "detector_summary": {
            "all_detectors_perfect": all_perfect,
            "total_ground_truth": total_gt,
            "total_detected": total_det,
            "overall_precision": float(overall_prec),
            "overall_recall": float(overall_rec),
        },
        "detectors": detector_scores,
        "estimator_audit": {
            "unflagged_w01_treatment_count": n_unflagged_treat,
            "true_saved_count": saved_count,
            "true_180d_itt_effect": float(true_180d_itt_effect),
            "estimated_180d_itt_lift": est_lift,
            "ci_95_low": ci_low,
            "ci_95_high": ci_high,
            "ci_contains_true_effect": ci_contains_true,
        },
    }

    # -------------------------------------------------------------------------
    # 4. Generate Markdown Report
    # -------------------------------------------------------------------------
    status_badge = "**PASS**" if all_perfect else "**FAIL**"
    ci_badge = "YES (VALID)" if ci_contains_true else "NO (OUTSIDE CI)"

    lines = [
        f"# Ground Truth Audit Report ({scale})",
        "",
        f"**Audit Status**: {status_badge}",
        f"**Detector Target**: 100% Precision and 100% Recall on all anomalies (A, B, C, D)",
        "",
        "## 1. Detector Performance vs Ground Truth",
        "",
        "| Detector Rule | Type | Severity | Ground Truth | Detected | TP | FP | FN | Precision | Recall | Status |",
        "| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]

    for rid, sc in sorted(detector_scores.items()):
        lines.append(
            f"| `{sc['rule_id']}` | {sc['anomaly_type']} | {sc['severity']} | "
            f"{sc['ground_truth_count']} | {sc['detected_count']} | "
            f"{sc['tp']} | {sc['fp']} | {sc['fn']} | "
            f"{sc['precision']:.4f} | {sc['recall']:.4f} | **{sc['status']}** |"
        )

    lines.extend(
        [
            "",
            "## 2. Causal Lift Estimator Audit (180-day ITT)",
            "",
            f"- **Unflagged W01 Treatment Population**: {n_unflagged_treat}",
            f"- **Ground Truth Saved Customers (`true_effect_flag == 1`)**: {saved_count}",
            f"- **True 180-day ITT Treatment Effect**: `{true_180d_itt_effect:.4f}` ({true_180d_itt_effect * 100:.2f}%)",
            f"- **Estimated 180-day ITT Lift**: `{est_lift:+.4f}` ({est_lift * 100:+.2f} pp)",
            f"- **Estimated 95% Confidence Interval**: `[{ci_low:+.4f}, {ci_high:+.4f}]` ([{ci_low * 100:+.2f} pp, {ci_high * 100:+.2f} pp])",
            f"- **CI Contains True Effect**: **{ci_badge}**",
            "",
            "## 3. Overall Audit Verdict",
            "",
            f"**AUDIT STATUS: {'PASS' if all_perfect else 'FAIL'}**",
            "",
        ]
    )

    report_md = "\n".join(lines)

    # Write files if output_dir provided
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "audit_report.json"
        md_path = output_dir / "audit_report.md"
        json_path.write_text(json.dumps(audit_results, indent=2), encoding="utf-8")
        md_path.write_text(report_md, encoding="utf-8")

    return audit_results, report_md, all_perfect
