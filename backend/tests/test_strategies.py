import numpy as np
import pandas as pd
import pytest

from app.strategies import get_strategy, STRATEGY_REGISTRY
from app.strategies.base import SignalDirection, TradeSignal
from app.strategies.manual import ManualStrategy


def _make_ohlcv(n: int = 100, base_price: float = 1.1000) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    close = base_price + np.cumsum(np.random.randn(n) * 0.0005)
    high = close + np.abs(np.random.randn(n) * 0.0003)
    low = close - np.abs(np.random.randn(n) * 0.0003)
    open_ = close + np.random.randn(n) * 0.0002

    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "tick_volume": np.random.randint(100, 5000, n),
    }, index=dates)
    return df


class TestStrategyRegistry:
    def test_get_fibonacci(self):
        strategy = get_strategy("fibonacci")
        assert strategy.name == "fibonacci"

    def test_get_ict(self):
        strategy = get_strategy("ict")
        assert strategy.name == "ict"

    def test_get_manual(self):
        strategy = get_strategy("manual")
        assert strategy.name == "manual"

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent")

    def test_registry_has_expected_strategies(self):
        assert set(STRATEGY_REGISTRY.keys()) == {"fibonacci", "ict", "manual", "hybrid_ml"}


class TestTradeSignal:
    def test_sl_pips(self):
        signal = TradeSignal(
            direction=SignalDirection.BUY,
            symbol="EURUSD",
            timeframe="H1",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
        )
        assert abs(signal.sl_pips - 0.005) < 1e-8

    def test_risk_reward_ratio(self):
        signal = TradeSignal(
            direction=SignalDirection.BUY,
            symbol="EURUSD",
            timeframe="H1",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
        )
        assert signal.risk_reward_ratio == pytest.approx(2.0)


class TestManualStrategy:
    def test_no_auto_signal(self):
        strategy = ManualStrategy()
        df = _make_ohlcv()
        signal = strategy.generate_signal(df, "EURUSD", "H1")
        assert signal is None

    def test_create_manual_signal(self):
        strategy = ManualStrategy()
        signal = strategy.create_manual_signal(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
        )
        assert signal.direction == SignalDirection.BUY
        assert signal.symbol == "EURUSD"
        assert signal.confidence == 1.0


class TestFibonacciStrategy:
    def test_generate_signal_returns_none_on_insufficient_data(self):
        strategy = get_strategy("fibonacci")
        df = _make_ohlcv(n=10)
        signal = strategy.generate_signal(df, "EURUSD", "H1")
        assert signal is None

    def test_generate_signal_with_enough_data(self):
        strategy = get_strategy("fibonacci")
        df = _make_ohlcv(n=200)
        # Signal may or may not be generated depending on random data
        signal = strategy.generate_signal(df, "EURUSD", "H1")
        if signal is not None:
            assert signal.direction in (SignalDirection.BUY, SignalDirection.SELL)
            assert signal.strategy_name == "fibonacci"


class TestICTStrategy:
    def test_generate_signal_returns_none_on_insufficient_data(self):
        strategy = get_strategy("ict")
        df = _make_ohlcv(n=10)
        signal = strategy.generate_signal(df, "EURUSD", "H1")
        assert signal is None

    def test_generate_signal_with_enough_data(self):
        strategy = get_strategy("ict")
        df = _make_ohlcv(n=200)
        signal = strategy.generate_signal(df, "EURUSD", "H1")
        if signal is not None:
            assert signal.direction in (SignalDirection.BUY, SignalDirection.SELL)
            assert signal.strategy_name == "ict"
