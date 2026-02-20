import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)

FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


class FibonacciStrategy(BaseStrategy):
    """
    Versión SIMPLE para debugging.
    Intencionalmente permisiva para detectar dónde falla.
    """

    name = "fibonacci"
    supported_timeframes = ["M15", "M30", "H1", "H4"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    def __init__(
        self,
        swing_lookback: int = 50,
        entry_levels: list[float] | None = None,
        tp_extension: float = 1.272,
        confirmation_candles: int = 1,
    ):
        self.swing_lookback = swing_lookback
        self.entry_levels = entry_levels or [0.382, 0.5, 0.618]
        self.tp_extension = tp_extension
        self.confirmation_candles = confirmation_candles

    # =========================
    # SWING DETECTION (simple)
    # =========================
    def _find_swing_points(self, df: pd.DataFrame):
        recent = df.tail(self.swing_lookback)

        swing_high_idx = recent["high"].idxmax()
        swing_low_idx = recent["low"].idxmin()

        swing_high = recent.loc[swing_high_idx, "high"]
        swing_low = recent.loc[swing_low_idx, "low"]

        high_pos = recent.index.get_loc(swing_high_idx)
        low_pos = recent.index.get_loc(swing_low_idx)

        return swing_high, swing_low, high_pos, low_pos

    # =========================
    # FIB LEVELS
    # =========================
    def _calculate_fib_levels(self, swing_high, swing_low, is_uptrend):
        diff = swing_high - swing_low
        levels = {}

        if diff <= 0:
            return levels

        if is_uptrend:
            for level in FIB_LEVELS:
                levels[level] = swing_high - diff * level
        else:
            for level in FIB_LEVELS:
                levels[level] = swing_low + diff * level

        return levels

    # =========================
    # CONFIRMATION (very simple)
    # =========================
    def _check_reversal_confirmation(self, df, direction):
        if len(df) < 2:
            return False

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if direction == SignalDirection.BUY:
            return last["close"] > prev["close"]
        else:
            return last["close"] < prev["close"]

    # =========================
    # MAIN SIGNAL
    # =========================
    def generate_signal(self, df: pd.DataFrame, symbol: str, timeframe: str):
        if len(df) < self.swing_lookback + 5:
            logger.debug("Not enough data")
            return None

        swing_high, swing_low, high_pos, low_pos = self._find_swing_points(df)
        is_uptrend = low_pos < high_pos
        current_price = df["close"].iloc[-1]

        diff = swing_high - swing_low
        if diff <= 0:
            logger.debug("Invalid swing diff")
            return None

        fib_levels = self._calculate_fib_levels(
            swing_high, swing_low, is_uptrend
        )

        # 🔥 Tolerancia amplia para debugging
        tolerance = diff * 0.05  # 5%

        signal_direction = None
        nearest_level = None

        for level in self.entry_levels:
            fib_price = fib_levels[level]

            logger.debug(
                "Fib check: price=%s fib=%s tol=%s",
                current_price,
                fib_price,
                tolerance,
            )

            if abs(current_price - fib_price) <= tolerance:
                nearest_level = level
                signal_direction = (
                    SignalDirection.BUY if is_uptrend else SignalDirection.SELL
                )
                break

        if signal_direction is None:
            logger.debug("No fib match")
            return None

        if not self._check_reversal_confirmation(df, signal_direction):
            logger.debug("Confirmation failed")
            return None

        sl, tp = self.calculate_sl_tp(
            df, signal_direction, current_price
        )

        signal = TradeSignal(
            direction=signal_direction,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.5,
            strategy_name=self.name,
            metadata={
                "swing_high": swing_high,
                "swing_low": swing_low,
                "fib_level": nearest_level,
                "is_uptrend": is_uptrend,
            },
        )

        logger.debug(
            "Signal generated: %s %s at %s (fib level %.3f)",
            symbol,
            signal_direction.value,
            current_price,
            nearest_level,
        )

        return signal if self.validate_signal(signal) else None

    # =========================
    # SL / TP simple
    # =========================
    def calculate_sl_tp(self, df, direction, entry_price):
        swing_high, swing_low, _, _ = self._find_swing_points(df)
        diff = swing_high - swing_low

        if direction == SignalDirection.BUY:
            sl = swing_low - diff * 0.02
            tp = entry_price + diff * self.tp_extension
        else:
            sl = swing_high + diff * 0.02
            tp = entry_price - diff * self.tp_extension

        return round(sl, 8), round(tp, 8)
