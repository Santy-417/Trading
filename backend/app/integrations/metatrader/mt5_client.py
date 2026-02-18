import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from functools import wraps
from typing import Any

import MetaTrader5 as mt5
import pandas as pd

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class OrderType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class Timeframe(str, Enum):
    M1 = "M1"
    M3 = "M3"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

    @property
    def mt5_value(self) -> int:
        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M3": mt5.TIMEFRAME_M3,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        return mapping[self.value]


@dataclass
class TradeResult:
    success: bool
    ticket: int | None = None
    price: float | None = None
    volume: float | None = None
    comment: str = ""
    retcode: int | None = None


def _with_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for MT5 operations with retry logic."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "mt5_operation_retry: operation=%s, attempt=%s, max_retries=%s, error=%s",
                        func.__name__, attempt, max_retries, str(e),
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(delay * attempt)
            logger.error(
                "mt5_operation_failed: operation=%s, error=%s",
                func.__name__, str(last_error),
            )
            raise last_error
        return wrapper
    return decorator


class MT5Client:
    """MetaTrader 5 client wrapper with retry mechanism and structured logging."""

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize connection to MT5 terminal."""
        settings = get_settings()

        def _init():
            if not mt5.initialize():
                raise ConnectionError(f"MT5 init failed: {mt5.last_error()}")
            authorized = mt5.login(
                login=settings.mt5_login,
                password=settings.mt5_password,
                server=settings.mt5_server,
            )
            if not authorized:
                mt5.shutdown()
                raise ConnectionError(f"MT5 login failed: {mt5.last_error()}")
            return True

        result = await asyncio.to_thread(_init)
        self._initialized = result
        logger.info(
            "mt5_initialized: server=%s, login=%s",
            settings.mt5_server, settings.mt5_login,
        )
        return result

    async def shutdown(self) -> None:
        """Shutdown MT5 connection."""
        await asyncio.to_thread(mt5.shutdown)
        self._initialized = False
        logger.info("mt5_shutdown")

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("MT5 client not initialized. Call initialize() first.")

    def _validate_symbol(self, symbol: str) -> None:
        """Validate that the symbol exists and is available for trading."""
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"Symbol '{symbol}' not found in MT5")
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise ValueError(f"Failed to select symbol '{symbol}'")

    @_with_retry(max_retries=3)
    async def send_market_order(
        self,
        symbol: str,
        direction: OrderType,
        volume: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
        magic: int = 100000,
    ) -> TradeResult:
        """Send a market order (BUY or SELL)."""
        self._ensure_initialized()

        def _execute():
            self._validate_symbol(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise ValueError(f"Cannot get tick for {symbol}")

            price = tick.ask if direction == OrderType.BUY else tick.bid
            order_type = (
                mt5.ORDER_TYPE_BUY if direction == OrderType.BUY else mt5.ORDER_TYPE_SELL
            )

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp

            result = mt5.order_send(request)
            if result is None:
                raise RuntimeError(f"Order send returned None: {mt5.last_error()}")

            return TradeResult(
                success=result.retcode == mt5.TRADE_RETCODE_DONE,
                ticket=result.order if result.retcode == mt5.TRADE_RETCODE_DONE else None,
                price=result.price,
                volume=result.volume,
                comment=result.comment,
                retcode=result.retcode,
            )

        trade_result = await asyncio.to_thread(_execute)
        logger.info(
            "mt5_market_order: symbol=%s, direction=%s, volume=%s, success=%s, ticket=%s, retcode=%s",
            symbol, direction.value, volume, trade_result.success,
            trade_result.ticket, trade_result.retcode,
        )
        return trade_result

    @_with_retry(max_retries=3)
    async def send_limit_order(
        self,
        symbol: str,
        direction: OrderType,
        volume: float,
        price: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
        magic: int = 100000,
    ) -> TradeResult:
        """Send a pending limit order."""
        self._ensure_initialized()

        def _execute():
            self._validate_symbol(symbol)

            type_mapping = {
                OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
                OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
                OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
                OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP,
            }

            order_type = type_mapping.get(direction)
            if order_type is None:
                raise ValueError(f"Invalid pending order type: {direction}")

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp

            result = mt5.order_send(request)
            if result is None:
                raise RuntimeError(f"Limit order returned None: {mt5.last_error()}")

            return TradeResult(
                success=result.retcode == mt5.TRADE_RETCODE_DONE,
                ticket=result.order if result.retcode == mt5.TRADE_RETCODE_DONE else None,
                price=result.price,
                volume=result.volume,
                comment=result.comment,
                retcode=result.retcode,
            )

        trade_result = await asyncio.to_thread(_execute)
        logger.info(
            "mt5_limit_order: symbol=%s, direction=%s, volume=%s, price=%s, success=%s, ticket=%s",
            symbol, direction.value, volume, price,
            trade_result.success, trade_result.ticket,
        )
        return trade_result

    @_with_retry(max_retries=3)
    async def close_position(self, ticket: int) -> TradeResult:
        """Close an open position by ticket number."""
        self._ensure_initialized()

        def _execute():
            position = mt5.positions_get(ticket=ticket)
            if not position:
                raise ValueError(f"Position {ticket} not found")

            pos = position[0]
            close_type = (
                mt5.ORDER_TYPE_SELL
                if pos.type == mt5.ORDER_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )
            tick = mt5.symbol_info_tick(pos.symbol)
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": "close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result is None:
                raise RuntimeError(f"Close position returned None: {mt5.last_error()}")

            return TradeResult(
                success=result.retcode == mt5.TRADE_RETCODE_DONE,
                ticket=result.order if result.retcode == mt5.TRADE_RETCODE_DONE else None,
                price=result.price,
                volume=result.volume,
                comment=result.comment,
                retcode=result.retcode,
            )

        trade_result = await asyncio.to_thread(_execute)
        logger.info(
            "mt5_close_position: ticket=%s, success=%s",
            ticket, trade_result.success,
        )
        return trade_result

    async def close_all_positions(self) -> list[TradeResult]:
        """Close all open positions. Used by kill switch."""
        positions = await self.get_open_positions()
        results = []
        for pos in positions:
            result = await self.close_position(pos["ticket"])
            results.append(result)
        return results

    async def get_open_positions(self) -> list[dict[str, Any]]:
        """Get all currently open positions."""
        self._ensure_initialized()

        def _get():
            positions = mt5.positions_get()
            if positions is None:
                return []
            return [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": p.volume,
                    "price_open": p.price_open,
                    "price_current": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": p.profit,
                    "swap": p.swap,
                    "commission": p.commission,
                    "magic": p.magic,
                    "comment": p.comment,
                    "time": datetime.fromtimestamp(p.time),
                }
                for p in positions
            ]

        return await asyncio.to_thread(_get)

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int = 1000,
        date_from: datetime | None = None,
    ) -> pd.DataFrame:
        """Get historical OHLCV data from MT5."""
        self._ensure_initialized()

        def _get():
            self._validate_symbol(symbol)
            if date_from:
                rates = mt5.copy_rates_from(
                    symbol, timeframe.mt5_value, date_from, count
                )
            else:
                rates = mt5.copy_rates_from_pos(
                    symbol, timeframe.mt5_value, 0, count
                )

            if rates is None or len(rates) == 0:
                raise ValueError(
                    f"No historical data for {symbol} {timeframe.value}"
                )

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)
            return df

        return await asyncio.to_thread(_get)

    async def get_account_info(self) -> dict[str, Any]:
        """Get current account information."""
        self._ensure_initialized()

        def _get():
            info = mt5.account_info()
            if info is None:
                raise RuntimeError("Failed to get account info")
            return {
                "login": info.login,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "free_margin": info.margin_free,
                "margin_level": info.margin_level,
                "profit": info.profit,
                "leverage": info.leverage,
                "currency": info.currency,
                "server": info.server,
                "name": info.name,
            }

        return await asyncio.to_thread(_get)

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Get symbol information (spread, digits, lot sizes, etc.)."""
        self._ensure_initialized()

        def _get():
            self._validate_symbol(symbol)
            info = mt5.symbol_info(symbol)
            return {
                "name": info.name,
                "spread": info.spread,
                "digits": info.digits,
                "point": info.point,
                "trade_contract_size": info.trade_contract_size,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
                "volume_step": info.volume_step,
            }

        return await asyncio.to_thread(_get)


# Singleton instance
mt5_client = MT5Client()
