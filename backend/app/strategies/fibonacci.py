import numpy as np
import pandas as pd
import ta

from app.core.logging_config import get_logger
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)

FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIB_EXTENSIONS = [1.272, 1.618, 2.0, 2.618]


class FibonacciStrategy(BaseStrategy):
    """
    Quant-enhanced Fibonacci strategy (FTMO-safe + ML-ready).
    """

    name = "fibonacci_quant"
    supported_timeframes = ["M15", "M30", "H1", "H4"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    def __init__(
        self,
        swing_lookback: int = 50,
        entry_levels: list[float] | None = None,
        tp_extension: float = 1.618,
        confirmation_candles: int = 2,
        ema_period: int = 50,
        atr_period: int = 14,
    ):
        self.swing_lookback = swing_lookback
        self.entry_levels = entry_levels or [0.382, 0.5, 0.618]
        self.tp_extension = tp_extension
        self.confirmation_candles = confirmation_candles
        self.ema_period = ema_period
        self.atr_period = atr_period

    # =========================
    # INDICATORS
    # =========================

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["ema"] = ta.trend.EMAIndicator(
            close=df["close"], window=self.ema_period
        ).ema_indicator()

        df["atr"] = ta.volatility.AverageTrueRange(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=self.atr_period,
        ).average_true_range()

        return df

    # =========================
    # SWING DETECTION (improved)
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
            return {}

        if is_uptrend:
            for level in FIB_LEVELS:
                levels[level] = swing_high - (diff * level)
        else:
            for level in FIB_LEVELS:
                levels[level] = swing_low + (diff * level)

        return levels

    # =========================
    # CONFIRMATION (stronger)
    # =========================

    def _check_reversal_confirmation(
        self, df: pd.DataFrame, direction: SignalDirection
    ) -> bool:
        recent = df.tail(self.confirmation_candles + 1)

        if len(recent) < self.confirmation_candles + 1:
            return False

        closes = recent["close"].values
        bodies = abs(recent["close"] - recent["open"]).values

        if direction == SignalDirection.BUY:
            momentum = all(
                closes[i] < closes[i + 1]
                for i in range(-self.confirmation_candles, -1)
            )
        else:
            momentum = all(
                closes[i] > closes[i + 1]
                for i in range(-self.confirmation_candles, -1)
            )

        # Require meaningful candle bodies (avoid noise)
        strong_bodies = np.mean(bodies[-self.confirmation_candles :]) > np.mean(
            bodies[:-self.confirmation_candles]
        )

        return momentum and strong_bodies

    # =========================
    # MAIN SIGNAL
    # =========================

    def generate_signal(self, df: pd.DataFrame, symbol: str, timeframe: str):
        if len(df) < self.swing_lookback + 50:
            return None

        df = self._add_indicators(df)

        swing_high, swing_low, high_pos, low_pos = self._find_swing_points(df)
        is_uptrend = low_pos < high_pos

        current_price = df["close"].iloc[-1]
        ema = df["ema"].iloc[-1]
        atr = df["atr"].iloc[-1]

        # 🔥 Trend filter (CRITICAL for FTMO)
        if is_uptrend and current_price < ema:
            return None
        if not is_uptrend and current_price > ema:
            return None

        fib_levels = self._calculate_fib_levels(swing_high, swing_low, is_uptrend)
        if not fib_levels:
            return None

        # 🔥 Dynamic tolerance using ATR
        tolerance = atr * 0.5

        signal_direction = None
        nearest_level = None

        for level in self.entry_levels:
            fib_price = fib_levels[level]
            if abs(current_price - fib_price) <= tolerance:
                nearest_level = level
                signal_direction = (
                    SignalDirection.BUY if is_uptrend else SignalDirection.SELL
                )
                break

        if signal_direction is None:
            return None

        if not self._check_reversal_confirmation(df, signal_direction):
            return None

        sl, tp = self.calculate_sl_tp(df, signal_direction, current_price, atr)

        # 🔥 Better confidence score (ML-ready)
        confidence = self._compute_confidence(
            atr=atr,
            distance_to_ema=abs(current_price - ema),
            fib_level=nearest_level,
        )

        signal = TradeSignal(
            direction=signal_direction,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=confidence,
            strategy_name=self.name,
            metadata={
                "swing_high": swing_high,
                "swing_low": swing_low,
                "fib_level": nearest_level,
                "is_uptrend": is_uptrend,
                "atr": atr,
                "ema_distance": abs(current_price - ema),
            },
        )

        return signal if self.validate_signal(signal) else None

    # =========================
    # SL / TP (FTMO safer)
    # =========================

    def calculate_sl_tp(self, df, direction, entry_price, atr):
        swing_high, swing_low, _, _ = self._find_swing_points(df)

        if direction == SignalDirection.BUY:
            sl = swing_low - atr * 0.5
            tp = entry_price + atr * self.tp_extension
        else:
            sl = swing_high + atr * 0.5
            tp = entry_price - atr * self.tp_extension

        return round(sl, 8), round(tp, 8)

    # =========================
    # CONFIDENCE MODEL (proto-ML)
    # =========================

    def _compute_confidence(self, atr, distance_to_ema, fib_level):
        score = 0.5

        # less volatility = more confidence
        score += max(0, 0.2 - (atr * 0.01))

        # closer to EMA trend = better
        score += max(0, 0.2 - distance_to_ema * 0.01)

        # deeper fib = stronger pullback
        score += fib_level * 0.2

        return float(np.clip(score, 0, 1))
