"""
Tests for ExecutionEngine.

Covers:
  - Full signal → risk check → MT5 execution flow (BUY & SELL)
  - Risk gates blocking trades (circuit breaker, kill switch)
  - Loop resilience: crash does NOT stop the loop (retry + backoff)
  - No-signal path: place_order is never called
  - Crash monitoring: DB (bot_config) updated on loop exception

Architecture notes:
  - ExecutionEngine accepts injected mt5 and risk deps → easy to mock
  - _run_loop() is tested directly (no need for start() overhead)
  - asyncio.sleep is patched to control exactly how many cycles run
  - _get_session_factory is patched to avoid real DB connections
  - news_filter.is_restricted is patched to always return False
"""
import asyncio

import pandas as pd
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.execution.execution_engine import BotState, ExecutionEngine
from app.integrations.metatrader.mt5_client import OrderType
from app.risk.risk_manager import RiskCheckResult, RiskManager
from app.strategies.base import SignalDirection, TradeSignal


# ─── data builders ──────────────────────────────────────────────────────────


def make_ohlcv_df(n: int = 200) -> pd.DataFrame:
    """Realistic OHLCV DataFrame that mimics what MT5 returns."""
    dates = pd.date_range("2026-01-01", periods=n, freq="1h")
    base = 1.0800
    return pd.DataFrame(
        {
            "open":        [base + i * 0.0001 for i in range(n)],
            "high":        [base + 0.0010 + i * 0.0001 for i in range(n)],
            "low":         [base - 0.0010 + i * 0.0001 for i in range(n)],
            "close":       [base + 0.0005 + i * 0.0001 for i in range(n)],
            "tick_volume": [1000 + i for i in range(n)],
        },
        index=dates,
    )


def make_trade_signal(direction: SignalDirection = SignalDirection.BUY) -> TradeSignal:
    if direction == SignalDirection.BUY:
        return TradeSignal(
            direction=SignalDirection.BUY,
            symbol="EURUSD",
            timeframe="H1",
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0915,
            confidence=0.80,
        )
    return TradeSignal(
        direction=SignalDirection.SELL,
        symbol="EURUSD",
        timeframe="H1",
        entry_price=1.0800,
        stop_loss=1.0850,
        take_profit=1.0735,
        confidence=0.75,
    )


def make_order_result(success: bool = True) -> MagicMock:
    r = MagicMock()
    r.success = success
    r.ticket = 123456
    r.price = 1.0850
    r.retcode = 10009
    r.comment = "Request completed"
    return r


# ─── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_mt5() -> AsyncMock:
    mt5 = AsyncMock()
    mt5.initialize.return_value = None
    mt5.shutdown.return_value = None
    mt5.get_account_info.return_value = {
        "balance": 10_000.0,
        "equity": 9_900.0,
        "margin": 100.0,
        "free_margin": 9_800.0,
    }
    mt5.get_historical_data.return_value = make_ohlcv_df()
    mt5.get_symbol_info.return_value = {
        "point": 0.0001,
        "trade_contract_size": 100_000.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
    }
    mt5.send_market_order.return_value = make_order_result(success=True)
    return mt5


@pytest.fixture
def mock_risk() -> MagicMock:
    risk = MagicMock(spec=RiskManager)
    risk.kill_switch = MagicMock()
    risk.kill_switch.is_activated = False
    risk.check_trade_allowed.return_value = RiskCheckResult(allowed=True)
    risk.calculate_lot_size.return_value = 0.01
    risk.record_trade.return_value = None
    risk.set_starting_balance.return_value = None
    risk.deactivate_kill_switch.return_value = None
    risk.get_status.return_value = {
        "kill_switch_active": False,
        "circuit_breaker_tripped": False,
        "starting_balance": 10_000.0,
        "max_drawdown_percent": 10.0,
        "max_daily_loss_percent": 3.0,
        "max_trades_per_hour": 10,
    }
    return risk


@pytest.fixture
def mock_strategy() -> MagicMock:
    strategy = MagicMock()
    strategy.name = "bias"
    strategy.choch_timeframe = None   # Disable lower-TF loading
    strategy.close_time_utc = None    # Disable time-based close
    strategy.generate_signal.return_value = make_trade_signal(SignalDirection.BUY)
    return strategy


@pytest.fixture
def mock_db_session():
    """
    Mock for _get_session_factory used by _update_heartbeat / _update_crash_state.

    Usage:
        mock_sf, mock_session = mock_db_session
        with patch("app.execution.execution_engine._get_session_factory", mock_sf):
            ...
        assert mock_session.execute.called
    """
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    mock_session.commit = AsyncMock(return_value=None)

    # async with _get_session_factory()() as session: → session is mock_session
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    # _get_session_factory()  →  sessionmaker (mock_sf.return_value)
    # sessionmaker()          →  context manager (mock_cm)
    mock_sf = MagicMock()
    mock_sf.return_value.return_value = mock_cm

    return mock_sf, mock_session


# ─── engine builder ─────────────────────────────────────────────────────────


def build_engine(
    mock_mt5: AsyncMock,
    mock_risk: MagicMock,
    mock_strategy: MagicMock,
    *,
    symbols: list[str] | None = None,
) -> ExecutionEngine:
    """
    Creates an ExecutionEngine already in RUNNING state with injected mocks.
    Bypasses start() so tests don't need extra MT5 / DB setup.
    """
    engine = ExecutionEngine(mt5=mock_mt5, risk=mock_risk)
    engine._state = BotState.RUNNING
    engine._strategy = mock_strategy
    engine._symbols = symbols or ["EURUSD"]
    engine._timeframe = "H1"
    engine._loop_interval = 0  # No real sleep between cycles
    engine._time_close_done_today = False
    return engine


# ─── sleep helpers ──────────────────────────────────────────────────────────


def stop_after_n_sleeps(n: int):
    """
    Returns an async sleep replacement that raises CancelledError on the
    n-th call, cleanly ending _run_loop via `except asyncio.CancelledError`.
    """
    call_count = 0

    async def _sleep(delay):
        nonlocal call_count
        call_count += 1
        if call_count >= n:
            raise asyncio.CancelledError

    return _sleep


# ─── common patch context ───────────────────────────────────────────────────

_NO_NEWS = {"app.execution.execution_engine.news_filter.is_restricted": False}


# ════════════════════════════════════════════════════════════════════════════
# 1 & 2 — Full signal flow
# ════════════════════════════════════════════════════════════════════════════


class TestSignalExecution:
    """Verify that a valid signal results in exactly one MT5 order."""

    async def test_full_signal_flow_buy(self, mock_mt5, mock_risk, mock_strategy, mock_db_session):
        mock_sf, _ = mock_db_session
        mock_strategy.generate_signal.return_value = make_trade_signal(SignalDirection.BUY)
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_after_n_sleeps(1)),
        ):
            await engine._run_loop()

        mock_mt5.send_market_order.assert_called_once()
        kw = mock_mt5.send_market_order.call_args.kwargs
        assert kw["symbol"] == "EURUSD"
        assert kw["direction"] == OrderType.BUY
        assert kw["sl"] == pytest.approx(1.0800, abs=1e-5)
        assert kw["tp"] == pytest.approx(1.0915, abs=1e-5)
        assert kw["volume"] == pytest.approx(0.01)

    async def test_full_signal_flow_sell(self, mock_mt5, mock_risk, mock_strategy, mock_db_session):
        mock_sf, _ = mock_db_session
        mock_strategy.generate_signal.return_value = make_trade_signal(SignalDirection.SELL)
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_after_n_sleeps(1)),
        ):
            await engine._run_loop()

        mock_mt5.send_market_order.assert_called_once()
        kw = mock_mt5.send_market_order.call_args.kwargs
        assert kw["symbol"] == "EURUSD"
        assert kw["direction"] == OrderType.SELL
        assert kw["sl"] == pytest.approx(1.0850, abs=1e-5)
        assert kw["tp"] == pytest.approx(1.0735, abs=1e-5)
        assert kw["volume"] == pytest.approx(0.01)


# ════════════════════════════════════════════════════════════════════════════
# 3 & 4 — Risk gates
# ════════════════════════════════════════════════════════════════════════════


class TestRiskGates:
    """Verify that risk blocks prevent any order from being placed."""

    async def test_risk_manager_blocks_trade(self, mock_mt5, mock_risk, mock_strategy, mock_db_session):
        mock_sf, _ = mock_db_session
        mock_risk.check_trade_allowed.return_value = RiskCheckResult(
            allowed=False,
            reason="Circuit breaker tripped: max drawdown exceeded",
        )
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_after_n_sleeps(1)),
        ):
            await engine._run_loop()

        mock_mt5.send_market_order.assert_not_called()

    async def test_kill_switch_stops_execution(self, mock_mt5, mock_risk, mock_strategy, mock_db_session):
        mock_sf, _ = mock_db_session
        mock_risk.check_trade_allowed.return_value = RiskCheckResult(
            allowed=False,
            reason="Kill switch active: Emergency stop",
        )
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_after_n_sleeps(1)),
        ):
            await engine._run_loop()

        mock_mt5.send_market_order.assert_not_called()


# ════════════════════════════════════════════════════════════════════════════
# 5, 6, 7 — Crash resilience & monitoring
# ════════════════════════════════════════════════════════════════════════════


class TestCrashResilience:
    """Verify loop resilience, no-signal path, and DB crash monitoring."""

    async def test_no_signal_no_trade(self, mock_mt5, mock_risk, mock_strategy, mock_db_session):
        mock_sf, _ = mock_db_session
        mock_strategy.generate_signal.return_value = None  # Strategy returns no signal
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_after_n_sleeps(1)),
        ):
            await engine._run_loop()

        mock_mt5.send_market_order.assert_not_called()

    async def test_mt5_exception_does_not_crash_loop(
        self, mock_mt5, mock_risk, mock_strategy, mock_db_session
    ):
        """
        An exception in generate_signal must NOT stop the loop.
        The loop should:
          1. Catch the exception (crash handler)
          2. Sleep with backoff (sleep call #1 → returns None)
          3. Retry the cycle — this time generate_signal succeeds
          4. Place a trade successfully
          5. Stop on the next normal sleep (sleep call #2 → CancelledError)
        """
        mock_sf, _ = mock_db_session

        generate_call_count = 0

        def generate_signal_side_effect(df, symbol, timeframe):
            nonlocal generate_call_count
            generate_call_count += 1
            if generate_call_count == 1:
                raise RuntimeError("Simulated connection loss on cycle 1")
            return make_trade_signal(SignalDirection.BUY)

        mock_strategy.generate_signal.side_effect = generate_signal_side_effect
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        # sleep #1 = backoff after crash (return None → loop retries)
        # sleep #2 = normal cycle sleep (CancelledError → loop exits cleanly)
        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_after_n_sleeps(2)),
        ):
            await engine._run_loop()

        assert generate_call_count == 2, (
            f"Expected 2 generate_signal calls (1 crash + 1 retry), got {generate_call_count}"
        )
        # Second cycle recovered and placed a trade
        mock_mt5.send_market_order.assert_called_once()

    async def test_crash_monitoring_updates_db(
        self, mock_mt5, mock_risk, mock_strategy, mock_db_session
    ):
        """
        When an exception bubbles up to _run_loop, _update_crash_state must
        write error_state=True and increment crash_count in bot_config via DB session.
        """
        mock_sf, mock_session = mock_db_session

        mock_strategy.generate_signal.side_effect = ValueError(
            "Forced crash: testing DB crash monitoring"
        )
        engine = build_engine(mock_mt5, mock_risk, mock_strategy)

        # Backoff sleep raises CancelledError so the loop stops after 1 crash cycle
        async def stop_on_backoff(delay):
            raise asyncio.CancelledError

        with (
            patch("app.execution.execution_engine._get_session_factory", mock_sf),
            patch("app.execution.execution_engine.news_filter.is_restricted", return_value=False),
            patch("asyncio.sleep", side_effect=stop_on_backoff),
        ):
            await engine._run_loop()

        # _update_crash_state ran and committed the error state
        assert mock_session.execute.called, (
            "session.execute not called — _update_crash_state did not persist crash to DB"
        )
        assert mock_session.commit.called, (
            "session.commit not called — DB transaction was not committed"
        )
        # No trade should have been placed (loop crashed before execution step)
        mock_mt5.send_market_order.assert_not_called()
