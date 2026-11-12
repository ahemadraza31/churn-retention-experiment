"""Deterministic MANIFEST.json and SOURCE_MANIFEST.md generation for churnexp exports."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import numpy as np
import pandas as pd
import yaml

from churnexp import __version__
from churnexp.config import Config


def file_sha256(path: Path | str) -> str:
    """Compute SHA-256 hex digest of a file."""
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def config_sha256(cfg: Config) -> str:
    """Compute deterministic SHA-256 of resolved configuration."""
    serialized = yaml.safe_dump(asdict(cfg), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_manifest(
    cfg: Config,
    table_row_counts: dict[str, int],
    written_files: list[Path],
    ground_truth_files: list[Path],
    base_dir: Path,
) -> dict[str, Any]:
    """Build deterministic manifest dictionary for an export directory."""
    files_entry: dict[str, dict[str, Any]] = {}
    for fp in sorted(written_files, key=lambda p: p.relative_to(base_dir).as_posix()):
        rel = fp.relative_to(base_dir).as_posix()
        files_entry[rel] = {
            "sha256": file_sha256(fp),
            "bytes": fp.stat().st_size,
        }

    gt_entry: dict[str, dict[str, Any]] = {}
    for gtp in sorted(ground_truth_files, key=lambda p: p.relative_to(base_dir).as_posix()):
        rel = gtp.relative_to(base_dir).as_posix()
        gt_entry[rel] = {
            "sha256": file_sha256(gtp),
            "bytes": gtp.stat().st_size,
        }

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return {
        "scale": cfg.scale,
        "seed": cfg.seed,
        "config_sha256": config_sha256(cfg),
        "package_version": __version__,
        "table_row_counts": dict(table_row_counts),
        "files": files_entry,
        "ground_truth_files": gt_entry,
        "environment": {
            "python": py_ver,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }


def write_manifest(manifest_data: dict[str, Any], output_dir: Path | str) -> Path:
    """Write MANIFEST.json to output_dir with deterministic formatting."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    m_path = out / "MANIFEST.json"
    m_path.write_text(
        json.dumps(manifest_data, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return m_path


SOURCE_MANIFEST_CONTENT = """# Data Source & Provenance Manifest

## 1. Synthetic Provenance Statement
- **100% Synthetic Data**: Every table, record, identifier, timestamp, behavioral metric, and latent variable in `data/` and `output/` is **fully synthetic** and generated deterministically by this repository (`churnexp`).
- **No External Datasets**: No third-party, public, scraped, or proprietary external datasets were used or derived from.
- **Zero Personal Data (PII)**: No real individuals, accounts, organizations, payment instruments, or support transcripts exist anywhere in this repository. No Faker or PII-like strings (names, emails, phone numbers, addresses) are generated.

## 2. Generator Entry Point & Master Seed
- **CLI Entry Point**:
  ```bash
  python -m churnexp generate --scale [starter|full]
  python -m churnexp export --scale [starter|full]
  ```
- **Orchestrator Module**: `src/churnexp/generation/world.py` (`generate_world`, `load_world`, `hash_world`)
- **Master Random Seed**: `20261022` (configured in `config/default.yaml` via `numpy.random.SeedSequence(20261022)` and per-entity substreams in `src/churnexp/rng.py`).
- **Ground-Truth Isolation**: Counterfactual potential outcomes (`hidden_segment`, `untreated_churn_date`, `treated_churn_date`, `true_effect_flag`) are written exclusively to `ground_truth/latent_customer_state.csv` and never appear in the SQLite database or in `csv/`, `json/`, or `sql/` exports.

## 3. Runtime & Dependency Licenses

| Package | Role | License |
| :--- | :--- | :--- |
| **pandas** | Tabular data manipulation and CSV/JSON serialization | BSD-3-Clause |
| **numpy** | Deterministic `SeedSequence` / `PCG64` RNG and numerical arrays | BSD-3-Clause |
| **scikit-learn** | Explainable Logistic Regression and model evaluation metrics | BSD-3-Clause |
| **PyYAML** | YAML configuration parsing (`config/default.yaml`, `config/starter.yaml`) | MIT |
| **Streamlit** | Multi-actor interactive dashboard UI | Apache-2.0 |
| **FastAPI** | Read-only REST API service | MIT |
| **pytest** | Unit, integration, and end-to-end automated test suite | MIT |
"""


def write_source_manifest(data_root: Path | str) -> Path:
    """Write data/SOURCE_MANIFEST.md."""
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)
    sm_path = root / "SOURCE_MANIFEST.md"
    sm_path.write_text(SOURCE_MANIFEST_CONTENT, encoding="utf-8")
    return sm_path

