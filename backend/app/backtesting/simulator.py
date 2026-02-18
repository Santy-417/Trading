from dataclasses import dataclass, field

import numpy as np


@dataclass
class SimulationConfig:
    """Configuration for trade simulation realism."""
    spread_pips: float = 1.5
    commission_per_lot: float = 7.0  # USD per lot round-trip
    slippage_pips: float = 0.5
    initial_balance: float = 10000.0
    pip_value: float = 10.0  # USD per pip per standard lot
    point: float = 0.0001  # Smallest price increment


@dataclass
class SimulatedTrade:
    """Result of a simulated trade."""
    entry_price: float
    exit_price: float
    direction: str
    lot_size: float
    stop_loss: float
    take_profit: float
    profit: float = 0.0
    commission: float = 0.0
    spread_cost: float = 0.0
    slippage_cost: float = 0.0
    gross_profit: float = 0.0
    bar_index: int = 0


class TradeSimulator:
    """
    Simulates trade execution with realistic costs.
    Accounts for spread, commission, and slippage.
    """

    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()

    def simulate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        lot_size: float,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        bar_index: int,
    ) -> SimulatedTrade | None:
        """
        Simulate a single trade through subsequent bars.

        Walks through price bars after entry to determine if SL or TP is hit first.
        """
        cfg = self.config

        # Apply spread to entry
        spread_adjustment = cfg.spread_pips * cfg.point
        if direction == "BUY":
            actual_entry = entry_price + spread_adjustment  # Buy at ask
        else:
            actual_entry = entry_price - spread_adjustment  # Sell at bid

        # Apply random slippage
        slippage = np.random.uniform(0, cfg.slippage_pips) * cfg.point
        if direction == "BUY":
            actual_entry += slippage
        else:
            actual_entry -= slippage

        # Walk through subsequent bars
        exit_price = None
        for i in range(bar_index + 1, len(high_prices)):
            bar_high = high_prices[i]
            bar_low = low_prices[i]

            if direction == "BUY":
                # Check SL first (worst case)
                if bar_low <= stop_loss:
                    exit_price = stop_loss
                    break
                # Check TP
                if bar_high >= take_profit:
                    exit_price = take_profit
                    break
            else:  # SELL
                if bar_high >= stop_loss:
                    exit_price = stop_loss
                    break
                if bar_low <= take_profit:
                    exit_price = take_profit
                    break

        if exit_price is None:
            return None  # Trade never closed within data

        # Calculate profit
        if direction == "BUY":
            price_diff = exit_price - actual_entry
        else:
            price_diff = actual_entry - exit_price

        pips = price_diff / cfg.point
        gross_profit = pips * cfg.pip_value * lot_size
        commission = cfg.commission_per_lot * lot_size
        spread_cost = cfg.spread_pips * cfg.pip_value * lot_size
        slippage_cost = (slippage / cfg.point) * cfg.pip_value * lot_size

        net_profit = gross_profit - commission

        return SimulatedTrade(
            entry_price=actual_entry,
            exit_price=exit_price,
            direction=direction,
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            profit=round(net_profit, 2),
            commission=round(commission, 2),
            spread_cost=round(spread_cost, 2),
            slippage_cost=round(slippage_cost, 2),
            gross_profit=round(gross_profit, 2),
            bar_index=bar_index,
        )


# Default configs for supported symbols
SYMBOL_CONFIGS = {
    "EURUSD": SimulationConfig(
        spread_pips=1.2,
        commission_per_lot=7.0,
        slippage_pips=0.3,
        pip_value=10.0,
        point=0.0001,
    ),
    "XAUUSD": SimulationConfig(
        spread_pips=3.0,
        commission_per_lot=7.0,
        slippage_pips=1.0,
        pip_value=1.0,  # $1 per pip per 0.01 lot (adjusted)
        point=0.01,
    ),
}
