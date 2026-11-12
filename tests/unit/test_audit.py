"""Unit tests for ground truth audit module (Run 2B)."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from churnexp.audit.score import run_audit
from churnexp.cli import run_generate
from churnexp.config import load_config
from churnexp.evaluation.report import run_evaluation
from churnexp.validation.checks import load_tables_from_db


def test_audit_perfect_precision_recall_on_starter(tmp_path):
    """Detectors achieve 100% precision and recall against ground truth on generated starter."""
    out_dir = tmp_path / "starter"
    ret = run_generate(scale="starter", output_dir=out_dir)
    assert ret == 0

    db_path = out_dir / "churnexp.db"
    gt_dir = out_dir / "ground_truth"

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        tables = load_tables_from_db(conn)
    finally:
        conn.close()

    eval_results, _ = run_evaluation(tables, output_dir=out_dir, scale="starter")
    audit_dict, report_md, passed = run_audit(
        tables=tables,
        gt_dir=gt_dir,
        output_dir=out_dir,
        scale="starter",
    )

    assert passed is True
    assert audit_dict["overall_status"] == "PASS"

    # All 4 detectors have 1.0 precision and recall
    for rid, sc in audit_dict["detectors"].items():
        assert sc["precision"] == 1.0, f"Precision failed for {rid}: {sc}"
        assert sc["recall"] == 1.0, f"Recall failed for {rid}: {sc}"
        assert sc["ground_truth_count"] == 10
        assert sc["detected_count"] == 10

    # Estimator check: CI contains true effect
    est = audit_dict["estimator_audit"]
    assert est["unflagged_w01_treatment_count"] > 0
    assert est["true_180d_itt_effect"] >= 0.0
    assert est["ci_contains_true_effect"] is True
    assert (out_dir / "audit_report.json").is_file()
    assert (out_dir / "audit_report.md").is_file()
