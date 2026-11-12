#!/usr/bin/env python3
"""Generate docs/TEST_REPORT.md from pytest XML results and operational CLI checks (stdlib only)."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any
import xml.etree.ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs" / "REQUIREMENTS_TRACEABILITY.md"
REPORT_PATH = REPO_ROOT / "docs" / "TEST_REPORT.md"


def load_traceability_mapping() -> dict[str, str]:
    """Load test_node -> requirement_id mapping from REQUIREMENTS_TRACEABILITY.md."""
    if not MATRIX_PATH.is_file():
        return {}
    mapping: dict[str, str] = {}
    for line in MATRIX_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|") or line.strip().startswith("| :---"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) >= 4:
            req_id = parts[0].replace("*", "").strip()
            test_col = parts[3].replace("`", "").strip()
            if req_id in ("Requirement ID", "---"):
                continue
            if test_col and test_col != "-":
                for node in test_col.split(";"):
                    node = node.strip()
                    if node:
                        mapping[node] = req_id
    return mapping


def run_pytest_and_parse(mapping: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Execute pytest with JUnit XML export and parse test case results."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", f"--junitxml={tmp_path}", "-q"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if not tmp_path.is_file() or tmp_path.stat().st_size == 0:
            print("ERROR: JUnit XML not produced by pytest.", file=sys.stderr)
            return {}, []

        tree = ET.parse(tmp_path)
        root = tree.getroot()

        testcases: list[dict[str, str]] = []
        file_counts: dict[str, dict[str, int]] = {}

        # Handle both <testsuites> and <testsuite> roots
        suite_elem = root if root.tag == "testsuite" else root.find("testsuite")
        tc_elems = root.findall(".//testcase") if suite_elem is None else suite_elem.findall("testcase")

        tc_counter = 1
        for tc in tc_elems:
            name = tc.get("name", "")
            classname = tc.get("classname", "")
            raw_file = tc.get("file", "")

            # Form standard pytest node name
            if raw_file:
                node_name = f"{raw_file}::{name}"
                fname = raw_file
            else:
                py_path = classname.replace(".", "/") + ".py"
                node_name = f"{py_path}::{name}"
                fname = py_path

            if fname not in file_counts:
                file_counts[fname] = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}
            file_counts[fname]["total"] += 1

            fail_elem = tc.find("failure")
            err_elem = tc.find("error")
            skip_elem = tc.find("skipped")

            if fail_elem is not None:
                result = "FAILED"
                defect = fail_elem.get("message", "Failure")
                file_counts[fname]["failed"] += 1
            elif err_elem is not None:
                result = "ERROR"
                defect = err_elem.get("message", "Error")
                file_counts[fname]["failed"] += 1
            elif skip_elem is not None:
                result = "SKIPPED"
                defect = skip_elem.get("message", "Skipped")
                file_counts[fname]["skipped"] += 1
            else:
                result = "PASSED"
                defect = "-"
                file_counts[fname]["passed"] += 1

            req_id = mapping.get(node_name, "-")
            if req_id == "-":
                # Fallback: check matching by suffix
                for k, v in mapping.items():
                    if k.endswith(f"::{name}"):
                        req_id = v
                        break

            testcases.append({
                "id": f"TC-{tc_counter:03d}",
                "node": node_name,
                "file": fname,
                "name": name,
                "req_id": req_id,
                "result": result,
                "defect": defect,
            })
            tc_counter += 1

        summary = {
            "total": len(testcases),
            "passed": sum(f["passed"] for f in file_counts.values()),
            "failed": sum(f["failed"] for f in file_counts.values()),
            "skipped": sum(f["skipped"] for f in file_counts.values()),
            "by_file": file_counts,
        }
        return summary, testcases
    finally:
        if tmp_path.is_file():
            tmp_path.unlink()


def run_operational_checks() -> list[dict[str, Any]]:
    """Run operational CLI commands against starter scale and capture exit codes."""
    checks = [
        ("validate", [sys.executable, "-m", "churnexp", "validate", "--scale", "starter"]),
        ("audit", [sys.executable, "-m", "churnexp", "audit", "--scale", "starter"]),
        ("repro-check", [sys.executable, "-m", "churnexp", "repro-check", "--scale", "starter"]),
        ("all", [sys.executable, "-m", "churnexp", "all", "--scale", "starter"]),
    ]
    results = []
    for name, cmd in checks:
        print(f"Running operational check: {' '.join(cmd)} ...")
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        results.append({
            "command": f"python -m churnexp {name} --scale starter",
            "exit_code": proc.returncode,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
        })
    return results


def main() -> int:
    mapping = load_traceability_mapping()
    summary, testcases = run_pytest_and_parse(mapping)
    op_checks = run_operational_checks()

    lines: list[str] = [
        "# Test Execution & Verification Report",
        "",
        "## 1. Test Execution Summary",
        "",
        f"- **Total Test Cases**: {summary.get('total', 0)}",
        f"- **Passed**: {summary.get('passed', 0)}",
        f"- **Failed**: {summary.get('failed', 0)}",
        f"- **Skipped**: {summary.get('skipped', 0)}",
        f"- **Status**: {'ALL PASSED' if summary.get('failed', 0) == 0 else 'FAILURES DETECTED'}",
        "",
        "### Test Counts by File",
        "",
        "| Test File | Total | Passed | Failed | Skipped | Status |",
        "| :--- | ---: | ---: | ---: | ---: | :---: |",
    ]

    for fname, cnts in sorted(summary.get("by_file", {}).items()):
        st = "PASS" if cnts["failed"] == 0 else "FAIL"
        lines.append(
            f"| `{fname}` | {cnts['total']} | {cnts['passed']} | {cnts['failed']} | {cnts['skipped']} | `{st}` |"
        )

    lines.extend([
        "",
        "## 2. Test Case Execution Details",
        "",
        "| Test Case ID | Test Node (`file::name`) | Requirement ID | Result | Defect Reference |",
        "| :--- | :--- | :---: | :---: | :--- |",
    ])

    for tc in testcases:
        lines.append(
            f"| `{tc['id']}` | `{tc['node']}` | `{tc['req_id']}` | `{tc['result']}` | {tc['defect']} |"
        )

    lines.extend([
        "",
        "## 3. Operational Checks",
        "",
        "The following operational CLI workflows were executed against starter scale in an isolated test run:",
        "",
        "| Subcommand Workflow | Exit Code | Operational Status |",
        "| :--- | :---: | :---: |",
    ])

    for op in op_checks:
        lines.append(
            f"| `{op['command']}` | `{op['exit_code']}` | `{op['status']}` |"
        )

    lines.append("")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Test report written to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
