import numpy as np
import pandas as pd
import pytest

from app.backtesting.engine import BacktestEngine
from app.backtesting.metrics import calculate_metrics
from app.backtesting.simulator import SimulationConfig, TradeSimulator
from app.strategies.fibonacci import FibonacciStrategy


def _make_ohlcv(n: int = 500, base_price: float = 1.1000) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    close = base_price + np.cumsum(np.random.randn(n) * 0.0005)
    high = close + np.abs(np.random.randn(n) * 0.0003)
    low = close - np.abs(np.random.randn(n) * 0.0003)
    open_ = close + np.random.randn(n) * 0.0002

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "tick_volume": np.random.randint(100, 5000, n),
    }, index=dates)


class TestMetrics:
    def test_empty_trades(self):
        df = pd.DataFrame(columns=["profit"])
        result = calculate_metrics(df)
        assert result["total_trades"] == 0
        assert result["win_rate"] == 0.0

    def test_all_winning(self):
        df = pd.DataFrame({"profit": [100, 200, 150]})
        result = calculate_metrics(df, initial_balance=10000)
        assert result["total_trades"] == 3
        assert result["winning_trades"] == 3
        assert result["losing_trades"] == 0
        assert result["win_rate"] == 100.0
        assert result["net_profit"] == 450.0

    def test_mixed_trades(self):
        df = pd.DataFrame({"profit": [100, -50, 200, -30, 80]})
        result = calculate_metrics(df, initial_balance=10000)
        assert result["total_trades"] == 5
        assert result["winning_trades"] == 3
        assert result["losing_trades"] == 2
        assert result["win_rate"] == 60.0
        assert result["net_profit"] == 300.0
        assert result["profit_factor"] > 0

    def test_equity_curve(self):
        df = pd.DataFrame({"profit": [100, -50, 200]})
        result = calculate_metrics(df, initial_balance=10000)
        assert len(result["equity_curve"]) == 3
        assert result["equity_curve"][-1] == 10250.0

    def test_consecutive_streaks(self):
        df = pd.DataFrame({"profit": [10, 20, 30, -5, -10, 15]})
        result = calculate_metrics(df, initial_balance=10000)
        assert result["max_consecutive_wins"] == 3
        assert result["max_consecutive_losses"] == 2


class TestSimulator:
    def test_simulator_buy_tp_hit(self):
        config = SimulationConfig(
            spread_pips=0, commission_per_lot=0, slippage_pips=0,
            pip_value=10, point=0.0001,
        )
        sim = TradeSimulator(config)

        # TP is above entry, high prices reach TP
        highs = np.array([1.1000, 1.1050, 1.1100, 1.1200])
        lows = np.array([1.0990, 1.0980, 1.1000, 1.1050])

        result = sim.simulate_trade(
            entry_price=1.1000, stop_loss=1.0950, take_profit=1.1100,
            direction="BUY", lot_size=0.1,
            high_prices=highs, low_prices=lows, bar_index=0,
        )

        assert result is not None
        assert result.profit > 0

    def test_simulator_returns_none_if_not_closed(self):
        config = SimulationConfig(
            spread_pips=0, commission_per_lot=0, slippage_pips=0,
            pip_value=10, point=0.0001,
        )
        sim = TradeSimulator(config)

        # Price doesn't reach SL or TP
        highs = np.array([1.1000, 1.1005])
        lows = np.array([1.0995, 1.0990])

        result = sim.simulate_trade(
            entry_price=1.1000, stop_loss=1.0900, take_profit=1.1200,
            direction="BUY", lot_size=0.1,
            high_prices=highs, low_prices=lows, bar_index=0,
        )

        assert result is None


class TestBacktestEngine:
    def test_run_returns_metrics(self):
        engine = BacktestEngine(initial_balance=10000, risk_per_trade=1.0)
        df = _make_ohlcv(n=500)
        strategy = FibonacciStrategy()

        result = engine.run(
            strategy=strategy, df=df, symbol="EURUSD", timeframe="H1"
        )

        assert "total_trades" in result
        assert "win_rate" in result
        assert "sharpe_ratio" in result
        assert "net_profit" in result
        assert result["strategy"] == "fibonacci"
        assert result["symbol"] == "EURUSD"

    def test_run_with_insufficient_data(self):
        engine = BacktestEngine()
        df = _make_ohlcv(n=10)
        strategy = FibonacciStrategy()

        result = engine.run(
            strategy=strategy, df=df, symbol="EURUSD", timeframe="H1"
        )

        assert result["total_trades"] == 0
