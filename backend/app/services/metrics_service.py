from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade


class MetricsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_performance(self) -> dict:
        """Get overall trading performance metrics."""
        # Total trades
        total_q = await self.session.execute(
            select(func.count()).select_from(Trade).where(Trade.status == "closed")
        )
        total_trades = total_q.scalar() or 0

        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "net_profit": 0.0,
                "profit_factor": 0.0,
                "average_profit": 0.0,
                "average_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
            }

        # Winning trades
        win_q = await self.session.execute(
            select(func.count()).select_from(Trade).where(
                Trade.status == "closed", Trade.profit > 0
            )
        )
        winning = win_q.scalar() or 0

        # Total profit (wins only)
        profit_q = await self.session.execute(
            select(func.coalesce(func.sum(Trade.profit), 0)).where(
                Trade.status == "closed", Trade.profit > 0
            )
        )
        total_profit = float(profit_q.scalar() or 0)

        # Total loss
        loss_q = await self.session.execute(
            select(func.coalesce(func.sum(Trade.profit), 0)).where(
                Trade.status == "closed", Trade.profit < 0
            )
        )
        total_loss = float(loss_q.scalar() or 0)

        # Largest win/loss
        max_win_q = await self.session.execute(
            select(func.coalesce(func.max(Trade.profit), 0)).where(
                Trade.status == "closed", Trade.profit > 0
            )
        )
        largest_win = float(max_win_q.scalar() or 0)

        min_loss_q = await self.session.execute(
            select(func.coalesce(func.min(Trade.profit), 0)).where(
                Trade.status == "closed", Trade.profit < 0
            )
        )
        largest_loss = float(min_loss_q.scalar() or 0)

        losing = total_trades - winning
        net_profit = total_profit + total_loss
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (total_profit / abs(total_loss)) if total_loss != 0 else 0
        avg_profit = (total_profit / winning) if winning > 0 else 0
        avg_loss = (total_loss / losing) if losing > 0 else 0

        return {
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": round(win_rate, 2),
            "total_profit": round(total_profit, 2),
            "total_loss": round(total_loss, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": round(profit_factor, 2),
            "average_profit": round(avg_profit, 2),
            "average_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
        }

    async def get_equity_curve(self) -> list[dict]:
        """Get equity curve data points from closed trades."""
        result = await self.session.execute(
            select(Trade.closed_at, Trade.profit)
            .where(Trade.status == "closed")
            .order_by(Trade.closed_at.asc())
        )
        rows = result.all()

        cumulative = 0.0
        curve = []
        for closed_at, profit in rows:
            cumulative += float(profit or 0)
            curve.append({
                "timestamp": closed_at.isoformat() if closed_at else None,
                "cumulative_profit": round(cumulative, 2),
            })

        return curve
