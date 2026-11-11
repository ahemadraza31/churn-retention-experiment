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
