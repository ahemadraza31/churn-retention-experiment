"""Command Line Interface (CLI) entrypoint for churnexp."""

import argparse
from dataclasses import asdict
import sqlite3
import sys
from typing import Sequence
import yaml

from churnexp import __version__
from churnexp.config import load_config


PLANNED_MILESTONES: dict[str, int] = {
    "generate": 3,
    "validate": 4,
    "train": 5,
    "campaign": 7,
    "evaluate": 9,
    "audit": 8,
    "repro-check": 4,
    "all": 9,
}


def build_parser() -> argparse.ArgumentParser:
    """Build top-level argument parser with all required subcommands."""
    parser = argparse.ArgumentParser(
        prog="churnexp",
        description="Churn Detection and Retention Offer Experiment CLI",
    )
    # Common parent parser so every subcommand inherits --scale
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

    # 3-10. Stub subcommands
    stub_names = [
        ("generate", "Generate synthetic data and anomalies"),
        ("validate", "Validate structural and temporal database rules"),
        ("train", "Train churn risk prediction model"),
        ("campaign", "Evaluate eligibility and assign retention offers"),
        ("evaluate", "Evaluate model performance, ITT lift, and financial impact"),
        ("audit", "Run blind detectors and audit precision/recall against ground truth"),
        ("repro-check", "Check end-to-end reproducibility with seed 20261022"),
        ("all", "Run end-to-end generation, training, assignment, and evaluation"),
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


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint function."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    command = args.command
    scale = getattr(args, "scale", "starter")

    if command == "health":
        return run_health(scale=scale)
    elif command == "config":
        return run_config(scale=scale)
    elif command in PLANNED_MILESTONES:
        m_num = PLANNED_MILESTONES[command]
        print(f"not implemented yet (planned for milestone {m_num})")
        return 2
    else:
        print(f"Unknown command: {command!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
