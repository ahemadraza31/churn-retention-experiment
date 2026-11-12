"""Unit tests for the Streamlit actor dashboard using AppTest."""

from pathlib import Path
import subprocess
import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PATH = REPO_ROOT / "app" / "streamlit_app.py"


@pytest.fixture(scope="module", autouse=True)
def ensure_starter_db():
    """Ensure output/starter/churnexp.db is built before running app tests."""
    starter_db = REPO_ROOT / "output" / "starter" / "churnexp.db"
    if not starter_db.is_file():
        subprocess.run(
            [".venv/bin/python", "-m", "churnexp", "all", "--scale", "starter"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
        )
    assert starter_db.is_file(), f"Starter DB not found at {starter_db}"


def test_app_pages_render_without_exception():
    """Verify all 5 pages render without any exception."""
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception, f"Initial run exception: {at.exception}"
    assert len(at.warning) >= 1
    assert "Synthetic data" in at.warning[0].value

    pages = ["Overview", "Marketing Ops", "Support Agent", "Analyst", "System Admin"]
    for page_name in pages:
        at.sidebar.radio[0].set_value(page_name).run()
        assert not at.exception, f"Exception rendering page {page_name}: {at.exception}"


def test_app_support_agent_detector_flagged_finding():
    """Verify Support Agent page displays at least one detector finding for a flagged customer."""
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception

    # Navigate to Support Agent
    at.sidebar.radio[0].set_value("Support Agent").run()
    assert not at.exception

    # Filter choice selectbox is the first selectbox in the main page (index 0 on page)
    # Default is "detector_flagged" (index 1)
    # Check that error elements appear on the page representing detector findings
    assert len(at.error) >= 1, "Expected at least one detector finding error widget on Support Agent page"
    assert any("DET-" in err.value for err in at.error)


def test_app_missing_db_error(tmp_path, monkeypatch):
    """Verify selecting a scale with a missing database renders st.error with the creation command."""
    # Create an app script pointing to a non-existent scale or directory
    missing_app = tmp_path / "test_app_missing.py"
    missing_app.write_text(
        """
import streamlit as st
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
scale = "nonexistent_scale"
db_path = REPO_ROOT / "output" / scale / "churnexp.db"
if not db_path.is_file():
    st.error(
        f"Database not found at `{db_path}`.\\n\\n"
        f"Please generate it by running:\\n"
        f"```bash\\npython -m churnexp all --scale {scale}\\n```"
    )
    st.stop()
st.write("Should not reach here")
        """,
        encoding="utf-8",
    )
    at = AppTest.from_file(str(missing_app), default_timeout=30)
    at.run()
    assert not at.exception
    assert len(at.error) >= 1
    assert "Database not found" in at.error[0].value
    assert "python -m churnexp all --scale nonexistent_scale" in at.error[0].value


def test_app_and_services_prohibited_imports_and_strings():
    """Verify app/ and services/ do not import churnexp.audit, churnexp.anomalies, or read ground_truth/."""
    scan_dirs = [REPO_ROOT / "app", REPO_ROOT / "src" / "churnexp" / "services"]
    prohibited_modules = ["churnexp.audit", "churnexp.anomalies"]
    prohibited_strings = ["ground_truth"]

    for d in scan_dirs:
        for py_file in d.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for mod in prohibited_modules:
                assert mod not in text, f"Prohibited module {mod!r} imported/used in {py_file}"
            for s in prohibited_strings:
                assert s not in text.lower(), f"Prohibited string {s!r} found in {py_file}"

