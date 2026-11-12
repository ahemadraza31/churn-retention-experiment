import re
import sqlite3
from pathlib import Path
from churnexp.schema.db import create_database

DICTIONARY_PATH = Path(__file__).resolve().parents[2] / "docs" / "03_data_dictionary.md"

def _load_dictionary() -> dict:
    """Parse the data dictionary markdown into a mapping {table: set(columns)}.
    Very simple parser: looks for '## table_name' headings and the markdown table that follows.
    """
    table_to_cols = {}
    current_table = None
    in_table = False
    for line in DICTIONARY_PATH.read_text().splitlines():
        heading = re.match(r"##\s+(\w+)", line)
        if heading:
            current_table = heading.group(1).strip().lower()
            table_to_cols[current_table] = set()
            in_table = False
            continue
        if current_table and line.startswith("|"):
            # header separator or row
            parts = [p.strip() for p in line.strip("|\n").split("|")]
            if parts[0].lower() == "column":
                # header row, start collecting data rows next lines
                in_table = True
                continue
            if in_table and parts:
                col_name = parts[0]
                if col_name and col_name != '---' and not col_name.startswith('**'):
                    table_to_cols[current_table].add(col_name)
        elif current_table and line.strip() == "":
            in_table = False
    return table_to_cols


def test_dictionary_sync():
    # Load dictionary mapping
    dict_map = _load_dictionary()
    # Open an in‑memory DB with the schema
    conn = create_database()
    cur = conn.cursor()
    # Get list of tables from sqlite_master
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0].lower() for row in cur.fetchall()}
    # Verify every table has a dictionary section
    for table in tables:
        assert table in dict_map, f"Table {table} missing from data dictionary"
        # Get columns from PRAGMA
        cur.execute(f"PRAGMA table_info({table});")
        cols = {row[1] for row in cur.fetchall()}
        # Ensure each column appears in dictionary
        missing = cols - dict_map[table]
        assert not missing, f"Columns {missing} of table {table} missing from dictionary"
        # Ensure dictionary does not list extra columns
        extra = dict_map[table] - cols
        assert not extra, f"Dictionary lists unknown columns {extra} for table {table}"


def test_ground_truth_dictionary_headers_match_csv():
    """Verify docs/03_data_dictionary.md ground-truth column lists match real CSV headers at starter scale."""
    repo_root = Path(__file__).resolve().parents[2]
    gt_dir = repo_root / "data" / "starter" / "ground_truth"
    assert gt_dir.is_dir(), f"Starter ground_truth directory missing at {gt_dir}"

    dict_text = DICTIONARY_PATH.read_text(encoding="utf-8")

    # Parse ground truth files and their documented columns from markdown
    # Matches patterns like: **`filename.csv`**: followed by bullet items: - `col_name`:
    gt_docs: dict[str, list[str]] = {}
    current_csv = None
    for line in dict_text.splitlines():
        csv_match = re.search(r"\*\*`(\w+\.csv)`\*\*", line)
        if csv_match:
            current_csv = csv_match.group(1)
            gt_docs[current_csv] = []
            continue
        if current_csv:
            col_match = re.match(r"^\s*-\s*`(\w+)`:", line)
            if col_match:
                gt_docs[current_csv].append(col_match.group(1))
            elif line.startswith("## ") or (line.startswith("---") and not line.startswith("--- ")):
                current_csv = None

    assert "anomalies.csv" in gt_docs
    assert "expected_decisions.csv" in gt_docs
    assert "latent_customer_state.csv" in gt_docs

    for fname in ["anomalies.csv", "expected_decisions.csv", "latent_customer_state.csv"]:
        csv_path = gt_dir / fname
        assert csv_path.is_file(), f"Expected ground-truth file {csv_path} does not exist"
        header_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
        real_cols = [c.strip() for c in header_line.split(",")]
        doc_cols = gt_docs[fname]

        assert doc_cols == real_cols, (
            f"Ground-truth columns mismatch for {fname}:\n"
            f"  Documented: {doc_cols}\n"
            f"  Real CSV:   {real_cols}"
        )

