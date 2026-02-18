import pandas as pd

from app.core.logging_config import get_logger
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)


class ManualStrategy(BaseStrategy):
    """
    Manual strategy that allows direct trade entry via API.
    Does not generate signals automatically — signals come from user input.
    """

    name = "manual"
    supported_timeframes = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> TradeSignal | None:
        # Manual strategy never auto-generates signals
        return None

    def create_manual_signal(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        timeframe: str = "H1",
    ) -> TradeSignal:
        """Create a signal from manual user input."""
        signal_dir = SignalDirection.BUY if direction.upper() == "BUY" else SignalDirection.SELL

        signal = TradeSignal(
            direction=signal_dir,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=1.0,  # User decision
            strategy_name=self.name,
            metadata={"source": "manual"},
        )

        logger.info(
            "manual_signal_created: symbol=%s, direction=%s, entry=%s, sl=%s, tp=%s",
            symbol, direction, entry_price, stop_loss, take_profit,
        )
        return signal

    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
    ) -> tuple[float, float]:
        # Manual strategy requires user-provided SL/TP
        raise NotImplementedError("Manual strategy requires explicit SL/TP from user")
