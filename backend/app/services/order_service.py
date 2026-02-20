from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.integrations.metatrader.mt5_client import OrderType, mt5_client
from app.repositories.audit_repository import AuditRepository
from app.repositories.trade_repository import TradeRepository
from app.risk.risk_manager import risk_manager
from app.schemas.order import LimitOrderRequest, MarketOrderRequest
from app.schemas.trade import TradeResponse

logger = get_logger(__name__)


class OrderService:
    def __init__(self, session: AsyncSession | None):
        self.trade_repo = TradeRepository(session) if session else None
        self.audit_repo = AuditRepository(session) if session else None

    async def market_order(
        self, request: MarketOrderRequest, ip: str | None = None
    ) -> dict:
        # Risk check
        account = await mt5_client.get_account_info()
        risk_result = risk_manager.check_trade_allowed(
            balance=account["balance"],
            equity=account["equity"],
        )

        if not risk_result.allowed:
            logger.warning(f"Trade blocked by risk manager: {risk_result.reason}")
            return {"success": False, "comment": risk_result.reason}

        direction = OrderType.BUY if request.direction.upper() == "BUY" else OrderType.SELL

        # Calculate volume if not provided
        volume = request.volume
        if volume is None:
            symbol_info = await mt5_client.get_symbol_info(request.symbol)
            volume = symbol_info.get("volume_min", 0.01)

        result = await mt5_client.send_market_order(
            symbol=request.symbol,
            direction=direction,
            volume=volume,
            sl=request.stop_loss,
            tp=request.take_profit,
            comment=request.comment or "manual",
        )

        if result.success:
            logger.info(f"Market order successful: {request.symbol} {request.direction} {volume} @ {result.price}, ticket={result.ticket}")
            risk_manager.record_trade()

            # Save to database only if session is available
            if self.trade_repo is not None:
                try:
                    await self.trade_repo.create(
                        symbol=request.symbol,
                        direction=request.direction.upper(),
                        lot_size=volume,
                        entry_price=result.price or 0,
                        stop_loss=request.stop_loss,
                        take_profit=request.take_profit,
                        strategy="manual",
                        timeframe="N/A",
                        mt5_ticket=result.ticket,
                        status="open",
                    )
                    logger.info(f"Trade saved to DB: ticket={result.ticket}")
                except Exception as e:
                    logger.error(f"Failed to save trade to DB: {e}")

            if self.audit_repo is not None:
                try:
                    await self.audit_repo.create(
                        action="order_executed",
                        entity_type="trade",
                        entity_id=str(result.ticket),
                        details={
                            "symbol": request.symbol,
                            "direction": request.direction,
                            "volume": volume,
                            "price": result.price,
                        },
                        ip_address=ip,
                    )
                except Exception as e:
                    logger.error(f"Failed to save audit log: {e}")
        else:
            logger.warning(f"Market order failed: {result.comment} (retcode={result.retcode})")

        return {
            "success": result.success,
            "ticket": result.ticket,
            "price": result.price,
            "volume": result.volume,
            "comment": result.comment,
            "retcode": result.retcode,
        }

    async def limit_order(
        self, request: LimitOrderRequest, ip: str | None = None
    ) -> dict:
        direction = OrderType(request.direction.upper())

        result = await mt5_client.send_limit_order(
            symbol=request.symbol,
            direction=direction,
            volume=request.volume,
            price=request.price,
            sl=request.stop_loss,
            tp=request.take_profit,
            comment=request.comment or "manual_limit",
        )

        if result.success:
            await self.audit_repo.create(
                action="limit_order_placed",
                entity_type="trade",
                entity_id=str(result.ticket),
                details={
                    "symbol": request.symbol,
                    "direction": request.direction,
                    "volume": request.volume,
                    "price": request.price,
                },
                ip_address=ip,
            )

        return {
            "success": result.success,
            "ticket": result.ticket,
            "price": result.price,
            "volume": result.volume,
            "comment": result.comment,
            "retcode": result.retcode,
        }

    async def close_position(self, ticket: int, ip: str | None = None) -> dict:
        result = await mt5_client.close_position(ticket)

        if result.success:
            logger.info(f"Position closed successfully: ticket={ticket}, price={result.price}")

            # Update trade record only if session is available
            if self.trade_repo is not None:
                try:
                    trade = await self.trade_repo.get_by_ticket(ticket)
                    if trade:
                        await self.trade_repo.close_trade(
                            trade_id=trade.id,
                            exit_price=result.price or 0,
                            profit=0,  # Will be updated from MT5 history
                        )
                        logger.info(f"Trade record updated in DB: ticket={ticket}")
                    else:
                        logger.warning(f"Trade not found in DB: ticket={ticket}")
                except Exception as e:
                    logger.error(f"Failed to update trade in DB: {e}")

            if self.audit_repo is not None:
                try:
                    await self.audit_repo.create(
                        action="position_closed",
                        entity_type="trade",
                        entity_id=str(ticket),
                        details={"price": result.price},
                        ip_address=ip,
                    )
                except Exception as e:
                    logger.error(f"Failed to save audit log: {e}")
        else:
            logger.warning(f"Failed to close position: ticket={ticket}, {result.comment}")

        return {
            "success": result.success,
            "ticket": result.ticket,
            "price": result.price,
            "comment": result.comment,
            "retcode": result.retcode,
        }

    async def modify_position(
        self,
        ticket: int,
        sl: float | None = None,
        tp: float | None = None,
        volume: float | None = None,
        ip: str | None = None,
    ) -> dict:
        if volume is not None:
            result = await mt5_client.partial_close(ticket=ticket, volume=volume)
            action = "partial_close"
        else:
            result = await mt5_client.modify_position(ticket=ticket, sl=sl, tp=tp)
            action = "modify_sltp"

        if result.success:
            logger.info(f"Position {action}: ticket={ticket}, sl={sl}, tp={tp}, volume={volume}")
            if self.audit_repo is not None:
                try:
                    await self.audit_repo.create(
                        action=action,
                        entity_type="trade",
                        entity_id=str(ticket),
                        details={"sl": sl, "tp": tp, "volume": volume},
                        ip_address=ip,
                    )
                except Exception as e:
                    logger.error(f"Failed to save audit log: {e}")
        else:
            logger.warning(f"Position {action} failed: ticket={ticket}, {result.comment}")

        return {
            "success": result.success,
            "ticket": result.ticket,
            "comment": result.comment,
            "retcode": result.retcode,
        }

    async def get_pending_orders(self) -> list[dict]:
        try:
            orders = await mt5_client.get_pending_orders()
            logger.info(f"Fetched {len(orders)} pending orders from MT5")
            return orders
        except Exception as e:
            logger.error(f"Failed to fetch pending orders: {e}")
            raise

    async def cancel_order(self, ticket: int, ip: str | None = None) -> dict:
        result = await mt5_client.cancel_order(ticket)

        if result.success:
            logger.info(f"Pending order cancelled: ticket={ticket}")
            if self.audit_repo is not None:
                try:
                    await self.audit_repo.create(
                        action="order_cancelled",
                        entity_type="trade",
                        entity_id=str(ticket),
                        details={"ticket": ticket},
                        ip_address=ip,
                    )
                except Exception as e:
                    logger.error(f"Failed to save audit log: {e}")
        else:
            logger.warning(f"Failed to cancel order: ticket={ticket}, {result.comment}")

        return {
            "success": result.success,
            "ticket": result.ticket,
            "comment": result.comment,
            "retcode": result.retcode,
        }

    async def get_open_positions(self) -> list[dict]:
        try:
            positions = await mt5_client.get_open_positions()
            logger.info(f"Fetched {len(positions)} open positions from MT5")
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch open positions: {e}")
            raise

    async def get_trade_history(
        self,
        page: int = 1,
        page_size: int = 50,
        symbol: str | None = None,
        strategy: str | None = None,
    ) -> dict:
        trades, total = await self.trade_repo.get_trades(
            page=page,
            page_size=page_size,
            symbol=symbol,
            strategy=strategy,
            status="closed",
        )

        # Convert ORM objects to Pydantic models for proper JSON serialization
        trade_responses = [TradeResponse.model_validate(trade) for trade in trades]

        return {
            "trades": trade_responses,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
