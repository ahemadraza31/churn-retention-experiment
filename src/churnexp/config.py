"""Configuration loader, dataclasses, and invariant validation for churnexp."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
import yaml


@dataclass(frozen=True)
class PopulationConfig:
    n_customers: int


@dataclass(frozen=True)
class TimelineConfig:
    data_start: date
    data_end: date
    train_as_of: date
    score_as_of: date
    label_horizon_days: int
    feature_lookback_months: int
    outcome_window_days: int


@dataclass(frozen=True)
class ChurnConfig:
    target_rate: float
    min_rate: float
    max_rate: float


@dataclass(frozen=True)
class ExperimentConfig:
    treatment_share: float
    stratify_by: str


@dataclass(frozen=True)
class AnomaliesConfig:
    records_per_type: int


@dataclass(frozen=True)
class Config:
    scale: str
    seed: int
    population: PopulationConfig
    timeline: TimelineConfig
    churn: ChurnConfig
    experiment: ExperimentConfig
    anomalies: AnomaliesConfig


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Cannot parse date from {value!r}")


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], Mapping) and isinstance(v, Mapping):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def validate_config(cfg: Config) -> None:
    """Validate temporal, population, rate, and experiment invariants."""
    # 1. Timeline order
    t = cfg.timeline
    if not (t.data_start < t.train_as_of < t.score_as_of < t.data_end):
        raise ValueError(
            f"Timeline order invariant violated: expected data_start ({t.data_start}) < "
            f"train_as_of ({t.train_as_of}) < score_as_of ({t.score_as_of}) < data_end ({t.data_end})"
        )

    # 2. Training label resolution before scoring date (leakage defense)
    train_label_end = t.train_as_of + timedelta(days=t.label_horizon_days)
    if train_label_end > t.score_as_of:
        raise ValueError(
            f"Temporal leakage invariant violated: training labels must be fully resolved before "
            f"scoring date. train_as_of + label_horizon_days ({train_label_end}) > score_as_of ({t.score_as_of})"
        )

    # 3. Score label horizon within data end (+ 1 day)
    score_label_end = t.score_as_of + timedelta(days=t.label_horizon_days)
    allowed_end = t.data_end + timedelta(days=1)
    if score_label_end > allowed_end:
        raise ValueError(
            f"Timeline data boundary violated: score_as_of + label_horizon_days ({score_label_end}) "
            f"must be <= data_end + 1 day ({allowed_end})"
        )

    # 4. Churn rate bounds within 0.05 to 0.20
    c = cfg.churn
    if not (0.05 <= c.min_rate <= c.target_rate <= c.max_rate <= 0.20):
        raise ValueError(
            f"Churn rate invariant violated: expected 0.05 <= min_rate <= target_rate <= max_rate <= 0.20. "
            f"Got min_rate={c.min_rate}, target_rate={c.target_rate}, max_rate={c.max_rate}"
        )

    # 5. Customer population bounds
    n = cfg.population.n_customers
    if not (1 <= n <= 999999):
        raise ValueError(
            f"Population invariant violated: expected 1 <= n_customers <= 999999, got {n}"
        )

    # 6. Experiment treatment share strictly between 0 and 1
    share = cfg.experiment.treatment_share
    if not (0.0 < share < 1.0):
        raise ValueError(
            f"Experiment invariant violated: treatment_share must be strictly between 0 and 1, got {share}"
        )


def _config_from_dict(data: Mapping[str, Any]) -> Config:
    pop = PopulationConfig(n_customers=int(data["population"]["n_customers"]))
    tl_raw = data["timeline"]
    timeline = TimelineConfig(
        data_start=_parse_date(tl_raw["data_start"]),
        data_end=_parse_date(tl_raw["data_end"]),
        train_as_of=_parse_date(tl_raw["train_as_of"]),
        score_as_of=_parse_date(tl_raw["score_as_of"]),
        label_horizon_days=int(tl_raw["label_horizon_days"]),
        feature_lookback_months=int(tl_raw["feature_lookback_months"]),
        outcome_window_days=int(tl_raw["outcome_window_days"]),
    )
    churn = ChurnConfig(
        target_rate=float(data["churn"]["target_rate"]),
        min_rate=float(data["churn"]["min_rate"]),
        max_rate=float(data["churn"]["max_rate"]),
    )
    experiment = ExperimentConfig(
        treatment_share=float(data["experiment"]["treatment_share"]),
        stratify_by=str(data["experiment"]["stratify_by"]),
    )
    anomalies = AnomaliesConfig(
        records_per_type=int(data["anomalies"]["records_per_type"])
    )

    cfg = Config(
        scale=str(data["scale"]),
        seed=int(data["seed"]),
        population=pop,
        timeline=timeline,
        churn=churn,
        experiment=experiment,
        anomalies=anomalies,
    )
    validate_config(cfg)
    return cfg


def load_config(scale: str = "starter", config_dir: Path | str | None = None) -> Config:
    """Load configuration for the requested scale (starter or full).

    'full' loads default.yaml.
    'starter' loads default.yaml and deep-merges starter.yaml overrides.
    """
    if config_dir is None:
        # Locate project root config directory relative to this file
        base_dir = Path(__file__).resolve().parent.parent.parent / "config"
    else:
        base_dir = Path(config_dir)

    default_path = base_dir / "default.yaml"
    if not default_path.is_file():
        raise FileNotFoundError(f"Default config not found at {default_path}")

    with open(default_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    scale_lower = scale.lower()
    if scale_lower == "full":
        pass
    elif scale_lower == "starter":
        starter_path = base_dir / "starter.yaml"
        if not starter_path.is_file():
            raise FileNotFoundError(f"Starter config not found at {starter_path}")
        with open(starter_path, "r", encoding="utf-8") as f:
            starter_data = yaml.safe_load(f) or {}
        data = _deep_merge(data, starter_data)
    else:
        raise ValueError(f"Unknown scale: {scale!r}. Expected 'starter' or 'full'.")

    return _config_from_dict(data)
