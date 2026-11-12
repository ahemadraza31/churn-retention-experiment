"""Unit tests for reproducibility snapshot comparison and fake mismatch detection."""

from dataclasses import replace

from churnexp.repro import RunSnapshot, compare_runs


def _sample_snapshot(hashseed: str = "1") -> RunSnapshot:
    return RunSnapshot(
        label=f"run_{hashseed}",
        hashseed=hashseed,
        table_row_counts={
            "customer": 1000,
            "subscription": 1200,
            "usage_snapshot": 16255,
            "billing_event": 32379,
            "support_case": 1028,
            "state_event": 2640,
            "churn_outcome": 876,
        },
        exported_file_hashes={
            "csv/customer.csv": "aaaa1111" * 8,
            "csv/subscription.csv": "bbbb2222" * 8,
            "sql/schema.sql": "cccc3333" * 8,
            "sql/seed.sql": "dddd4444" * 8,
        },
        latent_sha256="eeee5555" * 8,
        aggregates={
            "overall_churn_rate": 0.12,
            "voluntary_count": 83,
            "involuntary_count": 37,
            "plan_change_count": 200,
            "total_invoiced_cents": 29123456,
            "total_settled_cents": 28900000,
        },
    )


def test_repro_compare_identical_passes():
    """Two identical snapshots under different PYTHONHASHSEED values pass with 0 mismatches."""
    r1 = _sample_snapshot("1")
    r2 = _sample_snapshot("2")
    comp = compare_runs(r1, r2, scale="starter")
    assert comp.passed is True
    assert comp.status_str == "PASS"
    assert comp.mismatches == []
    assert "Reproducibility Result: PASS" in comp.format_cli_table()
    assert "**Result**: **PASS**" in comp.to_markdown()


def test_repro_compare_fake_row_count_mismatch():
    """A fake row-count mismatch causes compare_runs to fail and report the table."""
    r1 = _sample_snapshot("1")
    bad_counts = dict(r1.table_row_counts, customer=999)
    r2 = replace(_sample_snapshot("2"), table_row_counts=bad_counts)

    comp = compare_runs(r1, r2, scale="starter")
    assert comp.passed is False
    assert comp.status_str == "FAIL"
    assert any("customer" in m for m in comp.mismatches)
    assert "Reproducibility Result: FAIL" in comp.format_cli_table()


def test_repro_compare_fake_file_hash_mismatch():
    """A fake exported file SHA-256 mismatch causes compare_runs to fail."""
    r1 = _sample_snapshot("1")
    bad_hashes = dict(r1.exported_file_hashes, **{"csv/customer.csv": "ffff9999" * 8})
    r2 = replace(_sample_snapshot("2"), exported_file_hashes=bad_hashes)

    comp = compare_runs(r1, r2, scale="starter")
    assert comp.passed is False
    assert any("csv/customer.csv" in m for m in comp.mismatches)


def test_repro_compare_fake_latent_hash_mismatch():
    """A fake latent file SHA-256 mismatch causes compare_runs to fail."""
    r1 = _sample_snapshot("1")
    r2 = replace(_sample_snapshot("2"), latent_sha256="00001111" * 8)

    comp = compare_runs(r1, r2, scale="starter")
    assert comp.passed is False
    assert any("Latent file SHA-256 mismatch" in m for m in comp.mismatches)


def test_repro_compare_fake_aggregate_mismatch():
    """A fake aggregate mismatch (e.g. total_settled_cents) causes compare_runs to fail."""
    r1 = _sample_snapshot("1")
    bad_aggs = dict(r1.aggregates, total_settled_cents=100)
    r2 = replace(_sample_snapshot("2"), aggregates=bad_aggs)

    comp = compare_runs(r1, r2, scale="starter")
    assert comp.passed is False
    assert any("total_settled_cents" in m for m in comp.mismatches)

