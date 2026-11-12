"""Unit tests for the CLI interface, subcommands, health check, and error handling."""

import pytest

from churnexp.cli import PLANNED_MILESTONES, build_parser, main


def test_cli_help():
    """Verify that --help exits with 0 and lists all 10 subcommands."""
    parser = build_parser()
    help_text = parser.format_help()
    expected_subcommands = [
        "health",
        "config",
        "generate",
        "validate",
        "train",
        "campaign",
        "evaluate",
        "audit",
        "repro-check",
        "all",
    ]
    for cmd in expected_subcommands:
        assert cmd in help_text


def test_cli_health(capsys):
    """health subcommand exits 0 and prints Python version, package, seed, timeline, and sqlite3."""
    ret = main(["health", "--scale", "starter"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "Python version: 3.11." in captured
    assert "Package version: 0.1.0" in captured
    assert "Seed: 20261022" in captured
    assert "Timeline:" in captured
    assert "data_start=2025-01-01" in captured
    assert "sqlite3 functional" in captured
    assert "Health check PASSED." in captured


def test_cli_health_full_scale(capsys):
    """health with full scale exits 0."""
    ret = main(["health", "--scale", "full"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "scale='full'" in captured


def test_cli_config(capsys):
    """config subcommand exits 0 and prints valid YAML configuration."""
    ret = main(["config", "--scale", "starter"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "scale: starter" in captured
    assert "seed: 20261022" in captured
    assert "n_customers: 1000" in captured


def test_cli_generate_starter(capsys, tmp_path):
    """generate subcommand builds starter world, writes DB and latent CSV, and exits 0."""
    from churnexp.cli import run_generate

    ret = run_generate(scale="starter", output_root=tmp_path)
    assert ret == 0
    captured = capsys.readouterr().out
    assert "=== Generation Summary (scale=starter, seed=20261022) ===" in captured
    assert "overall_churn_rate" in captured
    assert "SHA-256 Hashes:" in captured
    assert (tmp_path / "starter" / "churnexp.db").is_file()
    assert (tmp_path / "starter" / "ground_truth" / "latent_customer_state.csv").is_file()


def test_cli_stubs(capsys):
    """All unreleased subcommands exit 2 and print planned milestone."""
    assert "generate" not in PLANNED_MILESTONES
    for cmd, milestone in PLANNED_MILESTONES.items():
        ret = main([cmd])
        assert ret == 2
        captured = capsys.readouterr().out
        assert f"not implemented yet (planned for milestone {milestone})" in captured


def test_cli_invalid_scale():
    """Invalid scale option is rejected with code 2."""
    ret = main(["health", "--scale", "invalid_scale"])
    assert ret == 2


def test_cli_missing_command():
    """Invoking CLI without command exits with code 2."""
    ret = main([])
    assert ret == 2
