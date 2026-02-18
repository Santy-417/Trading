import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.ml.feature_engineering import FeatureEngineer

logger = get_logger(__name__)


class DatasetBuilder:
    """Build ML datasets from OHLCV data with features and labels."""

    def __init__(
        self,
        forward_bars: int = 10,
        min_return_threshold: float = 0.001,
    ):
        self.forward_bars = forward_bars
        self.min_return_threshold = min_return_threshold

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build a complete dataset with features and target label.

        Target: 1 = profitable trade (price went up > threshold within N bars)
                0 = not profitable
        """
        # Add features
        dataset = FeatureEngineer.add_all_features(df)

        # Create target label: max forward return within N bars
        future_returns = []
        close_values = dataset["close"].values

        for i in range(len(close_values)):
            end_idx = min(i + self.forward_bars, len(close_values) - 1)
            if i >= len(close_values) - 1:
                future_returns.append(0.0)
            else:
                future_max = close_values[i + 1: end_idx + 1].max()
                future_return = (future_max - close_values[i]) / close_values[i]
                future_returns.append(future_return)

        dataset["forward_return"] = future_returns
        dataset["target"] = (
            dataset["forward_return"] > self.min_return_threshold
        ).astype(int)

        # Drop rows with NaN (from indicator warmup periods)
        before = len(dataset)
        dataset = dataset.dropna()
        logger.info(
            "Dataset built: %d rows (%d dropped), target distribution: %s",
            len(dataset),
            before - len(dataset),
            dataset["target"].value_counts().to_dict(),
        )

        return dataset

    def split_train_test(
        self, dataset: pd.DataFrame, train_ratio: float = 0.8
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Time-series aware split (no shuffling — preserves temporal order).
        """
        split_idx = int(len(dataset) * train_ratio)
        train = dataset.iloc[:split_idx]
        test = dataset.iloc[split_idx:]
        logger.info(
            "Split: train=%d rows, test=%d rows", len(train), len(test)
        )
        return train, test

    def walk_forward_split(
        self, dataset: pd.DataFrame, n_splits: int = 5, train_ratio: float = 0.7
    ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Walk-forward validation splits.
        Each split uses expanding training window and fixed test window.
        """
        total = len(dataset)
        test_size = int(total / (n_splits + 1))
        splits = []

        for i in range(n_splits):
            train_end = int(total * train_ratio) + (i * test_size)
            test_end = min(train_end + test_size, total)

            if train_end >= total or test_end <= train_end:
                break

            train = dataset.iloc[:train_end]
            test = dataset.iloc[train_end:test_end]
            splits.append((train, test))

        logger.info("Walk-forward splits: %d", len(splits))
        return splits
