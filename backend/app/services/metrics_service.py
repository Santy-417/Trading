from datetime import date, datetime, timezone

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
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "today_pnl": 0.0,
                "open_positions": 0,
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

        # Max drawdown from equity curve
        max_drawdown = await self._calculate_max_drawdown()

        # Today's P&L
        today_pnl = await self._calculate_today_pnl()

        # Open positions count
        open_q = await self.session.execute(
            select(func.count()).select_from(Trade).where(Trade.status == "open")
        )
        open_positions = open_q.scalar() or 0

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
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": 0.0,
            "today_pnl": round(today_pnl, 2),
            "open_positions": open_positions,
        }

    async def _calculate_max_drawdown(self) -> float:
        """Calculate max drawdown percentage from closed trades."""
        result = await self.session.execute(
            select(Trade.profit)
            .where(Trade.status == "closed")
            .order_by(Trade.closed_at.asc())
        )
        profits = [float(r[0] or 0) for r in result.all()]
        if not profits:
            return 0.0

        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in profits:
            cumulative += p
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return max_dd

    async def _calculate_today_pnl(self) -> float:
        """Calculate today's profit/loss."""
        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        result = await self.session.execute(
            select(func.coalesce(func.sum(Trade.profit), 0)).where(
                Trade.status == "closed",
                Trade.closed_at >= today_start,
            )
        )
        return float(result.scalar() or 0)

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
