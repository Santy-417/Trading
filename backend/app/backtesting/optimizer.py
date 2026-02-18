import itertools
from typing import Any

import pandas as pd

from app.backtesting.engine import BacktestEngine
from app.backtesting.simulator import SimulationConfig
from app.core.logging_config import get_logger
from app.strategies.base import BaseStrategy

logger = get_logger(__name__)


class ParameterOptimizer:
    """
    Optimize strategy parameters via grid search.
    Tests all combinations and ranks by a target metric.
    """

    def __init__(self, engine: BacktestEngine):
        self.engine = engine

    def grid_search(
        self,
        strategy_class: type[BaseStrategy],
        param_grid: dict[str, list[Any]],
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        sim_config: SimulationConfig | None = None,
        rank_by: str = "sharpe_ratio",
    ) -> list[dict]:
        """
        Run backtests for all parameter combinations.

        Args:
            strategy_class: Strategy class to instantiate
            param_grid: Dict of parameter names to lists of values
                        e.g. {"swing_lookback": [30, 50, 70], "tp_extension": [1.272, 1.618]}
            df: Historical OHLCV data
            symbol: Trading symbol
            timeframe: Timeframe string
            sim_config: Simulation configuration
            rank_by: Metric to sort results by (descending)

        Returns:
            List of dicts with params and metrics, sorted by rank_by.
        """
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        logger.info(
            "Starting grid search: %d combinations for %s",
            len(combinations),
            strategy_class.__name__,
        )

        results = []

        for combo in combinations:
            params = dict(zip(param_names, combo))

            try:
                strategy = strategy_class(**params)
                metrics = self.engine.run(
                    strategy=strategy,
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    sim_config=sim_config,
                )

                results.append({
                    "params": params,
                    "metrics": metrics,
                })
            except Exception as e:
                logger.warning(
                    "Grid search failed for params %s: %s", params, str(e)
                )

        # Sort by target metric (descending)
        results.sort(
            key=lambda r: r["metrics"].get(rank_by, 0),
            reverse=True,
        )

        logger.info(
            "Grid search complete: %d/%d successful runs",
            len(results),
            len(combinations),
        )

        return results
