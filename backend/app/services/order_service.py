from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.integrations.metatrader.mt5_client import OrderType, mt5_client
from app.repositories.audit_repository import AuditRepository
from app.repositories.trade_repository import TradeRepository
from app.risk.risk_manager import risk_manager
from app.schemas.order import LimitOrderRequest, MarketOrderRequest

logger = get_logger(__name__)


class OrderService:
    def __init__(self, session: AsyncSession):
        self.trade_repo = TradeRepository(session)
        self.audit_repo = AuditRepository(session)

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
            risk_manager.record_trade()
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
            # Update trade record
            trade = await self.trade_repo.get_by_ticket(ticket)
            if trade:
                await self.trade_repo.close_trade(
                    trade_id=trade.id,
                    exit_price=result.price or 0,
                    profit=0,  # Will be updated from MT5 history
                )

            await self.audit_repo.create(
                action="position_closed",
                entity_type="trade",
                entity_id=str(ticket),
                details={"price": result.price},
                ip_address=ip,
            )

        return {
            "success": result.success,
            "ticket": result.ticket,
            "price": result.price,
            "comment": result.comment,
            "retcode": result.retcode,
        }

    async def get_open_positions(self) -> list[dict]:
        return await mt5_client.get_open_positions()

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
        return {
            "trades": trades,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
