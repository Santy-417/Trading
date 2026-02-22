"""
Run BiasStrategy V1 Optimization backtests on EURUSD and XAUUSD with 10k bars.
"""
import asyncio
import json
from datetime import datetime

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import BacktestEngine
from app.core.logging_config import get_logger
from app.strategies import get_strategy

logger = get_logger(__name__)


async def run_backtest(symbol: str, bars: int = 10000):
    """Run backtest for a specific symbol."""
    logger.info(f"=" * 80)
    logger.info(f"Starting V1 Backtest: {symbol} | {bars} bars")
    logger.info(f"=" * 80)

    # Load data
    print(f"Loading {bars} bars of {symbol} H1 data from MT5...")
    loader = DataLoader()
    df = await loader.load_from_mt5(symbol, "H1", count=bars)
    df = DataLoader.validate_data(df)
    print(f"Loaded {len(df)} bars")

    # Get strategy instance
    strategy = get_strategy("bias")

    # Run backtest
    print(f"Running backtest...")
    engine = BacktestEngine(initial_balance=10000.0, risk_per_trade=1.0)
    result = engine.run(
        strategy=strategy,
        df=df,
        symbol=symbol,
        timeframe="H1",
        lot_mode="percent_risk",
    )

    # Print summary
    print(f"\n{'=' * 80}")
    print(f"BACKTEST RESULTS: {symbol} ({bars} bars)")
    print(f"{'=' * 80}")
    print(f"Total Trades:      {result['total_trades']}")
    print(f"Winning Trades:    {result['winning_trades']}")
    print(f"Losing Trades:     {result['losing_trades']}")
    print(f"Win Rate:          {result['win_rate']:.2f}%")
    print(f"Profit Factor:     {result.get('profit_factor', 0):.2f}")
    print(f"Sharpe Ratio:      {result.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown:      ${result.get('max_drawdown', 0):.2f} ({result.get('max_drawdown_percent', 0):.2f}%)")
    print(f"Net Profit:        ${result.get('net_profit', 0):.2f}")
    print(f"{'=' * 80}")

    # Print trade details
    trades = result.get("trades", [])
    if trades:
        print(f"\nTRADE DETAILS ({len(trades)} trades):")
        print(f"{'-' * 80}")
        for i, trade in enumerate(trades, 1):
            entry_time = trade.get("entry_time", "N/A")

            print(f"\nTrade #{i}:")
            print(f"  Entry:  {entry_time} @ {trade['entry_price']:.5f} ({trade['direction']})")
            print(f"  Exit:   @ {trade['exit_price']:.5f} ({trade['exit_reason']})")
            print(f"  SL/TP:  {trade['stop_loss']:.5f} / {trade['take_profit']:.5f}")
            print(f"  P&L:    ${trade['profit']:.2f} (RR: {trade.get('risk_reward', 0):.2f})")

            # Print metadata
            meta = trade.get("signal_metadata", {})
            if meta:
                print(f"  Bias:   {meta.get('daily_bias', 'N/A')}")
                print(f"  ChoCh:  {meta.get('choch_detected', 'N/A')} | Fractal Fallback: {meta.get('fractal_break_fallback', 'N/A')}")
                print(f"  Entropy: {meta.get('entropy', 'N/A')} (z={meta.get('entropy_zscore', 'N/A')})")
                print(f"  Manipulation: {meta.get('manipulation_type', 'N/A')} @ {meta.get('manipulation_level', 'N/A'):.5f}")

    print(f"\n{'=' * 80}\n")

    return result


async def main():
    """Run backtests on both symbols."""
    # Run EURUSD backtest
    eurusd_result = await run_backtest("EURUSD", 10000)

    # Run XAUUSD backtest
    xauusd_result = await run_backtest("XAUUSD", 10000)

    # Final summary
    print(f"\n{'=' * 80}")
    print("FINAL SUMMARY - BiasStrategy V1 Optimization")
    print(f"{'=' * 80}")
    print(f"\nEURUSD (10k bars):")
    print(f"  Trades: {eurusd_result['total_trades']} | Win Rate: {eurusd_result['win_rate']:.1f}% | "
          f"Profit Factor: {eurusd_result.get('profit_factor', 0):.2f} | Sharpe: {eurusd_result.get('sharpe_ratio', 0):.2f}")

    print(f"\nXAUUSD (10k bars):")
    print(f"  Trades: {xauusd_result['total_trades']} | Win Rate: {xauusd_result['win_rate']:.1f}% | "
          f"Profit Factor: {xauusd_result.get('profit_factor', 0):.2f} | Sharpe: {xauusd_result.get('sharpe_ratio', 0):.2f}")

    print(f"\nV1 Target Metrics:")
    print(f"  Trades/year: 15-30 (2-3/week)")
    print(f"  Win Rate: 40-55%")
    print(f"  Profit Factor: >1.0")
    print(f"  Sharpe Ratio: >0.8")

    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())
