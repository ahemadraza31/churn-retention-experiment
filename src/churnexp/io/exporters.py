"""Generic database exporters for CSV, JSON, SQL (schema + seed), and ground-truth copy."""

import csv
import hashlib
import importlib.resources
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Sequence
import pandas as pd

from churnexp.config import Config, load_config
from churnexp.io.manifest import build_manifest, write_manifest, write_source_manifest
from churnexp.schema.db import create_database

VALID_FORMATS: tuple[str, ...] = ("csv", "json", "sql")


def default_formats_for_scale(scale: str) -> tuple[str, ...]:
    """Return default export formats: all three for starter, csv only for full."""
    if scale.lower() == "starter":
        return ("csv", "json", "sql")
    return ("csv",)


def parse_formats(formats_arg: str | Sequence[str] | None, scale: str) -> list[str]:
    """Parse comma-separated format string or sequence and validate."""
    if formats_arg is None:
        return list(default_formats_for_scale(scale))
    if isinstance(formats_arg, str):
        parts = [p.strip().lower() for p in formats_arg.split(",") if p.strip()]
    else:
        parts = [str(p).strip().lower() for p in formats_arg if str(p).strip()]
    if not parts:
        raise ValueError("At least one export format must be specified")
    for fmt in parts:
        if fmt not in VALID_FORMATS:
            raise ValueError(
                f"Unknown export format {fmt!r}. Valid formats: {', '.join(VALID_FORMATS)}"
            )
    # Deduplicate preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for fmt in parts:
        if fmt not in seen:
            seen.add(fmt)
            ordered.append(fmt)
    return ordered


def get_db_tables_and_columns(
    conn: sqlite3.Connection,
) -> list[tuple[str, list[tuple[str, str]], list[str]]]:
    """Return all DB tables in creation order with [(col_name, col_type)] and [pk_cols]."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid;"
    )
    table_names = [r[0] for r in cur.fetchall()]
    result: list[tuple[str, list[tuple[str, str]], list[str]]] = []

    for tbl in table_names:
        cur.execute(f"PRAGMA table_info({tbl});")
        info = cur.fetchall()
        cols = [(str(r[1]), str(r[2]).upper()) for r in info]
        pks = [
            str(r[1])
            for r in sorted((r for r in info if int(r[5]) > 0), key=lambda x: int(x[5]))
        ]
        result.append((tbl, cols, pks))
    return result


def _sql_literal(val: Any, col_type: str) -> str:
    if val is None:
        return "NULL"
    if col_type == "INTEGER":
        return str(int(val))
    if col_type == "REAL":
        return f"{float(val):.6f}"
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def _csv_cell(val: Any, col_type: str) -> str:
    if val is None:
        return ""
    if col_type == "INTEGER":
        return str(int(val))
    if col_type == "REAL":
        return f"{float(val):.6f}"
    return str(val)


def _json_value(val: Any, col_type: str) -> Any:
    if val is None:
        return None
    if col_type == "INTEGER":
        return int(val)
    if col_type == "REAL":
        return float(f"{float(val):.6f}")
    return str(val)


def export_database(
    db_path: Path | str,
    export_dir: Path | str,
    cfg: Config | None = None,
    formats: Sequence[str] | str | None = None,
    source_gt_dir: Path | str | None = None,
    write_root_source_manifest: bool = True,
) -> dict[str, Any]:
    """Export all tables found in db_path to export_dir in requested formats and write MANIFEST.json."""
    db_p = Path(db_path)
    if not db_p.is_file():
        raise FileNotFoundError(f"Database not found at {db_p}")

    out_dir = Path(export_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if cfg is None:
        cfg = load_config("starter")

    fmt_list = parse_formats(formats, cfg.scale)

    conn = sqlite3.connect(str(db_p))
    try:
        tables_meta = get_db_tables_and_columns(conn)
        cur = conn.cursor()

        table_row_counts: dict[str, int] = {}
        written_files: list[Path] = []

        csv_dir = out_dir / "csv"
        json_dir = out_dir / "json"
        sql_dir = out_dir / "sql"

        if "csv" in fmt_list:
            csv_dir.mkdir(parents=True, exist_ok=True)
        if "json" in fmt_list:
            json_dir.mkdir(parents=True, exist_ok=True)
        if "sql" in fmt_list:
            sql_dir.mkdir(parents=True, exist_ok=True)

        seed_lines: list[str] = ["BEGIN;"] if "sql" in fmt_list else []

        for tbl, cols, pk_cols in tables_meta:
            col_names = [c[0] for c in cols]
            col_types = [c[1] for c in cols]
            cols_sql = ", ".join(col_names)
            order_sql = ", ".join(f"{pk} ASC" for pk in pk_cols) if pk_cols else "rowid ASC"

            cur.execute(f"SELECT {cols_sql} FROM {tbl} ORDER BY {order_sql};")
            rows = cur.fetchall()
            table_row_counts[tbl] = len(rows)

            if "csv" in fmt_list:
                csv_path = csv_dir / f"{tbl}.csv"
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f, lineterminator="\n")
                    writer.writerow(col_names)
                    for row in rows:
                        writer.writerow(
                            [_csv_cell(val, ctype) for val, ctype in zip(row, col_types)]
                        )
                written_files.append(csv_path)

            if "json" in fmt_list:
                json_path = json_dir / f"{tbl}.json"
                json_objs = [
                    {
                        cname: _json_value(val, ctype)
                        for cname, ctype, val in zip(col_names, col_types, row)
                    }
                    for row in rows
                ]
                json_path.write_text(
                    json.dumps(json_objs, indent=2, sort_keys=False) + "\n",
                    encoding="utf-8",
                )
                written_files.append(json_path)

            if "sql" in fmt_list:
                for row in rows:
                    vals_sql = ", ".join(
                        _sql_literal(val, ctype) for val, ctype in zip(row, col_types)
                    )
                    seed_lines.append(
                        f"INSERT INTO {tbl} ({cols_sql}) VALUES ({vals_sql});"
                    )

        if "sql" in fmt_list:
            schema_text = (
                importlib.resources.files("churnexp.schema")
                .joinpath("schema.sql")
                .read_text(encoding="utf-8")
            )
            views_text = (
                importlib.resources.files("churnexp.schema")
                .joinpath("views.sql")
                .read_text(encoding="utf-8")
            )
            combined_schema = schema_text.rstrip() + "\n\n" + views_text.lstrip()
            if not combined_schema.endswith("\n"):
                combined_schema += "\n"

            schema_out_path = sql_dir / "schema.sql"
            schema_out_path.write_text(combined_schema, encoding="utf-8")
            written_files.append(schema_out_path)

            seed_lines.append("COMMIT;")
            seed_out_path = sql_dir / "seed.sql"
            seed_out_path.write_text("\n".join(seed_lines) + "\n", encoding="utf-8")
            written_files.append(seed_out_path)
    finally:
        conn.close()

    # Copy model_info.json if present
    src_model_info = db_p.parent / "model_info.json"
    if src_model_info.is_file():
        dst_model_info = out_dir / "model_info.json"
        if src_model_info.resolve() != dst_model_info.resolve():
            shutil.copyfile(src_model_info, dst_model_info)
        written_files.append(dst_model_info)

    # Copy ground_truth/*.csv unchanged
    if source_gt_dir is None:
        src_gt = db_p.parent / "ground_truth"
    else:
        src_gt = Path(source_gt_dir)

    gt_written: list[Path] = []
    if src_gt.is_dir():
        dst_gt = out_dir / "ground_truth"
        dst_gt.mkdir(parents=True, exist_ok=True)
        for gt_file in sorted(src_gt.glob("*.csv")):
            dst_file = dst_gt / gt_file.name
            if gt_file.resolve() != dst_file.resolve():
                shutil.copyfile(gt_file, dst_file)
            gt_written.append(dst_file)

    manifest_data = build_manifest(
        cfg=cfg,
        table_row_counts=table_row_counts,
        written_files=written_files,
        ground_truth_files=gt_written,
        base_dir=out_dir,
    )
    write_manifest(manifest_data, out_dir)

    if write_root_source_manifest:
        write_source_manifest(out_dir.parent)

    return manifest_data


def _canonicalize_dataframe(
    df: pd.DataFrame,
    cols: list[tuple[str, str]],
    pk_cols: list[str],
) -> pd.DataFrame:
    """Normalize column order, row sort order, and types for exact cross-format comparison."""
    col_names = [c[0] for c in cols]
    if df.empty:
        return pd.DataFrame(columns=col_names)

    out = df[col_names].copy()
    for cname, ctype in cols:
        s = out[cname]
        if ctype == "INTEGER":
            is_null = s.isna() | (s == "")
            if is_null.any():
                out[cname] = pd.Series(
                    [None if pd.isna(v) or v == "" else int(float(v)) for v in s],
                    index=out.index,
                    dtype=object,
                )
            else:
                out[cname] = s.astype("int64")
        elif ctype == "REAL":
            out[cname] = pd.to_numeric(s, errors="coerce").round(6).astype("float64")
        else:
            out[cname] = pd.Series(
                [None if pd.isna(v) or v == "" else str(v) for v in s],
                index=out.index,
                dtype=object,
            )

    if pk_cols:
        out = out.sort_values(pk_cols, kind="mergesort").reset_index(drop=True)
    else:
        out = out.reset_index(drop=True)
    return out


def load_canonical_tables_from_db(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Load all DB tables normalized to canonical column types and sorted by PK."""
    meta = get_db_tables_and_columns(conn)
    result: dict[str, pd.DataFrame] = {}
    for tbl, cols, pk_cols in meta:
        raw_df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
        result[tbl] = _canonicalize_dataframe(raw_df, cols, pk_cols)
    return result


def load_canonical_tables_from_csv(csv_dir: Path | str) -> dict[str, pd.DataFrame]:
    """Load exported CSV files normalized to canonical schema column types and sorted by PK."""
    cdir = Path(csv_dir)
    schema_conn = create_database(":memory:")
    try:
        meta = get_db_tables_and_columns(schema_conn)
    finally:
        schema_conn.close()

    result: dict[str, pd.DataFrame] = {}
    for tbl, cols, pk_cols in meta:
        csv_path = cdir / f"{tbl}.csv"
        if not csv_path.is_file():
            continue
        raw_df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        result[tbl] = _canonicalize_dataframe(raw_df, cols, pk_cols)
    return result


def load_canonical_tables_from_json(json_dir: Path | str) -> dict[str, pd.DataFrame]:
    """Load exported JSON files normalized to canonical schema column types and sorted by PK."""
    jdir = Path(json_dir)
    schema_conn = create_database(":memory:")
    try:
        meta = get_db_tables_and_columns(schema_conn)
    finally:
        schema_conn.close()

    result: dict[str, pd.DataFrame] = {}
    for tbl, cols, pk_cols in meta:
        json_path = jdir / f"{tbl}.json"
        if not json_path.is_file():
            continue
        records = json.loads(json_path.read_text(encoding="utf-8"))
        raw_df = pd.DataFrame(records, columns=[c[0] for c in cols])
        result[tbl] = _canonicalize_dataframe(raw_df, cols, pk_cols)
    return result


def hash_db_tables(conn: sqlite3.Connection) -> dict[str, str]:
    """Compute deterministic SHA-256 hash per table in a SQLite connection."""
    meta = get_db_tables_and_columns(conn)
    cur = conn.cursor()
    hashes: dict[str, str] = {}

    for tbl, cols, pk_cols in meta:
        col_names = [c[0] for c in cols]
        col_types = [c[1] for c in cols]
        cols_sql = ", ".join(col_names)
        order_sql = ", ".join(f"{pk} ASC" for pk in pk_cols) if pk_cols else "rowid ASC"
        cur.execute(f"SELECT {cols_sql} FROM {tbl} ORDER BY {order_sql};")
        rows = cur.fetchall()

        h = hashlib.sha256()
        h.update((",".join(col_names) + "\n").encode("utf-8"))
        for row in rows:
            line = ",".join(_csv_cell(val, ctype) for val, ctype in zip(row, col_types)) + "\n"
            h.update(line.encode("utf-8"))
        hashes[tbl] = h.hexdigest()

    return hashes

