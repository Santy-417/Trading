from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


@dataclass
class TradeSignal:
    direction: SignalDirection
    symbol: str
    timeframe: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = 0.0  # 0.0 to 1.0
    strategy_name: str = ""
    metadata: dict | None = None

    @property
    def sl_pips(self) -> float:
        """Calculate stop loss distance in pips (approximate)."""
        return abs(self.entry_price - self.stop_loss)

    @property
    def tp_pips(self) -> float:
        """Calculate take profit distance in pips."""
        return abs(self.take_profit - self.entry_price)

    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk:reward ratio."""
        if self.sl_pips == 0:
            return 0.0
        return self.tp_pips / self.sl_pips


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    name: str = "base"
    supported_timeframes: list[str] = []
    supported_symbols: list[str] = []

    @abstractmethod
    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> TradeSignal | None:
        """
        Analyze market data and generate a trade signal.

        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, tick_volume]
            symbol: Trading symbol (e.g., EURUSD)
            timeframe: Timeframe string (e.g., H1)

        Returns:
            TradeSignal if conditions met, None otherwise.
        """
        ...

    @abstractmethod
    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
    ) -> tuple[float, float]:
        """
        Calculate stop loss and take profit levels.

        Returns:
            Tuple of (stop_loss, take_profit) prices.
        """
        ...

    def validate_signal(self, signal: TradeSignal) -> bool:
        """Basic signal validation. Override for custom validation."""
        if signal.direction == SignalDirection.NEUTRAL:
            return False
        if signal.stop_loss <= 0 or signal.take_profit <= 0:
            return False
        if signal.risk_reward_ratio < 1.0:
            return False
        return True
