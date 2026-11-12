"""Command Line Interface (CLI) entrypoint for churnexp."""

import argparse
from dataclasses import asdict
from pathlib import Path
import sqlite3
import sys
import time
from typing import Sequence
import yaml

from churnexp import __version__
from churnexp.config import load_config
from churnexp.experiment.pipeline import M4_STARTER_REFERENCE_HASH_PREFIXES, run_pipeline
from churnexp.generation.world import TABLE_LOAD_ORDER, hash_world, load_world
from churnexp.io.exporters import export_database, parse_formats
from churnexp.repro import run_repro_check
from churnexp.schema.db import create_database
from churnexp.validation.checks import (
    load_tables_from_csv_dir,
    load_tables_from_db,
    load_tables_from_json_dir,
    validate_tables,
)


PLANNED_MILESTONES: dict[str, int] = {}


def build_parser() -> argparse.ArgumentParser:
    """Build top-level argument parser with all required subcommands."""
    parser = argparse.ArgumentParser(
        prog="churnexp",
        description="Churn Detection and Retention Offer Experiment CLI",
    )
    scale_parent = argparse.ArgumentParser(add_help=False)
    scale_parent.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter",
        help="Dataset scale preset (default: starter)",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="subcommands",
        required=True,
    )

    # 1. health
    subparsers.add_parser(
        "health",
        parents=[scale_parent],
        help="Run environment, package, config, and sqlite3 health check",
    )

    # 2. config
    subparsers.add_parser(
        "config",
        parents=[scale_parent],
        help="Print the resolved configuration",
    )

    # 3. generate
    gen_parser = subparsers.add_parser(
        "generate",
        parents=[scale_parent],
        help="Generate synthetic data and anomalies",
    )
    gen_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom output directory (default: output/<scale>)",
    )

    # 4. validate
    val_parser = subparsers.add_parser(
        "validate",
        parents=[scale_parent],
        help="Validate structural and temporal database rules",
    )
    val_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom report output directory (default: data/<scale>)",
    )

    # 5. export
    exp_parser = subparsers.add_parser(
        "export",
        parents=[scale_parent],
        help="Export database tables to CSV, JSON, SQL, and write MANIFEST.json",
    )
    exp_parser.add_argument(
        "--formats",
        default=None,
        help="Comma-separated formats to export: csv,json,sql (default: csv,json,sql for starter; csv for full)",
    )
    exp_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom export directory (default: data/<scale>)",
    )

    # 6. repro-check
    repro_parser = subparsers.add_parser(
        "repro-check",
        parents=[scale_parent],
        help="Check end-to-end reproducibility with seed 20261022",
    )
    repro_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom report directory for REPRODUCIBILITY.md (default: data/<scale>)",
    )

    # 7. evaluate
    eval_parser = subparsers.add_parser(
        "evaluate",
        parents=[scale_parent],
        help="Evaluate model performance, ITT lift, and financial impact",
    )
    eval_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom report directory (default: data/<scale>)",
    )

    # 8. audit
    audit_parser = subparsers.add_parser(
        "audit",
        parents=[scale_parent],
        help="Run blind detectors and audit precision/recall against ground truth",
    )
    audit_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom report directory (default: data/<scale>)",
    )

    # 9. all
    all_parser = subparsers.add_parser(
        "all",
        parents=[scale_parent],
        help="Run generate, export, validate, evaluate, and audit in order",
    )
    all_parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom directory (default: data/<scale>)",
    )

    # Remaining stub subcommands
    stub_names = [
        ("train", "Train churn risk prediction model (runs as part of generate)"),
        ("campaign", "Evaluate eligibility and assign retention offers (runs as part of generate)"),
    ]

    for name, help_text in stub_names:
        subparsers.add_parser(name, parents=[scale_parent], help=help_text)

    return parser


def run_health(scale: str) -> int:
    """Check Python >= 3.11, package version, config loading, seed, timeline, and sqlite3."""
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python version: {py_ver}")
    if sys.version_info < (3, 11):
        print("ERROR: Python >= 3.11 is required.", file=sys.stderr)
        return 1

    print(f"Package version: {__version__}")

    try:
        cfg = load_config(scale=scale)
        print(f"Configuration loaded: scale='{cfg.scale}'")
        print(f"Seed: {cfg.seed}")
        tl = cfg.timeline
        print(
            f"Timeline: data_start={tl.data_start}, train_as_of={tl.train_as_of}, "
            f"score_as_of={tl.score_as_of}, data_end={tl.data_end}"
        )
    except Exception as exc:
        print(f"ERROR: Failed to load config: {exc}", file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("SELECT sqlite_version()")
        sqlite_ver = cur.fetchone()[0]
        conn.close()
        print(f"sqlite3 functional (version: {sqlite_ver})")
    except Exception as exc:
        print(f"ERROR: sqlite3 check failed: {exc}", file=sys.stderr)
        return 1

    print("Health check PASSED.")
    return 0


def run_config(scale: str) -> int:
    """Print the resolved configuration."""
    cfg = load_config(scale=scale)
    data = asdict(cfg)
    print(yaml.safe_dump(data, sort_keys=False))
    return 0


def run_generate(
    scale: str,
    output_root: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> int:
    """Generate the base untreated world, run the campaign pipeline, load SQLite, and write latent GT."""
    t0 = time.perf_counter()
    cfg = load_config(scale=scale)
    if output_dir is not None:
        scale_dir = Path(output_dir)
    elif output_root is not None:
        scale_dir = Path(output_root) / cfg.scale
    else:
        scale_dir = Path(__file__).resolve().parent.parent.parent / "output" / cfg.scale

    gt_dir = scale_dir / "ground_truth"
    scale_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    db_path = scale_dir / "churnexp.db"
    if db_path.exists():
        db_path.unlink()

    world = run_pipeline(cfg)
    conn = create_database(str(db_path))
    try:
        load_world(world, conn)
    finally:
        conn.close()

    latent_path = gt_dir / "latent_customer_state.csv"
    world.latent.to_csv(latent_path, index=False, lineterminator="\n")

    s = world.summary
    if "anomalies_gt" in s and s["anomalies_gt"] is not None:
        anom_path = gt_dir / "anomalies.csv"
        s["anomalies_gt"].to_csv(anom_path, index=False, lineterminator="\n")
    if "expected_decisions_gt" in s and s["expected_decisions_gt"] is not None:
        dec_path = gt_dir / "expected_decisions.csv"
        s["expected_decisions_gt"].to_csv(dec_path, index=False, lineterminator="\n")
    if "model_info" in s and s["model_info"] is not None:
        import json

        info_path = scale_dir / "model_info.json"
        info_path.write_text(json.dumps(s["model_info"], indent=2), encoding="utf-8")

    hashes = hash_world(world)
    elapsed = time.perf_counter() - t0

    print(f"=== Generation Summary (scale={cfg.scale}, seed={cfg.seed}) ===")
    print("Base Untreated World SHA-256 Hashes:")
    base_hashes = s.get("base_hashes", {})
    for b_tbl, b_h in base_hashes.items():
        if cfg.scale == "starter" and b_tbl in M4_STARTER_REFERENCE_HASH_PREFIXES:
            ref_p = M4_STARTER_REFERENCE_HASH_PREFIXES[b_tbl]
            match_tag = " (matches M4)" if b_h.startswith(ref_p) else f" (MISMATCH vs {ref_p})"
        else:
            match_tag = ""
        print(f"  {b_tbl:18s}: {b_h}{match_tag}")

    print("Table Row Counts:")
    for tbl_name, _ in TABLE_LOAD_ORDER:
        if tbl_name in world.tables:
            print(f"  {tbl_name:24s}: {len(world.tables[tbl_name]):8d}")
    print(f"  {'latent (GT)':24s}: {len(world.latent):8d}")

    print("Cohort & Churn Metrics:")
    print(
        f"  overall_churn_rate          : {s['overall_churn_rate']:.4f} "
        f"({s['n_churned']}/{s['n_customers']}) [untreated]"
    )
    print(
        f"  observed_churn_rate         : {s['observed_churn_rate']:.4f} "
        f"({s['observed_n_churned']}/{s['n_customers']}) [post-campaign]"
    )
    print(f"  voluntary_churn_count       : {s['n_voluntary']} (observed: {s['observed_n_voluntary']})")
    print(f"  involuntary_churn_count     : {s['n_involuntary']} (observed: {s['observed_n_involuntary']})")
    print(f"  plan_change_count           : {s['n_plan_changes']}")
    print(f"  active_on_train_as_of       : {s['active_on_train_as_of']}")
    print(f"  active_on_score_as_of       : {s['active_on_score_as_of']}")
    print(f"  untreated_churn_2025_horizon: {s['untreated_churn_2025_horizon']}")
    print(f"  untreated_churn_2026_horizon: {s['untreated_churn_2026_horizon']}")

    print("Model & Scoring Summary:")
    print(f"  training_rows (P0)          : {s['train_rows']}")
    print(f"  training_positives (2025)   : {s['train_positives']}")
    print(f"  training_roc_auc            : {s['train_auc']:.6f}")
    print(f"  scored_customers (P)        : {s['scored_customers']}")
    bc = s["band_counts"]
    print(f"  risk_bands (HIGH/MED/LOW)   : HIGH={bc['HIGH']}, MEDIUM={bc['MEDIUM']}, LOW={bc['LOW']}")
    print(
        f"  non_treatment_2026_auc      : {s['non_treatment_2026_auc']:.6f} "
        f"(rows={s['non_treatment_2026_rows']}, pos={s['non_treatment_2026_positives']})"
    )

    print("Eligibility & Assignment Summary:")
    rfc = s["rule_fail_counts"]
    for r_idx in range(1, 7):
        rid = f"ER-{r_idx:03d}"
        print(f"  {rid} failures             : {rfc[rid]}")
    print(
        f"  ER-007 failures             : {rfc['ER-007_all_offers']} customers failed all offers "
        f"({rfc['ER-007_eval_rows']} offer-eval rows failed)"
    )
    for k_oid, v_cnt in sorted(rfc.items()):
        if k_oid.startswith("ER-007:"):
            print(f"    {k_oid:24s}: {v_cnt}")
    print(f"  eligible_customers          : {s['eligible_customers']}")
    poc = s["planned_offer_counts"]
    poc_str = ", ".join(f"{oid}={cnt}" for oid, cnt in sorted(poc.items()))
    print(f"  planned_offer_counts        : {poc_str}")
    sac = s["stratum_arm_counts"]
    for strat in ("HIGH", "MEDIUM"):
        st_c = sac.get(strat, {"TREATMENT": 0, "CONTROL": 0})
        print(
            f"  stratum {strat:6s} arms         : TREATMENT={st_c['TREATMENT']}, CONTROL={st_c['CONTROL']}"
        )

    print("Simulation & Balance Summary:")
    print(f"  DELIVERY_FAILED             : {s['delivery_failed_count']}")
    print(f"  responded (SENT treatment)  : {s['responded_count']}")
    print(f"  redeemed (SENT treatment)   : {s['redeemed_count']}")
    print(f"  SAVEABLE (both arms)        : {s['saveable_count']}")
    print(f"  saved (TREATMENT+SENT)      : {s['saved_count']}")
    print(
        f"  90d_retention_rate          : TREATMENT={s['retention_90d_treatment']:.4f}, "
        f"CONTROL={s['retention_90d_control']:.4f}"
    )
    smds = s["smd_by_covariate"]
    print(
        f"  covariate_balance_max_smd   : {s['max_smd']:.6f} "
        f"(risk_score={smds['risk_score']:.6f}, tenure_days={smds['tenure_days']:.6f}, "
        f"monthly_price_cents={smds['monthly_price_cents']:.6f})"
    )

    if "anomaly_counts" in s:
        ac = s["anomaly_counts"]
        print("Anomaly Injection Summary:")
        print(f"  A (Temporal label leakage)        : {ac.get('A', 0)} injected")
        print(f"  B (Ineligible offer contact)      : {ac.get('B', 0)} injected")
        print(f"  C (Group leakage)                 : {ac.get('C', 0)} injected")
        print(f"  D (Multi-offer attribution)       : {ac.get('D', 0)} injected")

    print("SHA-256 Hashes:")
    for k, h in hashes.items():
        print(f"  {k:24s}: {h}")
    print(f"Elapsed seconds: {elapsed:.2f}s")
    return 0


def run_validate(
    scale: str,
    db_path: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> int:
    """Validate structural, temporal, reconciliation, cross-file, and detector rules."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    if db_path is None:
        db_p = repo_root / "output" / scale / "churnexp.db"
        if not db_p.is_file():
            db_p = repo_root / "data" / scale / "churnexp.db"
    else:
        db_p = Path(db_path)

    if not db_p.is_file():
        print(f"ERROR: Database not found at {db_p}", file=sys.stderr)
        return 1

    if output_dir is None:
        data_dir = repo_root / "data" / scale
    else:
        data_dir = Path(output_dir)

    conn = sqlite3.connect(str(db_p))
    try:
        db_tables = load_tables_from_db(conn)
        csv_dir = data_dir / "csv"
        json_dir = data_dir / "json"

        csv_tables = load_tables_from_csv_dir(csv_dir) if csv_dir.is_dir() else None
        json_tables = load_tables_from_json_dir(json_dir) if json_dir.is_dir() else None

        base_report = validate_tables(
            tables=db_tables,
            csv_tables=csv_tables,
            json_tables=json_tables,
            conn=conn,
            scale=scale,
        )

        from churnexp.validation.detectors import run_detectors, summarize_detector_findings
        from churnexp.validation.report import Report

        det_findings = run_detectors(db_tables)
        det_summaries = summarize_detector_findings(det_findings)

        report = Report(
            findings=base_report.findings,
            rule_summaries=base_report.rule_summaries,
            scale=scale,
            detector_findings=det_findings,
            detector_summaries=det_summaries,
        )
    finally:
        conn.close()

    print(f"=== Validation Report (scale={scale}) ===")
    for line in report.format_cli_lines():
        print(f"  {line}")

    md_path, json_path = report.write_reports(data_dir)
    overall = "PASS" if report.passed else "FAIL"
    print(
        f"Overall: {overall} (data_quality_findings={len(report.findings)}, "
        f"detector_findings={len(report.detector_findings)}, "
        f"summary={md_path.name}, report={json_path.name})"
    )
    return 1 if report.has_critical_or_high else 0


def run_export(
    scale: str,
    formats: str | Sequence[str] | None = None,
    output_dir: Path | str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """Export all tables found in the DB to CSV, JSON, SQL, and write MANIFEST.json."""
    t0 = time.perf_counter()
    cfg = load_config(scale=scale)
    repo_root = Path(__file__).resolve().parent.parent.parent

    if output_dir is not None:
        out_dir = Path(output_dir)
        write_root_sm = False
    else:
        out_dir = repo_root / "data" / cfg.scale
        write_root_sm = True

    if db_path is not None:
        db_p = Path(db_path)
    elif (out_dir / "churnexp.db").is_file():
        db_p = out_dir / "churnexp.db"
    else:
        db_p = repo_root / "output" / cfg.scale / "churnexp.db"

    fmt_list = parse_formats(formats, cfg.scale)
    manifest = export_database(
        db_path=db_p,
        export_dir=out_dir,
        cfg=cfg,
        formats=fmt_list,
        source_gt_dir=db_p.parent / "ground_truth",
        write_root_source_manifest=write_root_sm,
    )
    elapsed = time.perf_counter() - t0

    print(
        f"=== Export Summary (scale={cfg.scale}, formats={','.join(fmt_list)}) ==="
    )
    print(f"Output directory: {out_dir}")
    print(f"Files written   : {len(manifest['files'])}")
    print(f"GT files copied : {len(manifest['ground_truth_files'])}")
    print(f"Config SHA-256  : {manifest['config_sha256']}")
    print(f"Elapsed seconds : {elapsed:.2f}s")
    return 0


def run_repro(scale: str, output_dir: Path | str | None = None) -> int:
    """Run two-process reproducibility check and write REPRODUCIBILITY.md."""
    comp = run_repro_check(scale=scale, report_dir=output_dir)
    print(comp.format_cli_table())
    return 0 if comp.passed else 1


def run_evaluate(
    scale: str,
    output_dir: Path | str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """Evaluate model metrics, causal ITT lift, and financial impact excluding detector anomalies."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    if db_path is not None:
        db_p = Path(db_path)
    elif (repo_root / "data" / scale / "churnexp.db").is_file():
        db_p = repo_root / "data" / scale / "churnexp.db"
    elif (repo_root / "output" / scale / "churnexp.db").is_file():
        db_p = repo_root / "output" / scale / "churnexp.db"
    else:
        db_p = repo_root / "output" / scale / "churnexp.db"

    if not db_p.is_file():
        print(f"ERROR: Database not found at {db_p}", file=sys.stderr)
        return 1

    out_dir = Path(output_dir) if output_dir is not None else (repo_root / "data" / scale)
    out_dir.mkdir(parents=True, exist_ok=True)

    from churnexp.evaluation.report import run_evaluation

    conn = sqlite3.connect(str(db_p))
    try:
        tables = load_tables_from_db(conn)
    finally:
        conn.close()

    model_info_obj = None
    for p_try in [db_p.parent / "model_info.json", out_dir / "model_info.json"]:
        if p_try.is_file():
            try:
                model_info_obj = json.loads(p_try.read_text(encoding="utf-8"))
                break
            except Exception:
                pass

    results, _ = run_evaluation(
        tables,
        output_dir=out_dir,
        scale=scale,
        model_info=model_info_obj,
    )

    exp = results["experiment"]
    p90 = exp["primary_90d"]
    s180 = exp["secondary_180d"]
    fin = results["financial"]
    excl = results["exclusions"]
    mm = results["model_metrics"]

    m180 = mm.get("label_180d", mm.get("untreated_180d", {}))
    m90 = mm.get("label_90d", mm.get("untreated_90d", {}))
    f180 = fin.get("headline_180d", {})

    print(f"=== Evaluation Summary (scale={scale}) ===")
    print(
        f"Detector Exclusions: {excl['total_unique_excluded_customers']} unique customers"
    )
    print(
        f"Untreated Model AUC: 180d={m180.get('roc_auc')}, "
        f"90d={m90.get('roc_auc')}"
    )
    print(
        f"Primary 90d ITT Lift: {p90['absolute_lift_pp']:+.2f} pp "
        f"[{p90['ci_95_low_pp']:+.2f}, {p90['ci_95_high_pp']:+.2f}] (p={p90['p_value']:.4f})"
    )
    print(
        f"Secondary 180d ITT Lift: {s180['absolute_lift_pp']:+.2f} pp "
        f"[{s180['ci_95_low_pp']:+.2f}, {s180['ci_95_high_pp']:+.2f}] (p={s180['p_value']:.4f})"
    )
    print(
        f"Financial Impact (180d headline): Net Impact=${f180.get('net_impact_cents', 0) / 100.0:+,.2f}, "
        f"Benefit=${f180.get('benefit_cents', 0) / 100.0:+,.2f}, "
        f"Cost=${fin.get('realized_cost_cents', 0) / 100.0:+,.2f}"
    )
    print(
        f"Reports written: {out_dir / 'evaluation_results.json'}, "
        f"{out_dir / 'evaluation_report.md'}"
    )
    return 0


def run_audit_cli(
    scale: str,
    output_dir: Path | str | None = None,
    db_path: Path | str | None = None,
    gt_dir: Path | str | None = None,
) -> int:
    """Run ground truth audit against detectors and causal effects."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    if db_path is not None:
        db_p = Path(db_path)
    elif (repo_root / "data" / scale / "churnexp.db").is_file():
        db_p = repo_root / "data" / scale / "churnexp.db"
    elif (repo_root / "output" / scale / "churnexp.db").is_file():
        db_p = repo_root / "output" / scale / "churnexp.db"
    else:
        db_p = repo_root / "output" / scale / "churnexp.db"

    if not db_p.is_file():
        print(f"ERROR: Database not found at {db_p}", file=sys.stderr)
        return 1

    out_dir = Path(output_dir) if output_dir is not None else (repo_root / "data" / scale)
    out_dir.mkdir(parents=True, exist_ok=True)

    if gt_dir is not None:
        g_dir = Path(gt_dir)
    elif (out_dir / "ground_truth").is_dir():
        g_dir = out_dir / "ground_truth"
    elif (db_p.parent / "ground_truth").is_dir():
        g_dir = db_p.parent / "ground_truth"
    else:
        g_dir = repo_root / "data" / scale / "ground_truth"

    from churnexp.audit.score import run_audit

    conn = sqlite3.connect(str(db_p))
    try:
        tables = load_tables_from_db(conn)
    finally:
        conn.close()

    audit_res, report_md, passed = run_audit(
        tables=tables,
        gt_dir=g_dir,
        output_dir=out_dir,
        scale=scale,
    )
    print(report_md)
    return 0 if passed else 1


def run_all(
    scale: str,
    output_dir: Path | str | None = None,
) -> int:
    """Run generate, export, validate, evaluate, audit in order. Print one PASS/FAIL line per stage."""
    stages = [
        ("generate", lambda: run_generate(scale=scale, output_dir=output_dir)),
        ("export", lambda: run_export(scale=scale, output_dir=output_dir)),
        ("validate", lambda: run_validate(scale=scale, output_dir=output_dir)),
        ("evaluate", lambda: run_evaluate(scale=scale, output_dir=output_dir)),
        ("audit", lambda: run_audit_cli(scale=scale, output_dir=output_dir)),
    ]

    stage_results: list[tuple[str, str]] = []
    overall_exit = 0

    print(f"=== Running Full Pipeline ('all') (scale={scale}) ===")
    for name, fn in stages:
        try:
            code = fn()
            status = "PASS" if code == 0 else "FAIL"
        except Exception as exc:
            print(f"Stage {name} crashed with exception: {exc}", file=sys.stderr)
            status = "FAIL"
            code = 1

        stage_results.append((name, status))
        if code != 0 and overall_exit == 0:
            overall_exit = code

    print("\n=== Pipeline Execution Summary ===")
    for name, st in stage_results:
        print(f"  {name:10s}: {st}")

    return overall_exit


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint function."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    command = args.command
    scale = getattr(args, "scale", "starter")
    out_dir = getattr(args, "output_dir", None)

    if command == "health":
        return run_health(scale=scale)
    elif command == "config":
        return run_config(scale=scale)
    elif command == "generate":
        return run_generate(scale=scale, output_dir=out_dir)
    elif command == "validate":
        return run_validate(scale=scale, output_dir=out_dir)
    elif command == "export":
        return run_export(
            scale=scale,
            formats=getattr(args, "formats", None),
            output_dir=out_dir,
        )
    elif command == "repro-check":
        return run_repro(scale=scale, output_dir=out_dir)
    elif command == "evaluate":
        return run_evaluate(scale=scale, output_dir=out_dir)
    elif command == "audit":
        return run_audit_cli(scale=scale, output_dir=out_dir)
    elif command == "all":
        return run_all(scale=scale, output_dir=out_dir)
    elif command in ("train", "campaign"):
        print("runs as part of generate")
        return 0
    elif command in PLANNED_MILESTONES:
        m_num = PLANNED_MILESTONES[command]
        print(f"not implemented yet (planned for milestone {m_num})")
        return 2
    else:
        print(f"Unknown command: {command!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
