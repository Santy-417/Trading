from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="run_backtest")
def run_backtest_task(
    self,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    bars: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    timezone: str = "America/Bogota",
    warmup_bars: int = 200,
    initial_balance: float = 10000.0,
    risk_per_trade: float = 1.0,
    lot_mode: str = "percent_risk",
    strategy_params: dict | None = None,
):
    """Run a backtest as a background Celery task."""
    import asyncio
    from datetime import datetime

    import pytz

    from app.backtesting.data_loader import DataLoader
    from app.backtesting.engine import BacktestEngine
    from app.strategies import get_strategy

    async def _run():
        # Update state to LOADING DATA
        self.update_state(
            state="PROGRESS",
            meta={"stage": "Loading data", "percent": 0},
        )

        loader = DataLoader()
        warmup_count = 0

        if date_from and date_to:
            # Date range mode with warm-up
            tz = pytz.timezone(timezone)
            dt_from = datetime.fromisoformat(date_from)
            dt_to = datetime.fromisoformat(date_to)
            if dt_from.tzinfo is None:
                dt_from = tz.localize(dt_from)
            if dt_to.tzinfo is None:
                dt_to = tz.localize(dt_to)
            dt_from = dt_from.astimezone(pytz.UTC).replace(tzinfo=None)
            dt_to = dt_to.astimezone(pytz.UTC).replace(tzinfo=None)

            df, warmup_count = await loader.load_with_warmup(
                symbol, timeframe, dt_from, dt_to, warmup_bars,
            )
        else:
            # Legacy bar-count mode
            df = await loader.load_from_mt5(symbol, timeframe, count=bars or 5000)

        df = DataLoader.validate_data(df)

        # Update state to RUNNING BACKTEST
        self.update_state(
            state="PROGRESS",
            meta={"stage": "Running backtest", "percent": 5},
        )

        params = strategy_params or {}
        strategy = get_strategy(strategy_name, **params)

        engine = BacktestEngine(
            initial_balance=initial_balance,
            risk_per_trade=risk_per_trade,
        )

        # Define progress callback that updates Celery state
        def progress_callback(current: int, total: int, percent: int):
            adjusted_percent = 5 + int(percent * 0.9)
            self.update_state(
                state="PROGRESS",
                meta={
                    "stage": "Running backtest",
                    "percent": adjusted_percent,
                    "current_bar": current,
                    "total_bars": total,
                },
            )

        result = engine.run(
            strategy=strategy,
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            lot_mode=lot_mode,
            warmup_bars=warmup_count,
            progress_callback=progress_callback,
        )

        # Add date range metadata
        result["date_from"] = date_from
        result["date_to"] = date_to
        result["warmup_bars"] = warmup_count

        # Update state to FINALIZING
        self.update_state(
            state="PROGRESS",
            meta={"stage": "Finalizing results", "percent": 95},
        )

        return result

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
