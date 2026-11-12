"""End-to-end reproducibility verification across subprocesses with distinct PYTHONHASHSEEDs."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any

from churnexp.io.manifest import file_sha256


@dataclass(frozen=True)
class RunSnapshot:
    label: str
    hashseed: str
    table_row_counts: dict[str, int]
    exported_file_hashes: dict[str, str]
    latent_sha256: str
    aggregates: dict[str, int | float]


@dataclass(frozen=True)
class ReproComparison:
    scale: str
    run1: RunSnapshot
    run2: RunSnapshot
    mismatches: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.mismatches) == 0

    @property
    def status_str(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def format_cli_table(self) -> str:
        lines: list[str] = [
            f"=== Reproducibility Check (scale={self.scale}) ===",
            f"Run 1: PYTHONHASHSEED={self.run1.hashseed} | Run 2: PYTHONHASHSEED={self.run2.hashseed}",
            "",
            "1. Per-Table Row Counts:",
            f"  {'Table':24s} | {'Run 1':>10s} | {'Run 2':>10s} | {'Match':5s}",
            "  " + "-" * 58,
        ]
        all_tables = sorted(
            set(self.run1.table_row_counts.keys()) | set(self.run2.table_row_counts.keys())
        )
        for tbl in all_tables:
            c1 = self.run1.table_row_counts.get(tbl)
            c2 = self.run2.table_row_counts.get(tbl)
            ok = "YES" if c1 == c2 else "NO"
            lines.append(f"  {tbl:24s} | {str(c1):>10s} | {str(c2):>10s} | {ok:5s}")

        lines.extend(
            [
                "",
                "2. Aggregate Metrics:",
                f"  {'Metric':24s} | {'Run 1':>16s} | {'Run 2':>16s} | {'Match':5s}",
                "  " + "-" * 70,
            ]
        )
        all_aggs = list(self.run1.aggregates.keys())
        for k in np_or_unique_keys(all_aggs, list(self.run2.aggregates.keys())):
            v1 = self.run1.aggregates.get(k)
            v2 = self.run2.aggregates.get(k)
            s1 = f"{v1:.6f}" if isinstance(v1, float) else str(v1)
            s2 = f"{v2:.6f}" if isinstance(v2, float) else str(v2)
            ok = "YES" if s1 == s2 else "NO"
            lines.append(f"  {k:24s} | {s1:>16s} | {s2:>16s} | {ok:5s}")

        lines.extend(
            [
                "",
                "3. Ground-Truth Latent File SHA-256:",
                f"  Run 1: {self.run1.latent_sha256}",
                f"  Run 2: {self.run2.latent_sha256}",
                f"  Match: {'YES' if self.run1.latent_sha256 == self.run2.latent_sha256 else 'NO'}",
                "",
                "4. Exported File SHA-256 Hashes:",
                f"  {'File':34s} | {'Run 1 (prefix)':16s} | {'Run 2 (prefix)':16s} | {'Match':5s}",
                "  " + "-" * 80,
            ]
        )
        all_files = sorted(
            set(self.run1.exported_file_hashes.keys())
            | set(self.run2.exported_file_hashes.keys())
        )
        for rel in all_files:
            h1 = self.run1.exported_file_hashes.get(rel, "MISSING")
            h2 = self.run2.exported_file_hashes.get(rel, "MISSING")
            ok = "YES" if h1 == h2 and h1 != "MISSING" else "NO"
            lines.append(f"  {rel:34s} | {h1[:16]:16s} | {h2[:16]:16s} | {ok:5s}")

        if self.mismatches:
            lines.append("")
            lines.append("Mismatches Detected:")
            for m in self.mismatches:
                lines.append(f"  - {m}")

        lines.append("")
        lines.append(f"Reproducibility Result: {self.status_str}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines: list[str] = [
            f"# Reproducibility Report (`scale={self.scale}`)",
            "",
            f"**Result**: **{self.status_str}**",
            "",
            f"- **Run 1 Environment**: `PYTHONHASHSEED={self.run1.hashseed}`",
            f"- **Run 2 Environment**: `PYTHONHASHSEED={self.run2.hashseed}`",
            "",
            "## 1. Per-Table Row Counts",
            "",
            "| Table | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |",
            "| :--- | ---: | ---: | :---: |",
        ]
        all_tables = sorted(
            set(self.run1.table_row_counts.keys()) | set(self.run2.table_row_counts.keys())
        )
        for tbl in all_tables:
            c1 = self.run1.table_row_counts.get(tbl)
            c2 = self.run2.table_row_counts.get(tbl)
            ok = "PASS" if c1 == c2 else "FAIL"
            lines.append(f"| `{tbl}` | {c1} | {c2} | `{ok}` |")

        lines.extend(
            [
                "",
                "## 2. Aggregate Metrics",
                "",
                "| Metric | Run 1 (`PYTHONHASHSEED=1`) | Run 2 (`PYTHONHASHSEED=2`) | Match |",
                "| :--- | ---: | ---: | :---: |",
            ]
        )
        for k in np_or_unique_keys(
            list(self.run1.aggregates.keys()), list(self.run2.aggregates.keys())
        ):
            v1 = self.run1.aggregates.get(k)
            v2 = self.run2.aggregates.get(k)
            s1 = f"{v1:.6f}" if isinstance(v1, float) else str(v1)
            s2 = f"{v2:.6f}" if isinstance(v2, float) else str(v2)
            ok = "PASS" if s1 == s2 else "FAIL"
            lines.append(f"| `{k}` | `{s1}` | `{s2}` | `{ok}` |")

        lat_ok = "PASS" if self.run1.latent_sha256 == self.run2.latent_sha256 else "FAIL"
        lines.extend(
            [
                "",
                "## 3. Latent Ground-Truth File SHA-256",
                "",
                "| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |",
                "| :--- | :--- | :--- | :---: |",
                f"| `ground_truth/latent_customer_state.csv` | `{self.run1.latent_sha256}` | `{self.run2.latent_sha256}` | `{lat_ok}` |",
                "",
                "## 4. Exported File SHA-256 Hashes",
                "",
                "| File | Run 1 SHA-256 | Run 2 SHA-256 | Match |",
                "| :--- | :--- | :--- | :---: |",
            ]
        )
        all_files = sorted(
            set(self.run1.exported_file_hashes.keys())
            | set(self.run2.exported_file_hashes.keys())
        )
        for rel in all_files:
            h1 = self.run1.exported_file_hashes.get(rel, "MISSING")
            h2 = self.run2.exported_file_hashes.get(rel, "MISSING")
            ok = "PASS" if h1 == h2 and h1 != "MISSING" else "FAIL"
            lines.append(f"| `{rel}` | `{h1}` | `{h2}` | `{ok}` |")

        if self.mismatches:
            lines.extend(["", "## Mismatches", ""])
            for m in self.mismatches:
                lines.append(f"- {m}")

        lines.extend(["", f"Reproducibility Result: {self.status_str}", ""])
        return "\n".join(lines)


def np_or_unique_keys(keys1: list[str], keys2: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for k in keys1 + keys2:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def collect_run_snapshot(
    run_dir: Path | str,
    label: str = "run",
    hashseed: str = "1",
) -> RunSnapshot:
    """Inspect a completed generate + export directory and collect counts, hashes, and aggregates."""
    rdir = Path(run_dir)
    db_path = rdir / "churnexp.db"
    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found in run directory: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid;"
        )
        tables = [r[0] for r in cur.fetchall()]
        row_counts: dict[str, int] = {}
        for tbl in tables:
            cur.execute(f"SELECT COUNT(*) FROM {tbl};")
            row_counts[tbl] = int(cur.fetchone()[0])

        n_customers = row_counts.get("customer", 0)
        cur.execute(
            "SELECT COUNT(*) FROM subscription WHERE end_reason = 'VOLUNTARY_CANCEL';"
        )
        n_voluntary = int(cur.fetchone()[0])

        cur.execute(
            "SELECT COUNT(*) FROM subscription WHERE end_reason = 'INVOLUNTARY_CANCEL';"
        )
        n_involuntary = int(cur.fetchone()[0])

        cur.execute(
            "SELECT COUNT(*) FROM subscription WHERE end_reason = 'PLAN_CHANGE';"
        )
        n_plan_changes = int(cur.fetchone()[0])

        cur.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM billing_event WHERE event_type = 'INVOICE';"
        )
        total_invoiced_cents = int(cur.fetchone()[0])

        cur.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM billing_event WHERE status = 'SETTLED';"
        )
        total_settled_cents = int(cur.fetchone()[0])

        n_churned = n_voluntary + n_involuntary
        overall_churn_rate = (
            round(n_churned / float(n_customers), 6) if n_customers > 0 else 0.0
        )
    finally:
        conn.close()

    aggregates: dict[str, int | float] = {
        "overall_churn_rate": overall_churn_rate,
        "voluntary_count": n_voluntary,
        "involuntary_count": n_involuntary,
        "plan_change_count": n_plan_changes,
        "total_invoiced_cents": total_invoiced_cents,
        "total_settled_cents": total_settled_cents,
    }

    exported_hashes: dict[str, str] = {}
    for subdir in ("csv", "json", "sql"):
        sdir = rdir / subdir
        if sdir.is_dir():
            for fp in sorted(sdir.iterdir()):
                if fp.is_file():
                    rel = fp.relative_to(rdir).as_posix()
                    exported_hashes[rel] = file_sha256(fp)

    latent_path = rdir / "ground_truth" / "latent_customer_state.csv"
    latent_sha = file_sha256(latent_path) if latent_path.is_file() else "MISSING"

    return RunSnapshot(
        label=label,
        hashseed=hashseed,
        table_row_counts=row_counts,
        exported_file_hashes=exported_hashes,
        latent_sha256=latent_sha,
        aggregates=aggregates,
    )


def compare_runs(
    run1: RunSnapshot,
    run2: RunSnapshot,
    scale: str = "starter",
) -> ReproComparison:
    """Compare two RunSnapshots and record any mismatches."""
    mismatches: list[str] = []

    # 1. Per-table row counts
    all_tables = sorted(
        set(run1.table_row_counts.keys()) | set(run2.table_row_counts.keys())
    )
    for tbl in all_tables:
        c1 = run1.table_row_counts.get(tbl)
        c2 = run2.table_row_counts.get(tbl)
        if c1 != c2:
            mismatches.append(f"Table row count mismatch for {tbl!r}: run1={c1} vs run2={c2}")

    # 2. Aggregates
    for k in np_or_unique_keys(list(run1.aggregates.keys()), list(run2.aggregates.keys())):
        v1 = run1.aggregates.get(k)
        v2 = run2.aggregates.get(k)
        s1 = f"{v1:.6f}" if isinstance(v1, float) else str(v1)
        s2 = f"{v2:.6f}" if isinstance(v2, float) else str(v2)
        if s1 != s2:
            mismatches.append(f"Aggregate mismatch for {k!r}: run1={s1} vs run2={s2}")

    # 3. Latent file SHA-256
    if (
        run1.latent_sha256 != run2.latent_sha256
        or run1.latent_sha256 == "MISSING"
        or run2.latent_sha256 == "MISSING"
    ):
        mismatches.append(
            f"Latent file SHA-256 mismatch: run1={run1.latent_sha256} vs run2={run2.latent_sha256}"
        )

    # 4. Exported file SHA-256 hashes
    all_files = sorted(
        set(run1.exported_file_hashes.keys()) | set(run2.exported_file_hashes.keys())
    )
    if not all_files:
        mismatches.append("No exported files found to compare")
    for rel in all_files:
        h1 = run1.exported_file_hashes.get(rel, "MISSING")
        h2 = run2.exported_file_hashes.get(rel, "MISSING")
        if h1 != h2 or h1 == "MISSING":
            mismatches.append(
                f"Exported file SHA-256 mismatch for {rel!r}: run1={h1} vs run2={h2}"
            )

    return ReproComparison(
        scale=scale,
        run1=run1,
        run2=run2,
        mismatches=mismatches,
    )


def _run_subprocess_pipeline(scale: str, out_dir: Path, hashseed: str) -> None:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(hashseed)

    gen_cmd = [
        sys.executable,
        "-m",
        "churnexp",
        "generate",
        "--scale",
        scale,
        "--output-dir",
        str(out_dir),
    ]
    res_gen = subprocess.run(gen_cmd, env=env, capture_output=True, text=True)
    if res_gen.returncode != 0:
        raise RuntimeError(
            f"Subprocess generate failed (PYTHONHASHSEED={hashseed}):\n"
            f"STDOUT:\n{res_gen.stdout}\nSTDERR:\n{res_gen.stderr}"
        )

    exp_cmd = [
        sys.executable,
        "-m",
        "churnexp",
        "export",
        "--scale",
        scale,
        "--output-dir",
        str(out_dir),
    ]
    res_exp = subprocess.run(exp_cmd, env=env, capture_output=True, text=True)
    if res_exp.returncode != 0:
        raise RuntimeError(
            f"Subprocess export failed (PYTHONHASHSEED={hashseed}):\n"
            f"STDOUT:\n{res_exp.stdout}\nSTDERR:\n{res_exp.stderr}"
        )


def run_repro_check(
    scale: str = "starter",
    report_dir: Path | str | None = None,
) -> ReproComparison:
    """Execute generate + export twice under PYTHONHASHSEED=1 and 2, compare, and write REPRODUCIBILITY.md."""
    with tempfile.TemporaryDirectory(prefix=f"churnexp_repro_{scale}_") as tmp_root:
        root_p = Path(tmp_root)
        dir1 = root_p / "run1"
        dir2 = root_p / "run2"
        dir1.mkdir(parents=True, exist_ok=True)
        dir2.mkdir(parents=True, exist_ok=True)

        _run_subprocess_pipeline(scale, dir1, hashseed="1")
        _run_subprocess_pipeline(scale, dir2, hashseed="2")

        snap1 = collect_run_snapshot(dir1, label="run1", hashseed="1")
        snap2 = collect_run_snapshot(dir2, label="run2", hashseed="2")

    comp = compare_runs(snap1, snap2, scale=scale)

    if report_dir is None:
        base_data = Path(__file__).resolve().parent.parent.parent / "data" / scale
    else:
        base_data = Path(report_dir)
    base_data.mkdir(parents=True, exist_ok=True)
    repro_md_path = base_data / "REPRODUCIBILITY.md"
    repro_md_path.write_text(comp.to_markdown(), encoding="utf-8")

    return comp

