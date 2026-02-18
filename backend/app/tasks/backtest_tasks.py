from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="run_backtest")
def run_backtest_task(
    self,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    bars: int = 5000,
    initial_balance: float = 10000.0,
    risk_per_trade: float = 1.0,
    lot_mode: str = "percent_risk",
    strategy_params: dict | None = None,
):
    """Run a backtest as a background Celery task."""
    import asyncio

    from app.backtesting.data_loader import DataLoader
    from app.backtesting.engine import BacktestEngine
    from app.strategies import get_strategy

    async def _run():
        loader = DataLoader()
        df = await loader.load_from_mt5(symbol, timeframe, count=bars)
        df = DataLoader.validate_data(df)

        params = strategy_params or {}
        strategy = get_strategy(strategy_name, **params)

        engine = BacktestEngine(
            initial_balance=initial_balance,
            risk_per_trade=risk_per_trade,
        )

        return engine.run(
            strategy=strategy,
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            lot_mode=lot_mode,
        )

    return asyncio.run(_run())


@celery_app.task(bind=True, name="run_optimization")
def run_optimization_task(
    self,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    param_grid: dict,
    bars: int = 5000,
    rank_by: str = "sharpe_ratio",
):
    """Run parameter optimization as a background task."""
    import asyncio

    from app.backtesting.data_loader import DataLoader
    from app.backtesting.engine import BacktestEngine
    from app.backtesting.optimizer import ParameterOptimizer
    from app.strategies import STRATEGY_REGISTRY

    async def _run():
        loader = DataLoader()
        df = await loader.load_from_mt5(symbol, timeframe, count=bars)
        df = DataLoader.validate_data(df)

        strategy_class = STRATEGY_REGISTRY.get(strategy_name)
        if strategy_class is None:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        engine = BacktestEngine()
        optimizer = ParameterOptimizer(engine)

        return optimizer.grid_search(
            strategy_class=strategy_class,
            param_grid=param_grid,
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            rank_by=rank_by,
        )

    return asyncio.run(_run())
