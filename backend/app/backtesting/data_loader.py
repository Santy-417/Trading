from datetime import datetime, timedelta

import pandas as pd

from app.core.logging_config import get_logger
from app.integrations.metatrader.mt5_client import MT5Client, Timeframe, mt5_client

logger = get_logger(__name__)

# Duration of one bar per timeframe (for warmup date calculation)
TIMEFRAME_DURATION: dict[str, timedelta] = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}


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

    async def load_from_mt5_range(
        self,
        symbol: str,
        timeframe: str,
        date_from: datetime,
        date_to: datetime,
    ) -> pd.DataFrame:
        """Load historical OHLCV data for a specific date range from MT5."""
        tf = Timeframe(timeframe)
        df = await self._mt5.get_historical_data_range(
            symbol=symbol, timeframe=tf, date_from=date_from, date_to=date_to
        )
        logger.info(
            "Data loaded from MT5 range: %s %s, %d bars (%s to %s)",
            symbol, timeframe, len(df), date_from, date_to,
        )
        return df

    async def load_with_warmup(
        self,
        symbol: str,
        timeframe: str,
        date_from: datetime,
        date_to: datetime,
        warmup_bars: int = 200,
    ) -> tuple[pd.DataFrame, int]:
        """
        Load data with warm-up period for indicator precalculation.

        The warm-up bars are loaded BEFORE date_from so that indicators
        (daily_bias, entropy, etc.) are fully initialized when the trading
        period starts.

        Returns:
            Tuple of (full_df_with_warmup, warmup_bar_count)
            - full_df includes warmup bars before date_from
            - warmup_bar_count: index where actual trading period starts
        """
        bar_duration = TIMEFRAME_DURATION.get(timeframe)
        if bar_duration is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        # Calculate warmup start date
        warmup_duration = bar_duration * warmup_bars
        warmup_start = date_from - warmup_duration

        logger.info(
            "Loading with warmup: %s %s, warmup=%d bars (%s), range=%s to %s",
            symbol, timeframe, warmup_bars, warmup_start, date_from, date_to,
        )

        # Load full range (warmup + trading period)
        df = await self.load_from_mt5_range(
            symbol=symbol,
            timeframe=timeframe,
            date_from=warmup_start,
            date_to=date_to,
        )

        # Find the index where the actual trading period starts
        trading_start_mask = df.index >= pd.Timestamp(date_from)
        if trading_start_mask.any():
            warmup_count = int((~trading_start_mask).sum())
        else:
            warmup_count = len(df)
            logger.warning(
                "No bars found after date_from=%s. All %d bars are warmup.",
                date_from, len(df),
            )

        logger.info(
            "Warmup complete: %d total bars (%d warmup + %d trading)",
            len(df), warmup_count, len(df) - warmup_count,
        )

        return df, warmup_count

    @staticmethod
    def estimate_bars(
        timeframe: str,
        date_from: datetime,
        date_to: datetime,
        warmup_bars: int = 200,
    ) -> dict:
        """Estimate the number of bars for a given date range."""
        bar_duration = TIMEFRAME_DURATION.get(timeframe)
        if bar_duration is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        total_seconds = (date_to - date_from).total_seconds()
        bar_seconds = bar_duration.total_seconds()
        trading_bars = max(int(total_seconds / bar_seconds), 0)

        return {
            "estimated_bars": warmup_bars + trading_bars,
            "warmup_bars": warmup_bars,
            "trading_bars": trading_bars,
        }

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
