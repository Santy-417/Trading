from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade


class TradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Trade:
        trade = Trade(**kwargs)
        self.session.add(trade)
        await self.session.flush()
        return trade

    async def get_by_id(self, trade_id: UUID) -> Trade | None:
        result = await self.session.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticket(self, ticket: int) -> Trade | None:
        result = await self.session.execute(
            select(Trade).where(Trade.mt5_ticket == ticket)
        )
        return result.scalar_one_or_none()

    async def get_open_trades(self) -> list[Trade]:
        result = await self.session.execute(
            select(Trade).where(Trade.status == "open").order_by(Trade.opened_at.desc())
        )
        return list(result.scalars().all())

    async def get_trades(
        self,
        page: int = 1,
        page_size: int = 50,
        symbol: str | None = None,
        strategy: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Trade], int]:
        query = select(Trade)

        if symbol:
            query = query.where(Trade.symbol == symbol)
        if strategy:
            query = query.where(Trade.strategy == strategy)
        if status:
            query = query.where(Trade.status == status)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(Trade.opened_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)

        return list(result.scalars().all()), total

    async def close_trade(
        self,
        trade_id: UUID,
        exit_price: float,
        profit: float,
    ) -> Trade | None:
        trade = await self.get_by_id(trade_id)
        if trade is None:
            return None
        trade.exit_price = exit_price
        trade.profit = profit
        trade.status = "closed"
        trade.closed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return trade

    async def get_daily_profit(self) -> float:
        """Get total profit/loss for today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.session.execute(
            select(func.coalesce(func.sum(Trade.profit), 0)).where(
                Trade.closed_at >= today_start,
                Trade.status == "closed",
            )
        )
        return float(result.scalar() or 0)
