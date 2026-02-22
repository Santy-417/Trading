"""
Run BiasStrategy V1 Optimization backtests on EURUSD and XAUUSD with synthetic data.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

from app.backtesting.engine import BacktestEngine
from app.core.logging_config import get_logger
from app.strategies import get_strategy

logger = get_logger(__name__)


def generate_synthetic_ohlcv(symbol: str, bars: int = 10000, start_price: float = None) -> pd.DataFrame:
    """Generate synthetic OHLCV data with realistic price movements."""
    if start_price is None:
        start_price = 1.18000 if symbol == "EURUSD" else 1900.00

    # Parameters based on symbol
    if symbol == "EURUSD":
        pip = 0.0001
        volatility = 0.0005  # ~50 pips per hour average move
        spread = 0.00015  # 1.5 pips
    else:  # XAUUSD
        pip = 0.01
        volatility = 0.50  # ~50 cents per hour average move
        spread = 0.30  # 30 cents

    # Generate timestamps (H1 bars, starting 1 year ago)
    end_time = datetime.now(pytz.UTC)
    start_time = end_time - timedelta(hours=bars)
    timestamps = pd.date_range(start=start_time, periods=bars, freq="1h", tz=pytz.UTC)

    # Generate price data with realistic movements
    np.random.seed(42)  # Reproducibility
    data = []

    current_price = start_price

    for i, ts in enumerate(timestamps):
        # Simulate daily trend
        day_num = i // 24
        daily_trend = np.sin(day_num / 10) * volatility * 5  # Multi-day cycles

        # Hourly movement
        hourly_change = np.random.randn() * volatility + daily_trend

        open_price = current_price
        close_price = current_price + hourly_change

        # High/Low based on intrabar volatility
        high_price = max(open_price, close_price) + abs(np.random.randn()) * volatility * 0.5
        low_price = min(open_price, close_price) - abs(np.random.randn()) * volatility * 0.5

        # Volume
        tick_volume = int(np.random.gamma(2, 500))  # Realistic tick volume distribution

        data.append({
            "time": ts,
            "open": round(open_price, 5),
            "high": round(high_price, 5),
            "low": round(low_price, 5),
            "close": round(close_price, 5),
            "tick_volume": tick_volume,
            "spread": int(spread / pip),
            "real_volume": 0,
        })

        current_price = close_price

    df = pd.DataFrame(data)
    df.set_index("time", inplace=True)
    df.attrs["symbol"] = symbol
    df.attrs["timeframe"] = "H1"

    logger.info(f"Generated {len(df)} bars of synthetic {symbol} data")
    logger.info(f"Price range: {df['low'].min():.5f} - {df['high'].max():.5f}")

    return df


def run_backtest(symbol: str, bars: int = 10000):
    """Run backtest for a specific symbol."""
    logger.info(f"=" * 80)
    logger.info(f"Starting V1 Backtest: {symbol} | {bars} bars (SYNTHETIC DATA)")
    logger.info(f"=" * 80)

    # Generate synthetic data
    print(f"Generating {bars} bars of synthetic {symbol} H1 data...")
    df = generate_synthetic_ohlcv(symbol, bars)
    print(f"Generated {len(df)} bars (price range: {df['low'].min():.5f} - {df['high'].max():.5f})")

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
    print(f"BACKTEST RESULTS: {symbol} ({bars} bars - SYNTHETIC)")
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

            # Print V1 metadata
            meta = trade.get("signal_metadata", {})
            if meta:
                print(f"  Bias:   {meta.get('daily_bias', 'N/A')}")
                choch = meta.get('choch_detected', 'N/A')
                fractal = meta.get('fractal_break_fallback', 'N/A')
                print(f"  ChoCh:  {choch} | Fractal Fallback: {fractal}")
                print(f"  Entropy: {meta.get('entropy', 'N/A')} (z={meta.get('entropy_zscore', 'N/A')})")
                manip_type = meta.get('manipulation_type', 'N/A')
                manip_level = meta.get('manipulation_level', 0)
                if isinstance(manip_level, (int, float)):
                    print(f"  Manipulation: {manip_type} @ {manip_level:.5f}")
                else:
                    print(f"  Manipulation: {manip_type} @ {manip_level}")
    else:
        print(f"\nNo trades generated. Check logs for filtering reasons.")

    print(f"\n{'=' * 80}\n")

    return result


def main():
    """Run backtests on both symbols."""
    # Run EURUSD backtest
    eurusd_result = run_backtest("EURUSD", 10000)

    # Run XAUUSD backtest
    xauusd_result = run_backtest("XAUUSD", 10000)

    # Final summary
    print(f"\n{'=' * 80}")
    print("FINAL SUMMARY - BiasStrategy V1 Optimization (SYNTHETIC DATA)")
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

    # Analysis vs targets
    eurusd_trades_per_year = eurusd_result['total_trades'] / (10000 / 24 / 365) if (10000 / 24 / 365) > 0 else 0
    xauusd_trades_per_year = xauusd_result['total_trades'] / (10000 / 24 / 365) if (10000 / 24 / 365) > 0 else 0

    print(f"\nProjected Annual Frequency:")
    print(f"  EURUSD: ~{eurusd_trades_per_year:.0f} trades/year")
    print(f"  XAUUSD: ~{xauusd_trades_per_year:.0f} trades/year")

    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    main()
