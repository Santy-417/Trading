import pandas as pd

from app.backtesting.metrics import (
    calculate_buy_sell_distribution,
    calculate_metrics,
    calculate_session_analysis,
)
from app.backtesting.simulator import (
    SYMBOL_CONFIGS,
    SimulationConfig,
    TradeSimulator,
)
from app.core.logging_config import get_logger
from app.risk.lot_calculator import LotCalculator
from app.strategies.base import BaseStrategy, SignalDirection

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Trade filter configuration (FTMO-ready, configurable per symbol)
# ---------------------------------------------------------------------------

MAX_SL_PIPS: dict[str, float] = {
    "XAUUSD": 5000.0,   # 1 pip = $0.01; 5000 pips = $50 — typical H1 swing SL
    "EURUSD": 100.0,    # 1 pip = $0.0001; 100 pips = 0.01 — reasonable forex SL
}

MIN_SL_PIPS: dict[str, float] = {
    "XAUUSD": 100.0,    # 100 pips = $1 — prevents noise-level SLs
    "EURUSD": 10.0,     # 10 pips = 0.001 — prevents noise-level SLs
}

MIN_RR: float = 1.0
MAX_DRAWDOWN_PERCENT: float = 95.0
SKIP_IF_LOT_DISTORTED: bool = True


class BacktestEngine:
    """
    Professional backtesting engine (FTMO-ready).

    Walks through historical data bar-by-bar, generates signals via strategy,
    simulates trades with spread/commission/slippage, and calculates metrics.

    Safeguards:
    - Margin call: stops if balance reaches 0.
    - Drawdown guard: stops if equity drawdown exceeds MAX_DRAWDOWN_PERCENT.
    - SL size filter: rejects trades with SL > MAX_SL_PIPS or < MIN_SL_PIPS.
    - Risk-reward filter: rejects trades with RR < MIN_RR.
    - Lot distortion check: rejects trades where lot rounding doubles the risk.
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
        warmup_bars: int = 0,
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
            warmup_bars: Number of bars to skip for trade generation (warmup period)

        Returns:
            Dict with all performance metrics plus account_blown and debug_stats.
        """
        config = sim_config or SYMBOL_CONFIGS.get(symbol, SimulationConfig())
        config.initial_balance = self.initial_balance
        simulator = TradeSimulator(config)

        trades: list[dict] = []
        balance = self.initial_balance
        peak_balance = self.initial_balance
        account_blown = False
        min_bars = max(60, warmup_bars)  # Respect warmup period for date-range mode

        # Time-based close: strategy may define close_time_utc = (hour, minute)
        close_time_utc = getattr(strategy, "close_time_utc", None)

        # Per-symbol SL limits (fall back to conservative defaults)
        max_sl = MAX_SL_PIPS.get(symbol, 200.0)
        min_sl = MIN_SL_PIPS.get(symbol, 10.0)

        debug_stats: dict[str, int] = {
            "skipped_sl_too_large": 0,
            "skipped_sl_too_small": 0,
            "skipped_rr_too_low": 0,
            "skipped_lot_distortion": 0,
            "executed_trades": 0,
        }

        logger.info(
            "Backtest started: %s on %s %s, %d bars",
            strategy.name, symbol, timeframe, len(df),
        )

        high_prices = df["high"].values
        low_prices = df["low"].values
        close_prices = df["close"].values

        # Pre-compute bar hours for time-based close
        bar_hours: list[tuple[int, int]] | None = None
        if close_time_utc and hasattr(df.index, "hour"):
            bar_hours = [(int(t.hour), int(t.minute)) for t in df.index]

        total_bars = len(df) - 1
        for i in range(min_bars, len(df) - 1):
            # Progress indicator (every 500 bars)
            if i % 500 == 0:
                progress_pct = (i / total_bars) * 100
                print(f"  Progress: {i}/{total_bars} bars ({progress_pct:.1f}%) - Balance: ${balance:.2f}")

            # ------------------------------------------------------------------
            # Pre-trade guards: margin call and drawdown
            # ------------------------------------------------------------------
            if balance <= 0:
                logger.warning("Account blown: balance depleted. Stopping backtest.")
                account_blown = True
                break

            peak_balance = max(peak_balance, balance)
            drawdown_pct = (peak_balance - balance) / peak_balance * 100
            if drawdown_pct >= MAX_DRAWDOWN_PERCENT:
                logger.warning("Max drawdown exceeded. Stopping backtest.")
                account_blown = True
                break

            # Feed strategy only data up to current bar (no look-ahead)
            window = df.iloc[:i + 1]
            signal = strategy.generate_signal(window, symbol, timeframe)

            if signal is None or signal.direction == SignalDirection.NEUTRAL:
                continue

            # ------------------------------------------------------------------
            # SL / RR validation (before lot calculation)
            # ------------------------------------------------------------------
            sl_pips = abs(signal.entry_price - signal.stop_loss) / config.point
            reward_pips = abs(signal.take_profit - signal.entry_price) / config.point

            if sl_pips <= 0:
                continue

            if sl_pips > max_sl:
                logger.debug("Trade skipped: SL too large (sl_pips=%.0f)", sl_pips)
                debug_stats["skipped_sl_too_large"] += 1
                continue

            if sl_pips < min_sl:
                logger.debug("Trade skipped: SL too small (sl_pips=%.0f)", sl_pips)
                debug_stats["skipped_sl_too_small"] += 1
                continue

            rr = reward_pips / sl_pips
            if rr < MIN_RR - 1e-9:  # small epsilon for floating-point tolerance
                logger.debug("Trade skipped: RR too low (rr=%.2f)", rr)
                debug_stats["skipped_rr_too_low"] += 1
                continue

            # ------------------------------------------------------------------
            # Lot calculation (with ML-based risk override if available)
            # ------------------------------------------------------------------
            effective_risk = self.risk_per_trade
            if signal.metadata and "risk_percent" in signal.metadata:
                effective_risk = signal.metadata["risk_percent"]

            if lot_mode == "fixed":
                lot = fixed_lot
            else:
                lot = LotCalculator.percent_risk(
                    balance=balance,
                    risk_percent=effective_risk,
                    sl_pips=sl_pips,
                    pip_value=config.pip_value,
                    volume_min=0.01,
                    volume_max=10.0,
                )

            # ------------------------------------------------------------------
            # Lot distortion check
            # ------------------------------------------------------------------
            if SKIP_IF_LOT_DISTORTED and lot_mode == "percent_risk":
                actual_risk = lot * sl_pips * config.pip_value
                allowed_risk = balance * (self.risk_per_trade / 100.0)
                if allowed_risk > 0 and actual_risk > allowed_risk * 2.0:
                    logger.warning(
                        "Trade skipped: lot size distortion detected "
                        "(actual_risk=%.2f, allowed=%.2f)",
                        actual_risk, allowed_risk,
                    )
                    debug_stats["skipped_lot_distortion"] += 1
                    continue

            # ------------------------------------------------------------------
            # Simulate trade (with time-based close support)
            # ------------------------------------------------------------------
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

            # Time-based close: if trade didn't hit SL/TP, check if session ended
            if result is None and close_time_utc and bar_hours:
                close_h, close_m = close_time_utc
                close_mins = close_h * 60 + close_m
                # Search forward for the first bar past close time
                for j in range(i + 1, len(df)):
                    bh, bm = bar_hours[j]
                    bar_mins = bh * 60 + bm
                    if bar_mins >= close_mins:
                        # Close at this bar's close price
                        exit_price = float(close_prices[j])
                        entry_p = signal.entry_price
                        pip_diff = (exit_price - entry_p) / config.point
                        if signal.direction.value == "SELL":
                            pip_diff = -pip_diff
                        gross = pip_diff * config.pip_value * lot
                        comm = config.commission_per_lot * lot
                        from app.backtesting.simulator import SimulatedTrade
                        result = SimulatedTrade(
                            entry_price=entry_p,
                            exit_price=exit_price,
                            direction=signal.direction.value,
                            lot_size=lot,
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit,
                            profit=round(gross - comm, 2),
                            commission=round(comm, 2),
                            gross_profit=round(gross, 2),
                            bar_index=i,
                            exit_reason="TIME_CLOSE",
                        )
                        break

            if result is None:
                continue

            balance += result.profit
            debug_stats["executed_trades"] += 1

            # Build entry timestamp from DataFrame index
            entry_time = None
            if hasattr(df.index, "__getitem__"):
                entry_time = str(df.index[i])

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
                "exit_reason": result.exit_reason,
                "entry_time": entry_time,
                "signal_metadata": signal.metadata if signal.metadata else {},
                "risk_reward": round(reward_pips / sl_pips, 2) if sl_pips > 0 else 0,
                "effective_risk": effective_risk,
            })

        logger.info("Backtest filters summary: %s", debug_stats)

        trades_df = pd.DataFrame(trades)
        metrics = calculate_metrics(trades_df, self.initial_balance)
        metrics["strategy"] = strategy.name
        metrics["symbol"] = symbol
        metrics["timeframe"] = timeframe
        metrics["total_bars"] = len(df)
        metrics["account_blown"] = account_blown
        metrics["debug_stats"] = debug_stats
        metrics["trades"] = trades
        metrics["session_analysis"] = calculate_session_analysis(trades)
        metrics["buy_sell_distribution"] = calculate_buy_sell_distribution(trades)

        logger.info(
            "Backtest complete: %s | %d trades | Net: $%.2f | Win: %.1f%% | Sharpe: %.2f",
            strategy.name,
            metrics["total_trades"],
            metrics["net_profit"],
            metrics["win_rate"],
            metrics["sharpe_ratio"],
        )

        return metrics
