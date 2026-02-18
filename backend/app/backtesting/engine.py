import pandas as pd

from app.backtesting.metrics import calculate_metrics
from app.backtesting.simulator import (
    SYMBOL_CONFIGS,
    SimulationConfig,
    TradeSimulator,
)
from app.core.logging_config import get_logger
from app.risk.lot_calculator import LotCalculator
from app.strategies.base import BaseStrategy, SignalDirection

logger = get_logger(__name__)


class BacktestEngine:
    """
    Professional backtesting engine.

    Walks through historical data bar-by-bar, generates signals via strategy,
    simulates trades with spread/commission/slippage, and calculates metrics.
    """

    def __init__(self, initial_balance: float = 10000.0, risk_per_trade: float = 1.0):
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        sim_config: SimulationConfig | None = None,
        lot_mode: str = "percent_risk",
        fixed_lot: float = 0.01,
    ) -> dict:
        """
        Run a full backtest.

        Args:
            strategy: Strategy instance to test
            df: Historical OHLCV DataFrame (must have open, high, low, close)
            symbol: Trading symbol
            timeframe: Timeframe string
            sim_config: Simulation config (auto-detected from symbol if None)
            lot_mode: "fixed" or "percent_risk"
            fixed_lot: Lot size for fixed mode

        Returns:
            Dict with all performance metrics.
        """
        config = sim_config or SYMBOL_CONFIGS.get(symbol, SimulationConfig())
        config.initial_balance = self.initial_balance
        simulator = TradeSimulator(config)

        trades = []
        balance = self.initial_balance
        min_bars = 60  # Minimum bars before generating signals

        logger.info(
            "Backtest started: %s on %s %s, %d bars",
            strategy.name, symbol, timeframe, len(df),
        )

        high_prices = df["high"].values
        low_prices = df["low"].values

        for i in range(min_bars, len(df) - 1):
            # Feed strategy only data up to current bar (no look-ahead)
            window = df.iloc[:i + 1]
            signal = strategy.generate_signal(window, symbol, timeframe)

            if signal is None:
                continue

            if signal.direction == SignalDirection.NEUTRAL:
                continue

            # Calculate lot size
            if lot_mode == "fixed":
                lot = fixed_lot
            else:
                sl_pips = signal.sl_pips / config.point
                if sl_pips <= 0:
                    continue
                lot = LotCalculator.percent_risk(
                    balance=balance,
                    risk_percent=self.risk_per_trade,
                    sl_pips=sl_pips,
                    pip_value=config.pip_value,
                    volume_min=0.01,
                    volume_max=10.0,
                )

            # Simulate trade
            result = simulator.simulate_trade(
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                direction=signal.direction.value,
                lot_size=lot,
                high_prices=high_prices,
                low_prices=low_prices,
                bar_index=i,
            )

            if result is None:
                continue

            balance += result.profit
            trades.append({
                "entry_price": result.entry_price,
                "exit_price": result.exit_price,
                "direction": result.direction,
                "lot_size": result.lot_size,
                "profit": result.profit,
                "commission": result.commission,
                "gross_profit": result.gross_profit,
                "bar_index": result.bar_index,
                "stop_loss": result.stop_loss,
                "take_profit": result.take_profit,
            })

            # Stop if balance is depleted
            if balance <= 0:
                logger.warning("Backtest stopped: balance depleted")
                break

        trades_df = pd.DataFrame(trades)
        metrics = calculate_metrics(trades_df, self.initial_balance)
        metrics["strategy"] = strategy.name
        metrics["symbol"] = symbol
        metrics["timeframe"] = timeframe
        metrics["total_bars"] = len(df)

        logger.info(
            "Backtest complete: %s | %d trades | Net: $%.2f | Win: %.1f%% | Sharpe: %.2f",
            strategy.name,
            metrics["total_trades"],
            metrics["net_profit"],
            metrics["win_rate"],
            metrics["sharpe_ratio"],
        )

        return metrics
