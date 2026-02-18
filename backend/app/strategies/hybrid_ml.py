import pandas as pd

from app.core.logging_config import get_logger
from app.ml.prediction import Predictor
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal
from app.strategies.fibonacci import FibonacciStrategy

logger = get_logger(__name__)


class HybridMLStrategy(BaseStrategy):
    """
    Hybrid strategy that combines rule-based signals with ML confirmation.

    Modes:
    - "confirmation": ML confirms/filters rule-based signals
    - "standalone": ML generates signals independently
    - "hybrid": Both must agree for a signal
    """

    name = "hybrid_ml"
    supported_timeframes = ["M15", "M30", "H1", "H4"]
    supported_symbols = ["EURUSD", "XAUUSD"]

    def __init__(
        self,
        model_id: str | None = None,
        mode: str = "confirmation",
        min_ml_confidence: float = 0.6,
        base_strategy: BaseStrategy | None = None,
    ):
        self.mode = mode
        self.min_ml_confidence = min_ml_confidence
        self._base_strategy = base_strategy or FibonacciStrategy()
        self._predictor: Predictor | None = None

        if model_id:
            self._predictor = Predictor(model_id=model_id)

    def set_predictor(self, predictor: Predictor) -> None:
        """Set the ML predictor (useful for testing)."""
        self._predictor = predictor

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> TradeSignal | None:
        if self._predictor is None:
            logger.warning("No ML model loaded, falling back to base strategy")
            return self._base_strategy.generate_signal(df, symbol, timeframe)

        if self.mode == "standalone":
            return self._ml_standalone(df, symbol, timeframe)
        elif self.mode == "hybrid":
            return self._hybrid(df, symbol, timeframe)
        else:  # confirmation (default)
            return self._confirmation(df, symbol, timeframe)

    def _confirmation(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> TradeSignal | None:
        """ML confirms rule-based signals. Filters out low-confidence signals."""
        signal = self._base_strategy.generate_signal(df, symbol, timeframe)
        if signal is None:
            return None

        # Get ML prediction
        ml_result = self._predictor.predict(df)

        if ml_result["probability"] < self.min_ml_confidence:
            logger.info(
                "ML rejected signal: prob=%.4f < threshold=%.2f",
                ml_result["probability"], self.min_ml_confidence,
            )
            return None

        # Boost confidence with ML probability
        signal.confidence = (signal.confidence + ml_result["probability"]) / 2
        signal.strategy_name = self.name
        signal.metadata = signal.metadata or {}
        signal.metadata["ml_probability"] = ml_result["probability"]
        signal.metadata["ml_confidence"] = ml_result["confidence"]
        signal.metadata["mode"] = "confirmation"

        logger.info(
            "ML confirmed signal: %s %s, prob=%.4f",
            signal.direction.value, symbol, ml_result["probability"],
        )
        return signal

    def _ml_standalone(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> TradeSignal | None:
        """ML generates signals independently."""
        ml_result = self._predictor.predict(df)

        if ml_result["prediction"] != 1:
            return None
        if ml_result["probability"] < self.min_ml_confidence:
            return None

        current_price = df["close"].iloc[-1]
        sl, tp = self.calculate_sl_tp(df, SignalDirection.BUY, current_price)

        signal = TradeSignal(
            direction=SignalDirection.BUY,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            confidence=ml_result["probability"],
            strategy_name=self.name,
            metadata={
                "ml_probability": ml_result["probability"],
                "ml_confidence": ml_result["confidence"],
                "mode": "standalone",
            },
        )

        if self.validate_signal(signal):
            return signal
        return None

    def _hybrid(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> TradeSignal | None:
        """Both rule-based and ML must agree."""
        signal = self._base_strategy.generate_signal(df, symbol, timeframe)
        if signal is None:
            return None

        ml_result = self._predictor.predict(df)

        # Both must agree: rule says trade AND ML says trade
        if ml_result["prediction"] != 1:
            return None
        if ml_result["probability"] < self.min_ml_confidence:
            return None

        signal.confidence = (signal.confidence + ml_result["probability"]) / 2
        signal.strategy_name = self.name
        signal.metadata = signal.metadata or {}
        signal.metadata["ml_probability"] = ml_result["probability"]
        signal.metadata["mode"] = "hybrid"

        return signal

    def calculate_sl_tp(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        entry_price: float,
    ) -> tuple[float, float]:
        """Use ATR-based SL/TP for standalone mode."""
        atr = (df["high"] - df["low"]).tail(20).mean()

        if direction == SignalDirection.BUY:
            sl = entry_price - (atr * 1.5)
            tp = entry_price + (atr * 3.0)
        else:
            sl = entry_price + (atr * 1.5)
            tp = entry_price - (atr * 3.0)

        return round(sl, 8), round(tp, 8)
