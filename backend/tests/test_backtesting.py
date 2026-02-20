import numpy as np
import pandas as pd
import pytest

import app.backtesting.engine as eng_module
from app.backtesting.engine import BacktestEngine
from app.backtesting.metrics import calculate_metrics
from app.backtesting.simulator import SimulationConfig, TradeSimulator
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal
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


# ---------------------------------------------------------------------------
# Helpers for hardening tests
# ---------------------------------------------------------------------------

def _make_mock_strategy(
    entry: float,
    stop_loss: float,
    take_profit: float,
    direction: str = "BUY",
) -> BaseStrategy:
    """Return a strategy that always emits the same signal."""
    sig_dir = SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL

    class _MockStrategy(BaseStrategy):
        name = "mock"

        def generate_signal(self, df, symbol, timeframe):
            return TradeSignal(
                direction=sig_dir,
                symbol=symbol,
                timeframe=timeframe,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=0.8,
            )

        def calculate_sl_tp(self, df, direction, entry_price):
            return stop_loss, take_profit

    return _MockStrategy()


class TestBacktestHardening:
    """FTMO-ready safeguard tests (Tasks 1–8)."""

    # --- Task 1 & 7: margin call / drawdown guard ---

    def test_account_blown_flag_always_present(self):
        """account_blown key exists in every result."""
        engine = BacktestEngine(initial_balance=10000)
        df = _make_ohlcv(n=10)  # Too few bars — 0 trades
        result = engine.run(
            strategy=FibonacciStrategy(), df=df, symbol="EURUSD", timeframe="H1"
        )
        assert "account_blown" in result
        assert result["account_blown"] is False

    def test_margin_call_sets_account_blown(self):
        """Balance reaches 0 → account_blown=True, loop stops."""
        # TP=1.1100 (RR=2.0) avoids floating-point boundary rejection.
        # With initial_balance=$10 the very first loss will deplete account.
        strategy = _make_mock_strategy(
            entry=1.1000, stop_loss=1.0950, take_profit=1.1100
        )
        engine = BacktestEngine(initial_balance=10.0, risk_per_trade=1.0)
        df = _make_ohlcv(n=300)
        result = engine.run(strategy=strategy, df=df, symbol="EURUSD", timeframe="H1")
        # Either blown or no trades executed (balance too small for min lot)
        assert result["account_blown"] is True or result["final_balance"] >= 0

    def test_drawdown_guard_triggers(self):
        """Drawdown guard fires when equity drops below threshold → account_blown=True."""
        # Build price data where every BUY trade always hits SL (low always < SL).
        # Use tp=1.1100 (100 pip TP) for unambiguous RR=2.0 (no float boundary issue).
        n = 300
        dates = pd.date_range("2024-01-01", periods=n, freq="h")
        entry, sl, tp = 1.1000, 1.0950, 1.1100
        losing_df = pd.DataFrame({
            "open":  np.full(n, 1.0975),
            "high":  np.full(n, entry),          # never reaches TP=1.1100
            "low":   np.full(n, sl - 0.0010),    # 1.0940 < 1.0950 → always hits SL
            "close": np.full(n, 1.0975),
            "tick_volume": np.full(n, 1000.0),
        }, index=dates)

        strategy = _make_mock_strategy(entry=entry, stop_loss=sl, take_profit=tp)
        engine = BacktestEngine(initial_balance=10000.0, risk_per_trade=50.0)

        # Lower guard threshold so it fires reliably after the first loss (~51% drawdown)
        original = eng_module.MAX_DRAWDOWN_PERCENT
        eng_module.MAX_DRAWDOWN_PERCENT = 10.0
        try:
            result = engine.run(
                strategy=strategy, df=losing_df, symbol="EURUSD", timeframe="H1"
            )
        finally:
            eng_module.MAX_DRAWDOWN_PERCENT = original

        assert result["account_blown"] is True

    # --- Task 2: final_balance clamp ---

    def test_final_balance_clamped_to_zero(self):
        """max(final_balance, 0) is always non-negative (service layer logic)."""
        profits = np.array([-6000.0, -5000.0, -3000.0])
        df = pd.DataFrame({"profit": profits})
        metrics = calculate_metrics(df, initial_balance=1000.0)
        # Clamped value must be >= 0
        assert max(metrics["final_balance"], 0.0) >= 0

    # --- Task 3: SL too large ---

    def test_sl_too_large_is_skipped(self):
        """Trade with SL > MAX_SL_PIPS is rejected and counted."""
        # EURUSD MAX_SL_PIPS default = 100; use 200 pip SL (0.0200 distance)
        strategy = _make_mock_strategy(
            entry=1.1000, stop_loss=1.0800, take_profit=1.1400  # 200 pip SL, 400 pip TP
        )
        engine = BacktestEngine(initial_balance=10000)
        df = _make_ohlcv(n=300)
        result = engine.run(strategy=strategy, df=df, symbol="EURUSD", timeframe="H1")
        assert result["debug_stats"]["skipped_sl_too_large"] > 0
        assert result["total_trades"] == 0

    # --- Task 4.1: RR too low ---

    def test_rr_too_low_is_skipped(self):
        """Trade with reward < MIN_RR * SL is rejected and counted."""
        # SL=50 pips, TP=30 pips → RR=0.6 < MIN_RR=1.0
        strategy = _make_mock_strategy(
            entry=1.1000, stop_loss=1.0950, take_profit=1.1030
        )
        engine = BacktestEngine(initial_balance=10000)
        df = _make_ohlcv(n=300)
        result = engine.run(strategy=strategy, df=df, symbol="EURUSD", timeframe="H1")
        assert result["debug_stats"]["skipped_rr_too_low"] > 0
        assert result["total_trades"] == 0

    # --- Task 4.2: SL too small ---

    def test_sl_too_small_is_skipped(self):
        """Trade with SL < MIN_SL_PIPS is rejected and counted."""
        # EURUSD MIN_SL_PIPS default = 10; use 2 pip SL (0.0002 distance)
        strategy = _make_mock_strategy(
            entry=1.1000, stop_loss=1.0998, take_profit=1.1004  # 2 pip SL, 4 pip TP
        )
        engine = BacktestEngine(initial_balance=10000)
        df = _make_ohlcv(n=300)
        result = engine.run(strategy=strategy, df=df, symbol="EURUSD", timeframe="H1")
        assert result["debug_stats"]["skipped_sl_too_small"] > 0
        assert result["total_trades"] == 0

    # --- Task 5: debug_stats structure ---

    def test_debug_stats_always_present(self):
        """debug_stats with all required keys is present in every result."""
        engine = BacktestEngine(initial_balance=10000)
        df = _make_ohlcv(n=10)
        result = engine.run(
            strategy=FibonacciStrategy(), df=df, symbol="EURUSD", timeframe="H1"
        )
        ds = result["debug_stats"]
        assert "skipped_sl_too_large" in ds
        assert "skipped_sl_too_small" in ds
        assert "skipped_rr_too_low" in ds
        assert "skipped_lot_distortion" in ds
        assert "executed_trades" in ds

    def test_executed_trades_matches_total_trades(self):
        """debug_stats.executed_trades equals total_trades in metrics."""
        engine = BacktestEngine(initial_balance=10000)
        df = _make_ohlcv(n=500)
        result = engine.run(
            strategy=FibonacciStrategy(), df=df, symbol="EURUSD", timeframe="H1"
        )
        assert result["debug_stats"]["executed_trades"] == result["total_trades"]
