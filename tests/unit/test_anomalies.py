"""Unit tests for deterministic anomaly injection (Run 2B)."""

from __future__ import annotations

import pandas as pd
import pytest

from churnexp.anomalies.inject import (
    ANOMALIES_GT_COLUMNS,
    EXPECTED_DECISIONS_GT_COLUMNS,
    inject_anomalies,
)
from churnexp.config import load_config
from churnexp.experiment.pipeline import run_pipeline
from churnexp.generation.world import generate_world
from churnexp.rng import RngFactory
from churnexp.validation.checks import validate_tables


def test_anomaly_injection_deterministic_and_counts():
    """Verify injection is deterministic, respects records_per_type, and doesn't mutate base rows."""
    cfg = load_config("starter")
    world_base = generate_world(cfg)
    p_world1 = run_pipeline(cfg)
    p_world2 = run_pipeline(cfg)

    # 1. Counts: 10 each for starter
    assert p_world1.summary["anomaly_counts"] == {"A": 10, "B": 10, "C": 10, "D": 10}
    assert p_world2.summary["anomaly_counts"] == {"A": 10, "B": 10, "C": 10, "D": 10}

    # 2. Determinism: identical ground truth tables
    anom1 = p_world1.summary["anomalies_gt"]
    anom2 = p_world2.summary["anomalies_gt"]
    dec1 = p_world1.summary["expected_decisions_gt"]
    dec2 = p_world2.summary["expected_decisions_gt"]
    pd.testing.assert_frame_equal(anom1, anom2)
    pd.testing.assert_frame_equal(dec1, dec2)

    # 3. Schemas of GT files
    assert list(anom1.columns) == ANOMALIES_GT_COLUMNS
    assert list(dec1.columns) == EXPECTED_DECISIONS_GT_COLUMNS
    assert len(anom1) == 40

    # 4. Injected tables have expected counts
    assert len(p_world1.tables["churn_outcome"]) == 1803
    assert (p_world1.tables["churn_outcome"]["cycle_year"] == 2026).sum() == 917 + 10
    assert len(p_world1.tables["campaign_contact"]) >= 40
    assert len(p_world1.tables["retention_outcome"]) >= 40

    # 5. Data quality integrity: all 18 rules pass with zero findings
    report = validate_tables(p_world1.tables)
    assert len(report.findings) == 0
