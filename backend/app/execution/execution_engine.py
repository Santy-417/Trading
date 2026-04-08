import asyncio
import traceback
from collections import deque
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import update as sa_update

from app.core.logging_config import get_logger
from app.execution.news_filter import news_filter
from app.integrations.metatrader.mt5_client import MT5Client, OrderType, Timeframe, mt5_client
from app.integrations.supabase.client import _get_session_factory
from app.models.bot_config import BotConfig
from app.risk.risk_manager import RiskManager, risk_manager
from app.strategies import get_strategy
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)

_MAX_LOG_ENTRIES = 200


class BotState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class ExecutionEngine:
    """
    Main trading execution engine.

    Orchestrates: Market data → Strategy signal → Risk check → MT5 execution.

    The engine runs in an async loop, periodically checking for signals.
    """

    def __init__(
        self,
        mt5: MT5Client | None = None,
        risk: RiskManager | None = None,
    ):
        self._mt5 = mt5 or mt5_client
        self._risk = risk or risk_manager
        self._state = BotState.STOPPED
        self._strategy: BaseStrategy | None = None
        self._symbols: list[str] = []
        self._timeframe: str = "H1"
        self._task: asyncio.Task | None = None
        self._loop_interval: int = 60  # seconds between checks
        self._log_buffer: deque[dict] = deque(maxlen=_MAX_LOG_ENTRIES)

    def _log(self, level: str, message: str, symbol: str | None = None) -> None:
        """Log a message and store it in the buffer."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "symbol": symbol,
        }
        self._log_buffer.append(entry)
        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn(message)

    def get_logs(self, limit: int = 50) -> list[dict]:
        """Return the most recent log entries."""
        entries = list(self._log_buffer)
        return entries[-limit:]

    @property
    def state(self) -> BotState:
        return self._state

    async def start(
        self,
        strategy_name: str,
        symbols: list[str],
        timeframe: str = "H1",
        strategy_params: dict | None = None,
        loop_interval: int = 60,
    ) -> None:
        """Start the trading bot."""
        if self._state == BotState.RUNNING:
            self._log("warning", "Bot already running, ignoring start request")
            return

        # Deactivate kill switch if it was active (user explicitly restarting)
        if self._risk.kill_switch.is_activated:
            self._risk.deactivate_kill_switch()
            self._log("info", "Kill switch deactivated (bot restarted)")

        # Initialize MT5
        await self._mt5.initialize()

        # Set starting balance for daily loss tracking
        account = await self._mt5.get_account_info()
        self._risk.set_starting_balance(account["balance"])

        # Initialize strategy
        params = strategy_params or {}
        self._strategy = get_strategy(strategy_name, **params)
        self._symbols = symbols
        self._timeframe = timeframe
        self._loop_interval = loop_interval
        self._state = BotState.RUNNING

        self._log(
            "info",
            f"Bot started: strategy={strategy_name}, symbols={symbols}, "
            f"timeframe={timeframe}, interval={loop_interval}s, "
            f"balance=${account['balance']:,.2f}",
        )

        # Start the main loop
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the trading bot gracefully."""
        if self._state == BotState.STOPPED:
            return

        self._state = BotState.STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self._mt5.shutdown()
        self._log("info", "Bot stopped")

    async def kill(self, close_positions: bool = True) -> dict:
        """
        Emergency kill: stop bot and optionally close all positions.
        """
        self._risk.activate_kill_switch("Emergency kill triggered")

        result = {"positions_closed": []}
        if close_positions:
            try:
                await self._mt5.initialize()
                close_results = await self._mt5.close_all_positions()
                result["positions_closed"] = [
                    {"ticket": r.ticket, "success": r.success} for r in close_results
                ]
            except Exception as e:
                self._log("error", f"Kill switch failed to close positions: {e}")
                result["error"] = str(e)

        await self.stop()
        self._log("error", f"KILL SWITCH activated, close_positions={close_positions}")
        return result

    async def _run_loop(self) -> None:
        """Main trading loop with crash monitoring and exponential backoff retry."""
        _RETRY_DELAYS = [5, 10, 30]  # seconds: first crash, second, third+
        retry_count = 0
        self._time_close_done_today = False

        while self._state == BotState.RUNNING:
            try:
                await self._check_time_close()

                for symbol in self._symbols:
                    await self._process_symbol(symbol)

                # Successful cycle — reset retry counter and update heartbeat
                retry_count = 0
                await self._update_heartbeat()
                await asyncio.sleep(self._loop_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                tb = traceback.format_exc()
                self._log(
                    "error",
                    f"Bot loop crash (attempt #{retry_count + 1}): {e}\n{tb}",
                )
                await self._update_crash_state(error=e, tb=tb)

                delay = _RETRY_DELAYS[min(retry_count, len(_RETRY_DELAYS) - 1)]
                retry_count += 1
                self._log("warning", f"Retrying loop in {delay}s...")
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break

    async def _update_heartbeat(self) -> None:
        """Update last_heartbeat and clear error_state in bot_config after a successful cycle."""
        try:
            async with _get_session_factory()() as session:
                await session.execute(
                    sa_update(BotConfig)
                    .where(BotConfig.is_active.is_(True))
                    .values(
                        last_heartbeat=datetime.now(timezone.utc),
                        error_state=False,
                    )
                )
                await session.commit()
        except Exception as db_exc:
            self._log("warning", f"Heartbeat DB update failed: {db_exc}")

    async def _update_crash_state(self, error: Exception, tb: str) -> None:
        """Persist crash details to bot_config: error_state, last_error, crash_count."""
        try:
            error_text = f"{type(error).__name__}: {error}\n\n--- Traceback ---\n{tb}"
            async with _get_session_factory()() as session:
                await session.execute(
                    sa_update(BotConfig)
                    .where(BotConfig.is_active.is_(True))
                    .values(
                        error_state=True,
                        last_error=error_text,
                        crash_count=BotConfig.crash_count + 1,
                        last_heartbeat=datetime.now(timezone.utc),
                    )
                )
                await session.commit()
        except Exception as db_exc:
            self._log("warning", f"Crash state DB update failed: {db_exc}")

    async def _check_time_close(self) -> None:
        """Close all positions if strategy has a time-based close and time is reached."""
        if self._strategy is None:
            return

        close_time = getattr(self._strategy, "close_time_utc", None)
        if close_time is None:
            return

        now = datetime.now(timezone.utc)
        close_hour, close_minute = close_time
        current_mins = now.hour * 60 + now.minute
        close_mins = close_hour * 60 + close_minute

        # Reset flag at midnight
        if current_mins < 60:
            self._time_close_done_today = False

        if current_mins >= close_mins and not self._time_close_done_today:
            self._time_close_done_today = True
            self._log(
                "info",
                f"Time-based close triggered at {now.strftime('%H:%M')} UTC "
                f"(target: {close_hour:02d}:{close_minute:02d} UTC)",
            )
            try:
                close_results = await self._mt5.close_all_positions()
                closed_count = sum(1 for r in close_results if r.success)
                self._log(
                    "info",
                    f"Time-based close: {closed_count}/{len(close_results)} positions closed",
                )
            except Exception as e:
                self._log("error", f"Time-based close failed: {e}")

    async def _process_symbol(self, symbol: str) -> None:
        """Process a single symbol: get data -> generate signal -> execute."""
        if self._strategy is None:
            return

        # 0. News filter: skip if High Impact news is nearby
        now_utc = datetime.now(timezone.utc)
        if news_filter.is_restricted(symbol, now_utc):
            self._log(
                "warning",
                f"[{symbol}] Skipped: High Impact news within ±5 min window",
                symbol,
            )
            return

        # 1. Get market data
        try:
            tf = Timeframe(self._timeframe)
            df = await self._mt5.get_historical_data(symbol, tf, count=200)
            self._log("info", f"[{symbol}] Fetched {len(df)} bars ({self._timeframe})", symbol)
        except Exception as e:
            self._log("error", f"[{symbol}] Data fetch failed: {e}", symbol)
            return

        # 1b. Multi-timeframe: load lower TF data if strategy requires it
        choch_tf = getattr(self._strategy, "choch_timeframe", None)
        if choch_tf:
            try:
                lower_tf = Timeframe(choch_tf)
                df_lower = await self._mt5.get_historical_data(symbol, lower_tf, count=200)
                self._strategy._df_lower_tf = df_lower
                self._log(
                    "info",
                    f"[{symbol}] Loaded {len(df_lower)} bars ({choch_tf}) for multi-TF",
                    symbol,
                )
            except Exception as e:
                self._log("warning", f"[{symbol}] Lower TF data failed: {e}", symbol)
                self._strategy._df_lower_tf = None

        # 2. Generate signal
        signal = self._strategy.generate_signal(df, symbol, self._timeframe)
        if signal is None:
            self._log("info", f"[{symbol}] No signal from {self._strategy.name} strategy", symbol)
            return

        self._log(
            "info",
            f"[{symbol}] Signal: {signal.direction.value} @ SL={signal.stop_loss}, TP={signal.take_profit}",
            symbol,
        )

        # 3. Risk check
        account = await self._mt5.get_account_info()
        risk_result = self._risk.check_trade_allowed(
            balance=account["balance"],
            equity=account["equity"],
        )

        if not risk_result.allowed:
            self._log("warning", f"[{symbol}] Trade blocked by risk: {risk_result.reason}", symbol)
            return

        # 4. Calculate lot size (with ML-based risk override if available)
        symbol_info = await self._mt5.get_symbol_info(symbol)
        risk_kwargs = {}
        if signal.metadata and "risk_percent" in signal.metadata:
            risk_kwargs["risk_percent"] = signal.metadata["risk_percent"]
            self._log(
                "info",
                f"[{symbol}] ML risk override: {signal.metadata['risk_percent']}%",
                symbol,
            )

        lot_size = self._risk.calculate_lot_size(
            balance=account["balance"],
            equity=account["equity"],
            sl_pips=signal.sl_pips,
            pip_value=symbol_info.get("point", 0.0001) * symbol_info.get("trade_contract_size", 100000),
            volume_min=symbol_info.get("volume_min", 0.01),
            volume_max=symbol_info.get("volume_max", 100.0),
            volume_step=symbol_info.get("volume_step", 0.01),
            **risk_kwargs,
        )

        # 5. Execute trade
        direction = (
            OrderType.BUY if signal.direction == SignalDirection.BUY else OrderType.SELL
        )

        trade_result = await self._mt5.send_market_order(
            symbol=symbol,
            direction=direction,
            volume=lot_size,
            sl=signal.stop_loss,
            tp=signal.take_profit,
            comment=f"{self._strategy.name}|{self._timeframe}",
        )

        if trade_result.success:
            self._risk.record_trade()
            self._log(
                "info",
                f"[{symbol}] Trade executed: {direction.value} {lot_size} lots, "
                f"ticket=#{trade_result.ticket}, entry={trade_result.price}, "
                f"SL={signal.stop_loss}, TP={signal.take_profit}",
                symbol,
            )
        else:
            self._log(
                "error",
                f"[{symbol}] Trade failed: retcode={trade_result.retcode}, {trade_result.comment}",
                symbol,
            )

    def get_status(self) -> dict:
        """Get current bot status."""
        return {
            "state": self._state.value,
            "strategy": self._strategy.name if self._strategy else None,
            "symbols": self._symbols,
            "timeframe": self._timeframe,
            "risk": self._risk.get_status(),
        }


# Singleton instance
execution_engine = ExecutionEngine()
