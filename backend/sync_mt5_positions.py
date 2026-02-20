"""
Sync MT5 positions to database.
This script reads open positions and historical deals from MT5 and inserts them into the database.

Usage:
    python sync_mt5_positions.py [--history-days 30]
"""
import asyncio
import argparse
from datetime import datetime, timedelta, timezone

from app.integrations.metatrader.mt5_client import mt5_client
from app.integrations.supabase.client import _get_session_factory
from app.repositories.trade_repository import TradeRepository


async def sync_open_positions():
    """Sync open positions from MT5 to database."""
    print("\n=== Syncing Open Positions from MT5 ===")

    try:
        # Initialize MT5
        await mt5_client.initialize()
        print("[OK] MT5 initialized")

        # Get open positions
        positions = await mt5_client.get_open_positions()
        print(f"[OK] Found {len(positions)} open positions in MT5")

        if not positions:
            print("[INFO] No open positions to sync")
            return

        # Connect to database
        session_factory = _get_session_factory()
        async with session_factory() as session:
            repo = TradeRepository(session)
            synced = 0
            skipped = 0

            for pos in positions:
                ticket = pos.get("ticket")

                # Check if already exists
                existing = await repo.get_by_ticket(ticket)
                if existing:
                    print(f"[SKIP] Position {ticket} already exists in DB")
                    skipped += 1
                    continue

                # Insert into database
                try:
                    await repo.create(
                        symbol=pos.get("symbol", "UNKNOWN"),
                        direction="BUY" if pos.get("type") == 0 else "SELL",
                        lot_size=pos.get("volume", 0.01),
                        entry_price=pos.get("price_open", 0),
                        stop_loss=pos.get("stop_loss"),
                        take_profit=pos.get("take_profit"),
                        strategy="manual",  # Assume manual since opened externally
                        timeframe="N/A",
                        mt5_ticket=ticket,
                        status="open",
                    )
                    synced += 1
                    print(f"[SYNC] Position {ticket}: {pos.get('symbol')} {pos.get('type_str')} {pos.get('volume')} @ {pos.get('price_open')}")
                except Exception as e:
                    print(f"[ERROR] Failed to sync position {ticket}: {e}")

            # Commit all changes
            await session.commit()
            print(f"\n[DONE] Synced {synced} positions, skipped {skipped}")

    except Exception as e:
        print(f"[ERROR] Failed to sync positions: {e}")
        import traceback
        traceback.print_exc()


async def sync_historical_deals(days: int = 30):
    """Sync historical closed deals from MT5 to database."""
    print(f"\n=== Syncing Historical Deals (last {days} days) ===")

    try:
        # Initialize MT5
        await mt5_client.initialize()

        # Get historical deals
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        to_date = datetime.now(timezone.utc)

        print(f"[INFO] Fetching deals from {from_date.date()} to {to_date.date()}")

        # Get deals history (this requires implementing get_deals_history in mt5_client)
        # For now, we'll only sync open positions
        print("[WARN] Historical deals sync not implemented yet")
        print("[INFO] Only open positions will be synced")
        print("[INFO] To implement: add get_deals_history() method to MT5Client")

    except Exception as e:
        print(f"[ERROR] Failed to sync historical deals: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main sync function."""
    parser = argparse.ArgumentParser(description="Sync MT5 positions to database")
    parser.add_argument(
        "--history-days",
        type=int,
        default=0,
        help="Number of days of historical deals to sync (0 = only open positions)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("MT5 TO DATABASE SYNC TOOL")
    print("=" * 60)

    # Sync open positions
    await sync_open_positions()

    # Sync historical deals if requested
    if args.history_days > 0:
        await sync_historical_deals(args.history_days)

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print("\nYou can now view your positions in the database:")
    print("  - Open positions: SELECT * FROM trades WHERE status = 'open';")
    print("  - All trades: SELECT * FROM trades ORDER BY opened_at DESC;")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
