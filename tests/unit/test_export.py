"""Unit tests for database exports (CSV, JSON, SQL, MANIFEST.json, and ground-truth isolation)."""

from pathlib import Path
import sqlite3
import pandas as pd
import pytest

from churnexp.cli import run_generate
from churnexp.config import load_config
from churnexp.io.exporters import (
    export_database,
    hash_db_tables,
    load_canonical_tables_from_csv,
    load_canonical_tables_from_db,
    load_canonical_tables_from_json,
)


@pytest.fixture(scope="module")
def generated_starter_env(tmp_path_factory):
    base = tmp_path_factory.mktemp("export_test")
    gen_dir = base / "out_starter"
    exp_dir1 = base / "data_starter_1"
    exp_dir2 = base / "data_starter_2"

    ret = run_generate(scale="starter", output_dir=gen_dir)
    assert ret == 0

    cfg = load_config("starter")
    db_path = gen_dir / "churnexp.db"
    gt_dir = gen_dir / "ground_truth"

    m1 = export_database(
        db_path=db_path,
        export_dir=exp_dir1,
        cfg=cfg,
        formats=["csv", "json", "sql"],
        source_gt_dir=gt_dir,
        write_root_source_manifest=False,
    )
    m2 = export_database(
        db_path=db_path,
        export_dir=exp_dir2,
        cfg=cfg,
        formats=["csv", "json", "sql"],
        source_gt_dir=gt_dir,
        write_root_source_manifest=False,
    )
    return {
        "db_path": db_path,
        "exp_dir1": exp_dir1,
        "exp_dir2": exp_dir2,
        "m1": m1,
        "m2": m2,
    }


def test_exported_csv_reloaded_equals_db_tables(generated_starter_env):
    """Exported CSV files re-loaded equal the DB tables."""
    db_path = generated_starter_env["db_path"]
    csv_dir = generated_starter_env["exp_dir1"] / "csv"

    conn = sqlite3.connect(str(db_path))
    try:
        db_tables = load_canonical_tables_from_db(conn)
    finally:
        conn.close()

    csv_tables = load_canonical_tables_from_csv(csv_dir)
    assert set(db_tables.keys()) == set(csv_tables.keys())

    for tbl in db_tables:
        pd.testing.assert_frame_equal(
            db_tables[tbl],
            csv_tables[tbl],
            check_dtype=False,
            obj=f"CSV vs DB table {tbl}",
        )


def test_exported_json_equals_csv(generated_starter_env):
    """Exported JSON files re-loaded equal the exported CSV tables."""
    exp_dir = generated_starter_env["exp_dir1"]
    csv_tables = load_canonical_tables_from_csv(exp_dir / "csv")
    json_tables = load_canonical_tables_from_json(exp_dir / "json")

    assert set(csv_tables.keys()) == set(json_tables.keys())
    for tbl in csv_tables:
        pd.testing.assert_frame_equal(
            csv_tables[tbl],
            json_tables[tbl],
            check_dtype=False,
            obj=f"JSON vs CSV table {tbl}",
        )


def test_schema_and_seed_sql_reproduce_identical_table_hashes(generated_starter_env):
    """schema.sql + seed.sql loaded into a fresh in-memory DB gives identical per-table hashes."""
    db_path = generated_starter_env["db_path"]
    sql_dir = generated_starter_env["exp_dir1"] / "sql"

    src_conn = sqlite3.connect(str(db_path))
    try:
        src_hashes = hash_db_tables(src_conn)
    finally:
        src_conn.close()

    mem_conn = sqlite3.connect(":memory:")
    try:
        mem_cur = mem_conn.cursor()
        mem_cur.execute("PRAGMA foreign_keys = ON;")
        schema_sql = (sql_dir / "schema.sql").read_text(encoding="utf-8")
        seed_sql = (sql_dir / "seed.sql").read_text(encoding="utf-8")
        mem_cur.executescript(schema_sql)
        mem_cur.executescript(seed_sql)
        mem_hashes = hash_db_tables(mem_conn)
    finally:
        mem_conn.close()

    assert src_hashes == mem_hashes


def test_two_exports_of_same_db_are_byte_identical(generated_starter_env):
    """Two exports of the same DB produce byte-identical files across csv/, json/, sql/, ground_truth/, and MANIFEST.json."""
    dir1: Path = generated_starter_env["exp_dir1"]
    dir2: Path = generated_starter_env["exp_dir2"]

    files1 = sorted(p.relative_to(dir1).as_posix() for p in dir1.rglob("*") if p.is_file())
    files2 = sorted(p.relative_to(dir2).as_posix() for p in dir2.rglob("*") if p.is_file())
    assert files1 == files2
    assert "MANIFEST.json" in files1

    for rel in files1:
        b1 = (dir1 / rel).read_bytes()
        b2 = (dir2 / rel).read_bytes()
        assert b1 == b2, f"Byte mismatch in exported file {rel}"


def test_no_ground_truth_strings_in_csv_json_sql(generated_starter_env):
    """No file under csv/, json/, or sql/ contains hidden_segment or untreated_churn_date."""
    exp_dir: Path = generated_starter_env["exp_dir1"]
    forbidden = ("hidden_segment", "untreated_churn_date")

    checked_count = 0
    for subdir in ("csv", "json", "sql"):
        sdir = exp_dir / subdir
        assert sdir.is_dir()
        for fp in sdir.rglob("*"):
            if fp.is_file():
                checked_count += 1
                text = fp.read_text(encoding="utf-8")
                for bad in forbidden:
                    assert bad not in text, f"Forbidden string {bad!r} found in {fp}"
    assert checked_count > 0

    # Meanwhile ground_truth/latent_customer_state.csv DOES exist and has both columns
    gt_file = exp_dir / "ground_truth" / "latent_customer_state.csv"
    assert gt_file.is_file()
    gt_header = gt_file.read_text(encoding="utf-8").splitlines()[0]
    assert "hidden_segment" in gt_header
    assert "untreated_churn_date" in gt_header

