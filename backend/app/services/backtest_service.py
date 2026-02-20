from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import BacktestEngine
from app.backtesting.optimizer import ParameterOptimizer
from app.core.logging_config import get_logger
from app.models.backtest_result import BacktestResult
from app.schemas.backtest import BacktestRequest, OptimizeRequest
from app.strategies import STRATEGY_REGISTRY, get_strategy

logger = get_logger(__name__)


class BacktestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_backtest(self, request: BacktestRequest) -> dict:
        """Run a backtest and save results to DB."""
        loader = DataLoader()
        df = await loader.load_from_mt5(
            request.symbol, request.timeframe, count=request.bars
        )
        df = DataLoader.validate_data(df)

        params = request.strategy_params or {}
        strategy = get_strategy(request.strategy, **params)

        engine = BacktestEngine(
            initial_balance=request.initial_balance,
            risk_per_trade=request.risk_per_trade,
        )

        metrics = engine.run(
            strategy=strategy,
            df=df,
            symbol=request.symbol,
            timeframe=request.timeframe,
            lot_mode=request.lot_mode,
        )

        # Save to DB
        result = BacktestResult(
            strategy=request.strategy,
            symbol=request.symbol,
            timeframe=request.timeframe,
            total_trades=metrics["total_trades"],
            win_rate=metrics["win_rate"],
            net_profit=metrics["net_profit"],
            profit_factor=metrics["profit_factor"],
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown_percent=metrics["max_drawdown_percent"],
            initial_balance=metrics["initial_balance"],
            final_balance=max(metrics["final_balance"], 0.0),
            params=params,
            full_metrics=metrics,
        )
        self.session.add(result)
        await self.session.flush()

        return metrics

    async def run_optimization(self, request: OptimizeRequest) -> list[dict]:
        """Run parameter optimization."""
        loader = DataLoader()
        df = await loader.load_from_mt5(
            request.symbol, request.timeframe, count=request.bars
        )
        df = DataLoader.validate_data(df)

        strategy_class = STRATEGY_REGISTRY.get(request.strategy)
        if strategy_class is None:
            raise ValueError(f"Unknown strategy: {request.strategy}")

        engine = BacktestEngine()
        optimizer = ParameterOptimizer(engine)

        results = optimizer.grid_search(
            strategy_class=strategy_class,
            param_grid=request.param_grid,
            df=df,
            symbol=request.symbol,
            timeframe=request.timeframe,
            rank_by=request.rank_by,
        )

        return results

    async def get_results(self, limit: int = 50) -> list[dict]:
        """Get recent backtest results from DB."""
        from sqlalchemy import select

        query = (
            select(BacktestResult)
            .order_by(BacktestResult.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        rows = result.scalars().all()

        return [
            {
                "id": str(r.id),
                "strategy": r.strategy,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "total_trades": r.total_trades,
                "win_rate": float(r.win_rate),
                "net_profit": float(r.net_profit),
                "sharpe_ratio": float(r.sharpe_ratio),
                "max_drawdown_percent": float(r.max_drawdown_percent),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
