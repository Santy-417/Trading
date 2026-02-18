from datetime import datetime

import pandas as pd

from app.core.logging_config import get_logger
from app.integrations.metatrader.mt5_client import MT5Client, Timeframe, mt5_client

logger = get_logger(__name__)


class DataLoader:
    """Load historical data for backtesting from MT5 or CSV."""

    def __init__(self, mt5: MT5Client | None = None):
        self._mt5 = mt5 or mt5_client

    async def load_from_mt5(
        self,
        symbol: str,
        timeframe: str,
        count: int = 5000,
        date_from: datetime | None = None,
    ) -> pd.DataFrame:
        """Load historical OHLCV data from MetaTrader 5."""
        tf = Timeframe(timeframe)
        df = await self._mt5.get_historical_data(
            symbol=symbol, timeframe=tf, count=count, date_from=date_from
        )
        logger.info(
            "Data loaded from MT5: %s %s, %d bars", symbol, timeframe, len(df)
        )
        return df

    @staticmethod
    def load_from_csv(filepath: str) -> pd.DataFrame:
        """Load historical data from a CSV file."""
        df = pd.read_csv(filepath, parse_dates=["time"], index_col="time")
        required_cols = {"open", "high", "low", "close", "tick_volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")
        logger.info("Data loaded from CSV: %s, %d bars", filepath, len(df))
        return df

    @staticmethod
    def validate_data(df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean OHLCV data."""
        # Remove rows with NaN
        before = len(df)
        df = df.dropna(subset=["open", "high", "low", "close"])
        dropped = before - len(df)
        if dropped > 0:
            logger.warning("Dropped %d rows with NaN values", dropped)

        # Ensure sorted by time
        df = df.sort_index()

        return df
