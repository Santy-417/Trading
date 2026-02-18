import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)

# Standard Fibonacci retracement levels
FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
# Extension levels for take profit
FIB_EXTENSIONS = [1.272, 1.618, 2.0, 2.618]


class FibonacciStrategy(BaseStrategy):
    """
    Fibonacci retracement/extension strategy.

    Entry: Price retraces to key Fibonacci level (0.382, 0.5, 0.618) and shows
    reversal confirmation.
    SL: Beyond the swing high/low.
    TP: Fibonacci extension levels (1.272, 1.618).
    """

    name = "fibonacci"
    supported_timeframes = ["M15", "M30", "H1", "H4"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    def __init__(
        self,
        swing_lookback: int = 50,
        entry_levels: list[float] | None = None,
        tp_extension: float = 1.618,
        confirmation_candles: int = 2,
    ):
        self.swing_lookback = swing_lookback
        self.entry_levels = entry_levels or [0.382, 0.5, 0.618]
        self.tp_extension = tp_extension
        self.confirmation_candles = confirmation_candles

    def _find_swing_points(
        self, df: pd.DataFrame
    ) -> tuple[float, float, int, int]:
        """Find the most recent swing high and swing low."""
        recent = df.tail(self.swing_lookback)
        swing_high_idx = recent["high"].idxmax()
        swing_low_idx = recent["low"].idxmin()
        swing_high = recent.loc[swing_high_idx, "high"]
        swing_low = recent.loc[swing_low_idx, "low"]

        # Determine positions for trend direction
        high_pos = recent.index.get_loc(swing_high_idx)
        low_pos = recent.index.get_loc(swing_low_idx)

        return swing_high, swing_low, high_pos, low_pos

    def _calculate_fib_levels(
        self, swing_high: float, swing_low: float, is_uptrend: bool
    ) -> dict[float, float]:
        """Calculate Fibonacci retracement levels."""
        diff = swing_high - swing_low
        levels = {}

        if is_uptrend:
            # Retracement from high to low (pullback in uptrend)
            for level in FIB_LEVELS:
                levels[level] = swing_high - (diff * level)
        else:
            # Retracement from low to high (pullback in downtrend)
            for level in FIB_LEVELS:
                levels[level] = swing_low + (diff * level)

        return levels

    def _check_reversal_confirmation(
        self, df: pd.DataFrame, direction: SignalDirection
    ) -> bool:
        """Check for reversal candlestick confirmation."""
        if len(df) < self.confirmation_candles + 1:
            return False

        recent = df.tail(self.confirmation_candles + 1)

        if direction == SignalDirection.BUY:
            # Bullish confirmation: last N candles closing higher
            closes = recent["close"].values
            return all(closes[i] < closes[i + 1] for i in range(-self.confirmation_candles, -1))
        else:
            closes = recent["close"].values
            return all(closes[i] > closes[i + 1] for i in range(-self.confirmation_candles, -1))

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> TradeSignal | None:
        if len(df) < self.swing_lookback + 10:
            return None

        swing_high, swing_low, high_pos, low_pos = self._find_swing_points(df)
        is_uptrend = low_pos < high_pos  # Low came before high = uptrend
        current_price = df["close"].iloc[-1]

        fib_levels = self._calculate_fib_levels(swing_high, swing_low, is_uptrend)

        # Check if price is near a key Fibonacci level
        diff = swing_high - swing_low
        tolerance = diff * 0.02  # 2% tolerance

        signal_direction = None
        nearest_level = None

        for level in self.entry_levels:
            fib_price = fib_levels[level]
            if abs(current_price - fib_price) <= tolerance:
                nearest_level = level
                if is_uptrend:
                    signal_direction = SignalDirection.BUY
                else:
                    signal_direction = SignalDirection.SELL
                break

        if signal_direction is None or nearest_level is None:
            return None

        # Check confirmation
        if not self._check_reversal_confirmation(df, signal_direction):
            return None

        sl, tp = self.calculate_sl_tp(df, signal_direction, current_price)

        signal = TradeSignal(
            direction=signal_direction,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.5 + (nearest_level * 0.3),  # Higher fib = more confidence
            strategy_name=self.name,
            metadata={
                "swing_high": swing_high,
                "swing_low": swing_low,
                "fib_level": nearest_level,
                "is_uptrend": is_uptrend,
            },
        )

        if self.validate_signal(signal):
            logger.info(
                "fibonacci_signal: symbol=%s, direction=%s, fib_level=%s, entry=%s",
                symbol, signal_direction.value, nearest_level, current_price,
            )
            return signal
        return None

    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
    ) -> tuple[float, float]:
        swing_high, swing_low, _, _ = self._find_swing_points(df)
        diff = swing_high - swing_low

        if direction == SignalDirection.BUY:
            sl = swing_low - (diff * 0.05)  # Slightly below swing low
            tp = entry_price + (diff * self.tp_extension)
        else:
            sl = swing_high + (diff * 0.05)  # Slightly above swing high
            tp = entry_price - (diff * self.tp_extension)

        return round(sl, 8), round(tp, 8)
