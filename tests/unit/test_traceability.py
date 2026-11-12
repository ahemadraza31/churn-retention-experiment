"""Unit test for requirements traceability matrix synchronization."""

from pathlib import Path
import re
import subprocess
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "01_requirements_spec.md"
MATRIX_PATH = REPO_ROOT / "docs" / "REQUIREMENTS_TRACEABILITY.md"


def _load_collected_pytest_nodes() -> set[str]:
    """Execute pytest --collect-only -q to gather all available test node names."""
    proc = subprocess.run(
        [".venv/bin/python", "-m", "pytest", "--collect-only", "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    nodes = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "::" in line and not line.startswith("no tests") and not line.endswith("collected"):
            # Strip trailing status or parameters if any
            node = line.split(" ")[0]
            nodes.add(node)
    return nodes


def test_spec_and_matrix_traceability_sync():
    """Verify every FR, NFR, and AC in spec appears in the matrix, and every cited test node exists."""
    assert SPEC_PATH.is_file(), f"Requirements spec missing at {SPEC_PATH}"
    assert MATRIX_PATH.is_file(), f"Traceability matrix missing at {MATRIX_PATH}"

    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    matrix_text = MATRIX_PATH.read_text(encoding="utf-8")

    # 1. Extract IDs from spec (FR-01..FR-20, NFR-01..NFR-07, AC-01..AC-12)
    spec_ids = set(re.findall(r"\*\*(FR-\d{2}|NFR-\d{2}|AC-\d{2})\*\*", spec_text))
    assert len(spec_ids) >= 39, f"Expected at least 39 requirements in spec, found {len(spec_ids)}"

    # 2. Parse matrix table rows
    matrix_req_ids = set()
    cited_test_nodes = set()

    for line in matrix_text.splitlines():
        if not line.strip().startswith("|") or line.strip().startswith("| :---"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) >= 4:
            # Column 0: Requirement ID (e.g. **FR-01**)
            raw_id = parts[0].replace("*", "").strip()
            if raw_id in ("Requirement ID", "---"):
                continue
            matrix_req_ids.add(raw_id)

            # Column 3: Tests (pytest node names)
            test_col = parts[3].replace("`", "").strip()
            if test_col and test_col != "-":
                for node in test_col.split(";"):
                    node = node.strip()
                    if node:
                        cited_test_nodes.add(node)

    # 3. Assert every requirement from spec appears in matrix
    missing_in_matrix = spec_ids - matrix_req_ids
    assert not missing_in_matrix, f"Requirements in spec missing from traceability matrix: {missing_in_matrix}"

    # 4. Assert every cited test node exists in collected pytest nodes
    available_nodes = _load_collected_pytest_nodes()
    missing_nodes = cited_test_nodes - available_nodes
    assert not missing_nodes, f"Traceability matrix cites non-existent test nodes: {missing_nodes}"

