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

    def _get_filling_mode(self, symbol: str) -> int:
        """Get the appropriate filling mode for a symbol based on what it supports."""
        info = mt5.symbol_info(symbol)
        if info is None:
            # Fallback to IOC
            return mt5.ORDER_FILLING_IOC

        filling_mode = info.filling_mode
        # Check supported modes in priority order: FOK > IOC > RETURN
        if filling_mode & 1:  # SYMBOL_FILLING_FOK
            return mt5.ORDER_FILLING_FOK
        elif filling_mode & 2:  # SYMBOL_FILLING_IOC
            return mt5.ORDER_FILLING_IOC
        elif filling_mode & 4:  # SYMBOL_FILLING_RETURN (most brokers support this)
            return mt5.ORDER_FILLING_RETURN
        else:
            # Default fallback
            return mt5.ORDER_FILLING_RETURN

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
            filling_mode = self._get_filling_mode(symbol)

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
                "type_filling": filling_mode,
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

            filling_mode = self._get_filling_mode(symbol)

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
                "type_filling": filling_mode,
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
            filling_mode = self._get_filling_mode(pos.symbol)

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
                "type_filling": filling_mode,
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

    async def modify_position(
        self,
        ticket: int,
        sl: float | None = None,
        tp: float | None = None,
    ) -> TradeResult:
        """Modify stop loss and/or take profit of an existing position."""
        self._ensure_initialized()

        def _execute():
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return TradeResult(success=False, comment=f"Position {ticket} not found", retcode=-1)

            pos = positions[0]
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": pos.symbol,
                "position": ticket,
                "sl": sl if sl is not None else pos.sl,
                "tp": tp if tp is not None else pos.tp,
            }

            result = mt5.order_send(request)
            if result is None:
                raise RuntimeError(f"Modify position returned None: {mt5.last_error()}")

            return TradeResult(
                success=result.retcode == mt5.TRADE_RETCODE_DONE,
                ticket=ticket,
                comment=result.comment,
                retcode=result.retcode,
            )

        trade_result = await asyncio.to_thread(_execute)
        logger.info(
            "mt5_modify_position: ticket=%s, sl=%s, tp=%s, success=%s",
            ticket, sl, tp, trade_result.success,
        )
        return trade_result

    async def partial_close(self, ticket: int, volume: float) -> TradeResult:
        """Partially close an open position by specifying the volume to close."""
        self._ensure_initialized()

        def _execute():
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                raise ValueError(f"Position {ticket} not found")

            pos = positions[0]
            close_type = (
                mt5.ORDER_TYPE_SELL
                if pos.type == mt5.ORDER_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )
            tick = mt5.symbol_info_tick(pos.symbol)
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            filling_mode = self._get_filling_mode(pos.symbol)

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": f"partial_close_{volume}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            result = mt5.order_send(request)
            if result is None:
                raise RuntimeError(f"Partial close returned None: {mt5.last_error()}")

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
            "mt5_partial_close: ticket=%s, volume=%s, success=%s",
            ticket, volume, trade_result.success,
        )
        return trade_result

    async def get_pending_orders(self) -> list[dict[str, Any]]:
        """Get all pending orders (limit/stop orders not yet triggered)."""
        self._ensure_initialized()

        TYPE_MAP = {
            mt5.ORDER_TYPE_BUY_LIMIT: "BUY_LIMIT",
            mt5.ORDER_TYPE_SELL_LIMIT: "SELL_LIMIT",
            mt5.ORDER_TYPE_BUY_STOP: "BUY_STOP",
            mt5.ORDER_TYPE_SELL_STOP: "SELL_STOP",
            mt5.ORDER_TYPE_BUY_STOP_LIMIT: "BUY_STOP_LIMIT",
            mt5.ORDER_TYPE_SELL_STOP_LIMIT: "SELL_STOP_LIMIT",
        }

        def _get():
            orders = mt5.orders_get()
            if orders is None:
                return []
            return [
                {
                    "ticket": o.ticket,
                    "symbol": o.symbol,
                    "type": TYPE_MAP.get(o.type, str(o.type)),
                    "volume_initial": o.volume_initial,
                    "volume_current": o.volume_current,
                    "price_open": o.price_open,
                    "stop_loss": o.sl,
                    "take_profit": o.tp,
                    "price_current": o.price_current,
                    "comment": o.comment,
                    "time_setup": datetime.fromtimestamp(o.time_setup).isoformat(),
                }
                for o in orders
                if o.type in TYPE_MAP
            ]

        result = await asyncio.to_thread(_get)
        logger.info("get_pending_orders returning %d orders", len(result))
        return result

    async def cancel_order(self, ticket: int) -> TradeResult:
        """Cancel a pending order by ticket number."""
        self._ensure_initialized()

        def _execute():
            orders = mt5.orders_get(ticket=ticket)
            if not orders:
                return TradeResult(success=False, comment=f"Order {ticket} not found", retcode=-1)

            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
            }
            result = mt5.order_send(request)
            if result is None:
                raise RuntimeError(f"Cancel order returned None: {mt5.last_error()}")

            return TradeResult(
                success=result.retcode == mt5.TRADE_RETCODE_DONE,
                ticket=ticket,
                comment=result.comment,
                retcode=result.retcode,
            )

        trade_result = await asyncio.to_thread(_execute)
        logger.info("mt5_cancel_order: ticket=%s, success=%s", ticket, trade_result.success)
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
                logger.warning("MT5 positions_get returned None")
                return []

            logger.info(f"MT5 returned {len(positions)} open positions")
            return [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": p.volume,
                    "price_open": p.price_open,
                    "price_current": p.price_current,
                    "stop_loss": p.sl,
                    "take_profit": p.tp,
                    "profit": p.profit,
                    "swap": p.swap,
                    "commission": 0.0,  # Commission not available for open positions
                    "magic": p.magic,
                    "comment": p.comment,
                    "time_open": datetime.fromtimestamp(p.time).isoformat(),
                }
                for p in positions
            ]

        result = await asyncio.to_thread(_get)
        logger.info(f"get_open_positions returning {len(result)} positions")
        return result

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
            tick = mt5.symbol_info_tick(symbol)
            return {
                "name": info.name,
                "spread": info.spread,
                "digits": info.digits,
                "point": info.point,
                "trade_contract_size": info.trade_contract_size,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
                "volume_step": info.volume_step,
                "trade_stops_level": info.trade_stops_level,
                "bid": tick.bid if tick else 0,
                "ask": tick.ask if tick else 0,
            }

        return await asyncio.to_thread(_get)

    async def get_history_deals(
        self,
        days: int = 30,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get closed trade history from MT5 grouped by position.

        Uses mt5.history_deals_get() to fetch deals, then groups
        entry (DEAL_ENTRY_IN) and exit (DEAL_ENTRY_OUT) deals by
        position_id to reconstruct complete trades.
        """
        self._ensure_initialized()
        from datetime import timedelta, timezone

        def _get():
            date_to = datetime.now(timezone.utc)
            date_from = date_to - timedelta(days=days)

            if symbol:
                deals = mt5.history_deals_get(date_from, date_to, symbol=symbol)
            else:
                deals = mt5.history_deals_get(date_from, date_to)

            if deals is None or len(deals) == 0:
                logger.info("No history deals found in MT5")
                return []

            logger.info(f"MT5 returned {len(deals)} history deals")

            # Group deals by position_id
            positions: dict[int, dict[str, Any]] = {}
            for deal in deals:
                pos_id = deal.position_id
                if pos_id == 0:
                    continue  # Skip balance/deposit operations

                if pos_id not in positions:
                    positions[pos_id] = {
                        "position_id": pos_id,
                        "symbol": deal.symbol,
                        "entries": [],
                        "exits": [],
                        "total_profit": 0.0,
                        "total_commission": 0.0,
                        "total_swap": 0.0,
                    }

                entry = {
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "time": datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat(),
                    "type": deal.type,
                    "entry": deal.entry,
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "commission": deal.commission,
                    "swap": deal.swap,
                    "comment": deal.comment,
                }

                # DEAL_ENTRY_IN = 0 (open), DEAL_ENTRY_OUT = 1 (close)
                if deal.entry == 0:
                    positions[pos_id]["entries"].append(entry)
                elif deal.entry == 1:
                    positions[pos_id]["exits"].append(entry)

                positions[pos_id]["total_profit"] += deal.profit
                positions[pos_id]["total_commission"] += deal.commission
                positions[pos_id]["total_swap"] += deal.swap

            # Build trade list from grouped positions
            trades = []
            for pos_id, pos_data in positions.items():
                if not pos_data["entries"]:
                    continue

                entry_deal = pos_data["entries"][0]
                exit_deal = pos_data["exits"][0] if pos_data["exits"] else None

                # Determine direction from deal type
                # ORDER_TYPE_BUY = 0, ORDER_TYPE_SELL = 1
                direction = "BUY" if entry_deal["type"] == 0 else "SELL"
                is_closed = exit_deal is not None

                trade = {
                    "ticket": entry_deal["order"],
                    "position_id": pos_id,
                    "symbol": pos_data["symbol"],
                    "direction": direction,
                    "volume": entry_deal["volume"],
                    "entry_price": entry_deal["price"],
                    "exit_price": exit_deal["price"] if exit_deal else None,
                    "stop_loss": None,
                    "take_profit": None,
                    "profit": round(pos_data["total_profit"], 2),
                    "commission": round(pos_data["total_commission"], 2),
                    "swap": round(pos_data["total_swap"], 2),
                    "opened_at": entry_deal["time"],
                    "closed_at": exit_deal["time"] if exit_deal else None,
                    "status": "closed" if is_closed else "open",
                    "comment": entry_deal["comment"],
                }
                trades.append(trade)

            # Sort by opened_at descending (newest first)
            trades.sort(key=lambda t: t["opened_at"], reverse=True)
            return trades

        result = await asyncio.to_thread(_get)
        logger.info(f"get_history_deals returning {len(result)} trades")
        return result


# Singleton instance
mt5_client = MT5Client()
