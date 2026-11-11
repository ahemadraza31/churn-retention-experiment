"""Unit tests for config loading, scale presets, and invariant validation."""

from datetime import date
import pytest

from churnexp.config import (
    AnomaliesConfig,
    ChurnConfig,
    Config,
    ExperimentConfig,
    PopulationConfig,
    TimelineConfig,
    load_config,
    validate_config,
)


def test_load_config_full():
    """Verify full scale configuration matches approved architecture."""
    cfg = load_config("full")
    assert cfg.scale == "full"
    assert cfg.seed == 20261022
    assert cfg.population.n_customers == 20000
    assert cfg.timeline.data_start == date(2025, 1, 1)
    assert cfg.timeline.data_end == date(2026, 6, 30)
    assert cfg.timeline.train_as_of == date(2025, 7, 1)
    assert cfg.timeline.score_as_of == date(2026, 1, 1)
    assert cfg.timeline.label_horizon_days == 180
    assert cfg.timeline.feature_lookback_months == 6
    assert cfg.timeline.outcome_window_days == 90
    assert cfg.churn.target_rate == 0.12
    assert cfg.churn.min_rate == 0.05
    assert cfg.churn.max_rate == 0.20
    assert cfg.experiment.treatment_share == 0.5
    assert cfg.experiment.stratify_by == "risk_band"
    assert cfg.anomalies.records_per_type == 40


def test_load_config_starter():
    """Verify starter scale configuration deep merges over default."""
    cfg = load_config("starter")
    assert cfg.scale == "starter"
    assert cfg.seed == 20261022
    assert cfg.population.n_customers == 1000
    assert cfg.anomalies.records_per_type == 10
    # Inherited fields from default
    assert cfg.timeline.data_start == date(2025, 1, 1)
    assert cfg.timeline.score_as_of == date(2026, 1, 1)
    assert cfg.churn.target_rate == 0.12
    assert cfg.experiment.treatment_share == 0.5


def _valid_base_config() -> Config:
    return Config(
        scale="test",
        seed=20261022,
        population=PopulationConfig(n_customers=5000),
        timeline=TimelineConfig(
            data_start=date(2025, 1, 1),
            data_end=date(2026, 6, 30),
            train_as_of=date(2025, 7, 1),
            score_as_of=date(2026, 1, 1),
            label_horizon_days=180,
            feature_lookback_months=6,
            outcome_window_days=90,
        ),
        churn=ChurnConfig(target_rate=0.12, min_rate=0.05, max_rate=0.20),
        experiment=ExperimentConfig(treatment_share=0.5, stratify_by="risk_band"),
        anomalies=AnomaliesConfig(records_per_type=20),
    )


def test_validation_rule_timeline_order():
    """Rule: data_start < train_as_of < score_as_of < data_end."""
    base = _valid_base_config()
    # Inverted start and train dates
    bad_timeline = TimelineConfig(
        data_start=date(2025, 8, 1),
        data_end=date(2026, 6, 30),
        train_as_of=date(2025, 7, 1),
        score_as_of=date(2026, 1, 1),
        label_horizon_days=180,
        feature_lookback_months=6,
        outcome_window_days=90,
    )
    cfg = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=bad_timeline,
        churn=base.churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Timeline order invariant"):
        validate_config(cfg)


def test_validation_rule_training_label_leakage():
    """Rule: train_as_of + label_horizon_days <= score_as_of."""
    base = _valid_base_config()
    # Horizon 200 days from 2025-07-01 reaches 2026-01-17, exceeding 2026-01-01
    bad_timeline = TimelineConfig(
        data_start=date(2025, 1, 1),
        data_end=date(2026, 6, 30),
        train_as_of=date(2025, 7, 1),
        score_as_of=date(2026, 1, 1),
        label_horizon_days=200,
        feature_lookback_months=6,
        outcome_window_days=90,
    )
    cfg = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=bad_timeline,
        churn=base.churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Temporal leakage invariant"):
        validate_config(cfg)


def test_validation_rule_score_horizon_boundary():
    """Rule: score_as_of + label_horizon_days <= data_end + 1 day."""
    base = _valid_base_config()
    # data_end cut prematurely to 2026-05-01
    bad_timeline = TimelineConfig(
        data_start=date(2025, 1, 1),
        data_end=date(2026, 5, 1),
        train_as_of=date(2025, 7, 1),
        score_as_of=date(2026, 1, 1),
        label_horizon_days=180,
        feature_lookback_months=6,
        outcome_window_days=90,
    )
    cfg = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=bad_timeline,
        churn=base.churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Timeline data boundary"):
        validate_config(cfg)


def test_validation_rule_churn_rates():
    """Rule: min_rate <= target_rate <= max_rate within 0.05 to 0.20."""
    base = _valid_base_config()
    # Target rate exceeds 0.20
    bad_churn = ChurnConfig(target_rate=0.25, min_rate=0.05, max_rate=0.30)
    cfg = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=base.timeline,
        churn=bad_churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Churn rate invariant"):
        validate_config(cfg)

    # Inverted min and target
    inverted_churn = ChurnConfig(target_rate=0.08, min_rate=0.10, max_rate=0.15)
    cfg_inverted = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=base.timeline,
        churn=inverted_churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Churn rate invariant"):
        validate_config(cfg_inverted)


def test_validation_rule_population():
    """Rule: 1 <= n_customers <= 999999."""
    base = _valid_base_config()
    cfg_zero = Config(
        scale=base.scale,
        seed=base.seed,
        population=PopulationConfig(n_customers=0),
        timeline=base.timeline,
        churn=base.churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Population invariant"):
        validate_config(cfg_zero)

    cfg_million = Config(
        scale=base.scale,
        seed=base.seed,
        population=PopulationConfig(n_customers=1000000),
        timeline=base.timeline,
        churn=base.churn,
        experiment=base.experiment,
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Population invariant"):
        validate_config(cfg_million)


def test_validation_rule_treatment_share():
    """Rule: treatment_share strictly between 0 and 1."""
    base = _valid_base_config()
    cfg_zero = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=base.timeline,
        churn=base.churn,
        experiment=ExperimentConfig(treatment_share=0.0, stratify_by="risk_band"),
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Experiment invariant"):
        validate_config(cfg_zero)

    cfg_one = Config(
        scale=base.scale,
        seed=base.seed,
        population=base.population,
        timeline=base.timeline,
        churn=base.churn,
        experiment=ExperimentConfig(treatment_share=1.0, stratify_by="risk_band"),
        anomalies=base.anomalies,
    )
    with pytest.raises(ValueError, match="Experiment invariant"):
        validate_config(cfg_one)


def test_load_config_unknown_scale():
    """Reject unknown scale names."""
    with pytest.raises(ValueError, match="Unknown scale"):
        load_config("unsupported_scale")
