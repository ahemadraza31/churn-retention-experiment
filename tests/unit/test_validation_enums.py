"""Unit test verifying that validation.enums agrees with all column IN (...) CHECK clauses in schema.sql."""

import importlib.resources
import re

from churnexp.validation.enums import ALLOWED_STATE_TRANSITIONS, TABLE_COLUMN_ENUMS


def _parse_schema_enums() -> dict[str, dict[str, set[str | int]]]:
    schema_text = (
        importlib.resources.files("churnexp.schema")
        .joinpath("schema.sql")
        .read_text(encoding="utf-8")
    )
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);", re.DOTALL | re.IGNORECASE
    )
    col_in_pattern = re.compile(
        r"^\s*(\w+)\s+(?:TEXT|INTEGER|REAL)\b[^\n]*?\bCHECK\s*\(\s*\1\s+IN\s*\(([^)]+)\)\s*\)",
        re.IGNORECASE | re.MULTILINE,
    )

    parsed: dict[str, dict[str, set[str | int]]] = {}
    for tbl_match in table_pattern.finditer(schema_text):
        tbl_name = tbl_match.group(1).lower()
        body = tbl_match.group(2)
        col_map: dict[str, set[str | int]] = {}
        for col_match in col_in_pattern.finditer(body):
            col_name = col_match.group(1).lower()
            raw_vals = col_match.group(2)
            vals: set[str | int] = set()
            for token in raw_vals.split(","):
                tok = token.strip()
                if tok.startswith("'") and tok.endswith("'"):
                    vals.add(tok[1:-1])
                else:
                    vals.add(int(tok))
            col_map[col_name] = vals
        if col_map:
            parsed[tbl_name] = col_map
    return parsed


def test_enums_match_schema_sql_check_clauses():
    """Verify TABLE_COLUMN_ENUMS in enums.py matches every column IN (...) CHECK in schema.sql."""
    schema_enums = _parse_schema_enums()
    assert set(TABLE_COLUMN_ENUMS.keys()) == set(schema_enums.keys())
    for tbl, cols in schema_enums.items():
        assert TABLE_COLUMN_ENUMS[tbl] == cols, f"Enum mismatch on table {tbl!r}"


def test_allowed_state_transitions_defined():
    """Verify ALLOWED_STATE_TRANSITIONS covers all three state_event entity types."""
    assert set(ALLOWED_STATE_TRANSITIONS.keys()) == {
        "CUSTOMER",
        "SUBSCRIPTION",
        "CAMPAIGN_CONTACT",
    }
    assert ("INIT", "ACTIVE") in ALLOWED_STATE_TRANSITIONS["CUSTOMER"]
    assert ("ACTIVE", "CHURNED") in ALLOWED_STATE_TRANSITIONS["CUSTOMER"]
    assert ("INIT", "ACTIVE") in ALLOWED_STATE_TRANSITIONS["SUBSCRIPTION"]
    assert ("ACTIVE", "CANCELLED") in ALLOWED_STATE_TRANSITIONS["SUBSCRIPTION"]
    assert ("ACTIVE", "EXPIRED") in ALLOWED_STATE_TRANSITIONS["SUBSCRIPTION"]

