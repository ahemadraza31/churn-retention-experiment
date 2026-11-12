"""Unit tests for read-only services and queries."""

from pathlib import Path
import sqlite3
import pytest
import pandas as pd

from churnexp.services.queries import (
    campaign_summary,
    customer_360,
    get_ro_connection,
    list_customers,
    load_report,
)


@pytest.fixture(scope="module")
def starter_db_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    db_path = repo_root / "output" / "starter" / "churnexp.db"
    assert db_path.is_file(), f"Expected starter database at {db_path}"
    return db_path


@pytest.fixture(scope="module")
def starter_data_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "data" / "starter"
    assert data_dir.is_dir(), f"Expected starter data dir at {data_dir}"
    return data_dir


def test_list_customers_filters_and_limit(starter_db_path: Path):
    """Verify list_customers handles all filters and limit."""
    # all
    df_all = list_customers(starter_db_path, filter="all")
    assert isinstance(df_all, pd.DataFrame)
    assert len(df_all) == 1000
    assert "customer_id" in df_all.columns

    # limit
    df_lim = list_customers(starter_db_path, filter="all", limit=5)
    assert len(df_lim) == 5

    # churned
    df_churn = list_customers(starter_db_path, filter="churned")
    assert 0 < len(df_churn) <= len(df_all)

    # treated and control
    df_treat = list_customers(starter_db_path, filter="treated")
    df_ctrl = list_customers(starter_db_path, filter="control")
    assert len(df_treat) > 0
    assert len(df_ctrl) > 0

    # eligible
    df_elig = list_customers(starter_db_path, filter="eligible")
    assert len(df_elig) > 0

    # detector_flagged
    df_flagged = list_customers(starter_db_path, filter="detector_flagged")
    assert len(df_flagged) > 0

    # invalid filter
    with pytest.raises(ValueError):
        list_customers(starter_db_path, filter="invalid_filter_name")


def test_customer_360_shape(starter_db_path: Path):
    """Verify customer_360 returns comprehensive dict with valid dataframes."""
    df_flagged = list_customers(starter_db_path, filter="detector_flagged")
    cid = df_flagged.iloc[0]["customer_id"]

    c360 = customer_360(starter_db_path, cid)
    assert c360["customer_id"] == cid
    assert isinstance(c360["profile"], dict)
    assert c360["profile"]["customer_id"] == cid
    assert isinstance(c360["subscriptions"], pd.DataFrame)
    assert isinstance(c360["monthly_usage"], pd.DataFrame)
    assert isinstance(c360["billing_events"], pd.DataFrame)
    assert isinstance(c360["support_cases"], pd.DataFrame)
    assert isinstance(c360["risk_score"], dict)
    assert isinstance(c360["rule_evaluation"], pd.DataFrame)
    assert isinstance(c360["campaign_contacts"], pd.DataFrame)
    assert isinstance(c360["retention_outcomes"], pd.DataFrame)
    assert isinstance(c360["state_events"], pd.DataFrame)
    assert isinstance(c360["detector_findings"], list)
    assert len(c360["detector_findings"]) >= 1


def test_campaign_summary(starter_db_path: Path):
    """Verify campaign_summary aggregates arms and cost exposures."""
    summary = campaign_summary(starter_db_path)
    assert "eligible_counts_by_stratum" in summary
    assert "eligible_counts_by_offer" in summary
    assert "arm_sizes" in summary
    assert "offer_catalog" in summary
    assert "cost_exposure_per_offer" in summary

    assert "TREATMENT" in summary["arm_sizes"]
    assert "CONTROL" in summary["arm_sizes"]
    assert isinstance(summary["offer_catalog"], pd.DataFrame)
    assert len(summary["offer_catalog"]) == 3

    cost_exp = summary["cost_exposure_per_offer"]
    assert isinstance(cost_exp, dict)
    for oid, cost in cost_exp.items():
        assert cost >= 0


def test_load_report(starter_data_dir: Path):
    """Verify load_report parses JSON and text reports and returns None for missing."""
    eval_json = load_report(starter_data_dir, "evaluation_results.json")
    assert isinstance(eval_json, dict)
    assert "experiment" in eval_json

    repro_md = load_report(starter_data_dir, "REPRODUCIBILITY.md")
    assert isinstance(repro_md, str)
    assert "Reproducibility" in repro_md

    missing = load_report(starter_data_dir, "non_existent_file.json")
    assert missing is None


def test_readonly_connection_rejects_insert(starter_db_path: Path):
    """Verify read-only SQLite connection raises OperationalError on INSERT."""
    conn = get_ro_connection(starter_db_path)
    cur = conn.cursor()
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        cur.execute("INSERT INTO customer (customer_id, signup_date) VALUES ('CUS-TEST99', '2026-01-01')")
    conn.close()


def test_services_source_scan_no_forbidden_strings():
    """Verify services directory contains no ground_truth, latent, hidden_segment, or untreated_churn strings."""
    services_dir = Path(__file__).resolve().parents[2] / "src" / "churnexp" / "services"
    forbidden = ["ground_truth", "latent", "hidden_segment", "untreated_churn"]

    for py_file in services_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for term in forbidden:
            assert term not in content, f"Forbidden term {term!r} found in {py_file}"

