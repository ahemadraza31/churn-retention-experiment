from __future__ import annotations

from pathlib import Path

from churnexp.config import load_config
from churnexp.experiment.pipeline import M4_STARTER_REFERENCE_HASH_PREFIXES, run_pipeline
from churnexp.generation.world import hash_world


def test_pipeline_determinism_and_base_hashes():
    cfg = load_config("starter")
    r1 = run_pipeline(cfg)
    r2 = run_pipeline(cfg)

    # 1. Base-table hashes match M4 starter values (prefixes)
    base_hashes = r1.summary["base_hashes"]
    for tbl, expected_prefix in M4_STARTER_REFERENCE_HASH_PREFIXES.items():
        actual = base_hashes[tbl]
        assert actual.startswith(expected_prefix), (
            f"Base hash mismatch for {tbl}: {actual} vs {expected_prefix}"
        )

    # 2. Two runs produce identical hashes for every table and latent
    h1 = hash_world(r1)
    h2 = hash_world(r2)
    assert h1 == h2

    # 3. SMD is computed and < 0.15
    assert r1.summary["max_smd"] < 0.15
    for cov, smd in r1.summary["smd_by_covariate"].items():
        assert abs(smd) < 0.15, f"Covariate {cov} SMD {smd} >= 0.15"

    # 4. Forbidden strings check in features/, modeling/, eligibility/, and experiment/assign.py
    forbidden = ("latent", "ground_truth", "hidden_segment", "untreated_churn")
    check_paths = [
        Path("src/churnexp/features/builder.py"),
        Path("src/churnexp/modeling/train.py"),
        Path("src/churnexp/modeling/score.py"),
        Path("src/churnexp/modeling/metrics.py"),
        Path("src/churnexp/eligibility/catalog.py"),
        Path("src/churnexp/eligibility/rules.py"),
        Path("src/churnexp/eligibility/engine.py"),
        Path("src/churnexp/experiment/assign.py"),
    ]
    for p in check_paths:
        content = p.read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in content, f"Forbidden string '{word}' found in {p}"
