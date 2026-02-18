import numpy as np
import pandas as pd
import pytest

from app.ml.dataset_builder import DatasetBuilder
from app.ml.feature_engineering import FeatureEngineer
from app.ml.model_training import ModelTrainer


def _make_ohlcv(n: int = 500, base_price: float = 1.1000) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    close = base_price + np.cumsum(np.random.randn(n) * 0.0005)
    high = close + np.abs(np.random.randn(n) * 0.0003)
    low = close - np.abs(np.random.randn(n) * 0.0003)
    open_ = close + np.random.randn(n) * 0.0002

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "tick_volume": np.random.randint(100, 5000, n),
    }, index=dates)


class TestFeatureEngineering:
    def test_add_all_features(self):
        df = _make_ohlcv()
        result = FeatureEngineer.add_all_features(df)
        assert "rsi" in result.columns
        assert "macd" in result.columns
        assert "bb_upper" in result.columns
        assert "atr" in result.columns
        assert "ema_9" in result.columns
        assert "momentum_10" in result.columns

    def test_rsi_range(self):
        df = _make_ohlcv()
        result = FeatureEngineer.add_rsi(df)
        rsi_valid = result["rsi"].dropna()
        assert rsi_valid.min() >= 0
        assert rsi_valid.max() <= 100

    def test_get_feature_columns(self):
        df = _make_ohlcv()
        featured = FeatureEngineer.add_all_features(df)
        cols = FeatureEngineer.get_feature_columns(featured)
        assert "close" not in cols
        assert "open" not in cols
        assert len(cols) > 10


class TestDatasetBuilder:
    def test_build_dataset(self):
        df = _make_ohlcv(n=300)
        builder = DatasetBuilder(forward_bars=10)
        dataset = builder.build(df)
        assert "target" in dataset.columns
        assert dataset["target"].isin([0, 1]).all()
        assert len(dataset) > 0

    def test_split_preserves_order(self):
        df = _make_ohlcv(n=300)
        builder = DatasetBuilder()
        dataset = builder.build(df)
        train, test = builder.split_train_test(dataset, train_ratio=0.8)

        assert len(train) > 0
        assert len(test) > 0
        # Train comes before test in time
        assert train.index[-1] < test.index[0]

    def test_walk_forward_splits(self):
        df = _make_ohlcv(n=500)
        builder = DatasetBuilder()
        dataset = builder.build(df)
        splits = builder.walk_forward_split(dataset, n_splits=3)

        assert len(splits) >= 1
        for train, test in splits:
            assert len(train) > 0
            assert len(test) > 0


class TestModelTrainer:
    def test_train_and_evaluate(self):
        df = _make_ohlcv(n=500)
        builder = DatasetBuilder()
        dataset = builder.build(df)
        train, test = builder.split_train_test(dataset)

        trainer = ModelTrainer()
        trainer.train(train)
        metrics = trainer.evaluate(test)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "f1_score" in metrics
        assert 0 <= metrics["accuracy"] <= 1

    def test_feature_importance(self):
        df = _make_ohlcv(n=500)
        builder = DatasetBuilder()
        dataset = builder.build(df)
        train, _ = builder.split_train_test(dataset)

        trainer = ModelTrainer()
        trainer.train(train)
        importance = trainer.get_feature_importance(train)

        assert len(importance) > 0
        # Values should be non-negative
        assert all(v >= 0 for v in importance.values())

    def test_walk_forward_validate(self):
        df = _make_ohlcv(n=500)
        builder = DatasetBuilder()
        dataset = builder.build(df)
        splits = builder.walk_forward_split(dataset, n_splits=2)

        trainer = ModelTrainer()
        results = trainer.walk_forward_validate(splits)

        assert len(results) >= 1
        assert all("accuracy" in r for r in results)
