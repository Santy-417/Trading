import asyncio
from datetime import datetime, timezone
from enum import Enum

from app.core.logging_config import get_logger
from app.integrations.metatrader.mt5_client import MT5Client, OrderType, Timeframe, mt5_client
from app.risk.risk_manager import RiskManager, risk_manager
from app.strategies import get_strategy
from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal

logger = get_logger(__name__)


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
            logger.warning("bot_already_running")
            return

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

        logger.info(
            "bot_started: strategy=%s, symbols=%s, timeframe=%s",
            strategy_name, symbols, timeframe,
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
        logger.info("bot_stopped")

    async def kill(self, close_positions: bool = True) -> dict:
        """
        Emergency kill: stop bot and optionally close all positions.
        """
        self._risk.activate_kill_switch("Emergency kill triggered")

        result = {"positions_closed": []}
        if close_positions:
            # Re-initialize MT5 if needed
            try:
                await self._mt5.initialize()
                close_results = await self._mt5.close_all_positions()
                result["positions_closed"] = [
                    {"ticket": r.ticket, "success": r.success} for r in close_results
                ]
            except Exception as e:
                logger.error("kill_close_positions_failed: error=%s", str(e))
                result["error"] = str(e)

        await self.stop()
        logger.critical("bot_killed: close_positions=%s", close_positions)
        return result

    async def _run_loop(self) -> None:
        """Main trading loop."""
        while self._state == BotState.RUNNING:
            try:
                for symbol in self._symbols:
                    await self._process_symbol(symbol)
                await asyncio.sleep(self._loop_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("bot_loop_error: error=%s", str(e))
                self._state = BotState.ERROR
                break

    async def _process_symbol(self, symbol: str) -> None:
        """Process a single symbol: get data → generate signal → execute."""
        if self._strategy is None:
            return

        # 1. Get market data
        try:
            tf = Timeframe(self._timeframe)
            df = await self._mt5.get_historical_data(symbol, tf, count=200)
        except Exception as e:
            logger.error("data_fetch_failed: symbol=%s, error=%s", symbol, str(e))
            return

        # 2. Generate signal
        signal = self._strategy.generate_signal(df, symbol, self._timeframe)
        if signal is None:
            return

        # 3. Risk check
        account = await self._mt5.get_account_info()
        risk_result = self._risk.check_trade_allowed(
            balance=account["balance"],
            equity=account["equity"],
        )

        if not risk_result.allowed:
            logger.warning(
                "trade_blocked_by_risk: symbol=%s, reason=%s",
                symbol, risk_result.reason,
            )
            return

        # 4. Calculate lot size
        symbol_info = await self._mt5.get_symbol_info(symbol)
        lot_size = self._risk.calculate_lot_size(
            balance=account["balance"],
            equity=account["equity"],
            sl_pips=signal.sl_pips,
            pip_value=symbol_info.get("point", 0.0001) * symbol_info.get("trade_contract_size", 100000),
            volume_min=symbol_info.get("volume_min", 0.01),
            volume_max=symbol_info.get("volume_max", 100.0),
            volume_step=symbol_info.get("volume_step", 0.01),
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
            logger.info(
                "trade_executed: symbol=%s, direction=%s, lot=%s, ticket=%s, entry=%s, sl=%s, tp=%s, strategy=%s",
                symbol, direction.value, lot_size, trade_result.ticket,
                trade_result.price, signal.stop_loss, signal.take_profit,
                self._strategy.name,
            )
        else:
            logger.error(
                "trade_execution_failed: symbol=%s, retcode=%s, comment=%s",
                symbol, trade_result.retcode, trade_result.comment,
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
