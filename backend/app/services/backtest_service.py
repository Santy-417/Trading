from datetime import datetime

import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import BacktestEngine
from app.backtesting.optimizer import ParameterOptimizer
from app.core.logging_config import get_logger
from app.models.backtest_result import BacktestResult
from app.schemas.backtest import BacktestEstimateRequest, BacktestRequest, OptimizeRequest
from app.strategies import STRATEGY_REGISTRY, get_strategy

logger = get_logger(__name__)


def sanitize_for_json(obj):
    """Recursively convert non-JSON-serializable types to JSON-serializable equivalents."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, (int, float, str, type(None))):
        return obj
    else:
        return str(obj)


def _parse_date(date_str: str, timezone: str) -> datetime:
    """Parse ISO date string and convert from user timezone to UTC."""
    tz = pytz.timezone(timezone)
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    return dt.astimezone(pytz.UTC).replace(tzinfo=None)


class BacktestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_backtest(self, request: BacktestRequest) -> dict:
        """Run a backtest and save results to DB."""
        loader = DataLoader()
        warmup_count = 0
        date_from_str = None
        date_to_str = None

        if request.date_from and request.date_to:
            # Date range mode with warm-up
            date_from = _parse_date(request.date_from, request.timezone)
            date_to = _parse_date(request.date_to, request.timezone)
            date_from_str = request.date_from
            date_to_str = request.date_to

            df, warmup_count = await loader.load_with_warmup(
                request.symbol, request.timeframe,
                date_from, date_to, request.warmup_bars,
            )
        else:
            # Legacy bar-count mode (backward compatible)
            bars = request.bars or 5000
            df = await loader.load_from_mt5(
                request.symbol, request.timeframe, count=bars,
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
            warmup_bars=warmup_count,
        )

        # Add date range metadata
        metrics["date_from"] = date_from_str
        metrics["date_to"] = date_to_str
        metrics["warmup_bars"] = warmup_count

        # Save to DB (sanitize JSONB fields to avoid serialization errors)
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
            params=sanitize_for_json(params),
            full_metrics=sanitize_for_json(metrics),
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

    @staticmethod
    def estimate_bars(request: BacktestEstimateRequest) -> dict:
        """Estimate number of bars for a date range."""
        tz = pytz.timezone(request.timezone)
        date_from = datetime.fromisoformat(request.date_from)
        date_to = datetime.fromisoformat(request.date_to)

        if date_from.tzinfo is None:
            date_from = tz.localize(date_from)
        if date_to.tzinfo is None:
            date_to = tz.localize(date_to)

        return DataLoader.estimate_bars(
            timeframe=request.timeframe,
            date_from=date_from,
            date_to=date_to,
            warmup_bars=request.warmup_bars,
        )

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
