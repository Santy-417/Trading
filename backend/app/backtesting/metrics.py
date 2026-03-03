import numpy as np
import pandas as pd


def calculate_metrics(trades: pd.DataFrame, initial_balance: float = 10000.0) -> dict:
    """
    Calculate comprehensive backtesting metrics from a trades DataFrame.

    Expected columns: profit, entry_price, exit_price, direction, lot_size
    """
    if trades.empty:
        return _empty_metrics(initial_balance)

    profits = trades["profit"].values
    winning = profits[profits > 0]
    losing = profits[profits < 0]

    total_trades = len(profits)
    win_count = len(winning)
    loss_count = len(losing)

    total_profit = float(winning.sum()) if len(winning) > 0 else 0.0
    total_loss = float(losing.sum()) if len(losing) > 0 else 0.0
    net_profit = float(profits.sum())

    # Equity curve
    equity = initial_balance + np.cumsum(profits)
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak * 100
    max_drawdown = float(drawdown.max()) if len(drawdown) > 0 else 0.0

    # Sharpe ratio (annualized, assuming daily returns)
    if len(profits) > 1 and profits.std() > 0:
        sharpe = float((profits.mean() / profits.std()) * np.sqrt(252))
    else:
        sharpe = 0.0

    # Profit factor
    profit_factor = (total_profit / abs(total_loss)) if total_loss != 0 else 0.0

    # Win rate
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

    # Average win/loss
    avg_win = float(winning.mean()) if len(winning) > 0 else 0.0
    avg_loss = float(losing.mean()) if len(losing) > 0 else 0.0

    # Expectancy
    expectancy = float(profits.mean()) if total_trades > 0 else 0.0

    # Consecutive wins/losses
    max_consec_wins, max_consec_losses = _consecutive_streaks(profits)

    # Sortino ratio (downside deviation only)
    if len(losing) > 1 and losing.std() > 0:
        sortino = float((profits.mean() / losing.std()) * np.sqrt(252))
    else:
        sortino = 0.0

    # Calmar ratio (return / max_drawdown)
    annual_return = (float(equity[-1]) - initial_balance) / initial_balance * 100
    calmar = round(abs(annual_return / max_drawdown), 2) if max_drawdown > 0 else 0.0

    # VaR 95% (Value at Risk - 5th percentile of profits)
    var_95 = round(float(np.percentile(profits, 5)), 2) if len(profits) > 0 else 0.0

    # CVaR 95% (Expected Shortfall - average of losses worse than VaR)
    tail = profits[profits <= var_95]
    cvar_95 = round(float(tail.mean()), 2) if len(tail) > 0 else 0.0

    return {
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "win_rate": round(win_rate, 2),
        "net_profit": round(net_profit, 2),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "calmar_ratio": calmar,
        "var_95": var_95,
        "cvar_95": cvar_95,
        "max_drawdown_percent": round(max_drawdown, 2),
        "average_win": round(avg_win, 2),
        "average_loss": round(avg_loss, 2),
        "largest_win": round(float(winning.max()), 2) if len(winning) > 0 else 0.0,
        "largest_loss": round(float(losing.min()), 2) if len(losing) > 0 else 0.0,
        "expectancy": round(expectancy, 2),
        "max_consecutive_wins": max_consec_wins,
        "max_consecutive_losses": max_consec_losses,
        "initial_balance": initial_balance,
        "final_balance": round(float(equity[-1]), 2),
        "return_percent": round((float(equity[-1]) - initial_balance) / initial_balance * 100, 2),
        "equity_curve": equity.tolist(),
    }


def _consecutive_streaks(profits: np.ndarray) -> tuple[int, int]:
    """Calculate max consecutive wins and losses."""
    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0

    for p in profits:
        if p > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif p < 0:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
        else:
            current_wins = 0
            current_losses = 0

    return max_wins, max_losses


def calculate_session_analysis(trades: list[dict]) -> dict:
    """Analyze trade performance by trading session (London vs NY)."""
    london_trades = []
    ny_trades = []

    for t in trades:
        entry_time = t.get("entry_time")
        if not entry_time:
            continue
        try:
            hour = pd.Timestamp(entry_time).hour
        except Exception:
            continue
        # London: 07:00-11:30 UTC (02:00-06:30 Bogota)
        if 7 <= hour <= 11:
            london_trades.append(t)
        # NY: 13:00-19:00 UTC (08:00-14:00 Bogota)
        elif 13 <= hour <= 19:
            ny_trades.append(t)

    return {
        "london": _session_metrics(london_trades),
        "ny": _session_metrics(ny_trades),
    }


def _session_metrics(trades: list[dict]) -> dict:
    """Calculate metrics for a subset of trades."""
    if not trades:
        return {"trades": 0, "win_rate": 0.0, "profit_factor": 0.0, "net_profit": 0.0}

    profits = [t["profit"] for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    total_win = sum(wins) if wins else 0.0
    total_loss = sum(losses) if losses else 0.0

    return {
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "profit_factor": round(total_win / abs(total_loss), 2) if total_loss != 0 else 0.0,
        "net_profit": round(sum(profits), 2),
    }


def calculate_buy_sell_distribution(trades: list[dict]) -> dict:
    """Calculate BUY/SELL trade distribution."""
    buy_trades = [t for t in trades if t.get("direction") == "BUY"]
    sell_trades = [t for t in trades if t.get("direction") == "SELL"]
    total = len(trades) or 1
    return {
        "buy_count": len(buy_trades),
        "sell_count": len(sell_trades),
        "buy_pct": round(len(buy_trades) / total * 100, 1),
        "sell_pct": round(len(sell_trades) / total * 100, 1),
        "ratio": round(len(buy_trades) / max(len(sell_trades), 1), 2),
    }


def _empty_metrics(initial_balance: float = 0.0) -> dict:
    return {
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,
        "net_profit": 0.0,
        "total_profit": 0.0,
        "total_loss": 0.0,
        "profit_factor": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "calmar_ratio": 0.0,
        "var_95": 0.0,
        "cvar_95": 0.0,
        "max_drawdown_percent": 0.0,
        "average_win": 0.0,
        "average_loss": 0.0,
        "largest_win": 0.0,
        "largest_loss": 0.0,
        "expectancy": 0.0,
        "max_consecutive_wins": 0,
        "max_consecutive_losses": 0,
        "initial_balance": initial_balance,
        "final_balance": initial_balance,
        "return_percent": 0.0,
        "equity_curve": [],
    }
