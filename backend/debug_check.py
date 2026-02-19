"""
Debug script to verify MT5 connection and database connectivity.
Run this from the backend directory: python debug_check.py
"""
import asyncio
from sqlalchemy import select, text

from app.integrations.metatrader.mt5_client import mt5_client
from app.integrations.supabase.client import _get_engine
from app.models.trade import Trade


async def check_mt5():
    """Check MT5 connection and positions."""
    print("\n=== MT5 Connection Check ===")
    try:
        await mt5_client.initialize()
        print("[OK] MT5 initialized successfully")

        account = await mt5_client.get_account_info()
        print(f"[OK] Account: {account['login']} - Balance: ${account['balance']}")

        positions = await mt5_client.get_open_positions()
        print(f"[OK] Open positions: {len(positions)}")
        for pos in positions:
            print(f"  - Ticket: {pos['ticket']}, Symbol: {pos['symbol']}, Type: {pos['type']}, "
                  f"Volume: {pos['volume']}, Profit: ${pos['profit']:.2f}")

    except Exception as e:
        print(f"[ERROR] MT5 Error: {e}")
        import traceback
        traceback.print_exc()


async def check_database():
    """Check database connection and trades."""
    print("\n=== Database Connection Check ===")
    try:
        engine = _get_engine()
        async with engine.begin() as conn:
            # Test basic query
            result = await conn.execute(text("SELECT 1"))
            print("[OK] Database connected successfully")

            # Check trades table
            result = await conn.execute(
                text("SELECT COUNT(*) FROM trades")
            )
            count = result.scalar()
            print(f"[OK] Total trades in database: {count}")

            # Get recent trades
            result = await conn.execute(
                text("SELECT symbol, direction, lot_size, entry_price, mt5_ticket, status "
                     "FROM trades ORDER BY created_at DESC LIMIT 5")
            )
            trades = result.fetchall()
            if trades:
                print("[OK] Recent trades:")
                for trade in trades:
                    print(f"  - {trade.symbol} {trade.direction} {trade.lot_size} @ {trade.entry_price}, "
                          f"ticket={trade.mt5_ticket}, status={trade.status}")
            else:
                print("[WARN] No trades found in database")

    except Exception as e:
        print(f"[ERROR] Database Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("=== Trading Platform Debug Check ===")
    await check_mt5()
    await check_database()
    print("\n=== Check Complete ===\n")


if __name__ == "__main__":
    asyncio.run(main())
