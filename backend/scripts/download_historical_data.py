"""
Standalone script: download historical OHLCV data into ohlcv_bars.

Downloads:
  XAUUSD H1  — 5 years
  XAUUSD M15 — 2 years
  EURUSD H1  — 5 years
  EURUSD M15 — 2 years

Re-running the script is safe: existing bars are skipped via ON CONFLICT DO NOTHING.

Usage (from backend/ directory):
    python scripts/download_historical_data.py

    # Override lookback (e.g. only last 30 days for H1, 7 days for M15):
    python scripts/download_historical_data.py --h1-years 0.08 --m15-years 0.02

Options:
    --h1-years   N    Lookback in years for H1 data  (default: 5)
    --m15-years  N    Lookback in years for M15 data (default: 2)
    --dry-run         Print the plan without downloading anything
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── path setup ───────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# ── imports (after path setup) ───────────────────────────────────────────────
from app.core.logging_config import get_logger, setup_logging
from app.integrations.metatrader.mt5_client import mt5_client
from app.integrations.supabase.client import _get_session_factory
from app.services.data_pipeline import DataPipeline

setup_logging("INFO")
logger = get_logger(__name__)

# ── tqdm with plain-print fallback ───────────────────────────────────────────
try:
    from tqdm import tqdm as _tqdm

    def progress_bar(iterable, **kwargs):
        return _tqdm(iterable, **kwargs)

    def print_progress(current: int, total: int, label: str) -> None:
        pass  # tqdm handles it

except ImportError:
    def progress_bar(iterable, **kwargs):
        return iterable

    def print_progress(current: int, total: int, label: str) -> None:
        pct = int(current / total * 100) if total else 0
        print(f"  [{pct:3d}%] {label}: {current}/{total}", flush=True)


# ════════════════════════════════════════════════════════════════════════════
# Job definitions
# ════════════════════════════════════════════════════════════════════════════

def build_jobs(h1_years: float, m15_years: float) -> list[dict]:
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    def years_ago(n: float) -> datetime:
        return now - timedelta(days=int(n * 365))

    return [
        {"symbol": "XAUUSD", "timeframe": "H1",  "start": years_ago(h1_years),  "end": now},
        {"symbol": "XAUUSD", "timeframe": "M15", "start": years_ago(m15_years), "end": now},
        {"symbol": "EURUSD", "timeframe": "H1",  "start": years_ago(h1_years),  "end": now},
        {"symbol": "EURUSD", "timeframe": "M15", "start": years_ago(m15_years), "end": now},
    ]


# ════════════════════════════════════════════════════════════════════════════
# Main runner
# ════════════════════════════════════════════════════════════════════════════

async def run(jobs: list[dict], dry_run: bool) -> None:
    pipeline = DataPipeline()
    summary: list[dict] = []

    # ── MT5 init (best-effort; yfinance fallback kicks in on failure) ─────────
    mt5_available = False
    if not dry_run:
        try:
            await mt5_client.initialize()
            mt5_available = True
            logger.info("MT5 connected — will use MT5 as primary data source")
        except Exception as mt5_err:
            logger.warning("MT5 unavailable (%s) — falling back to yfinance", mt5_err)

    print()
    print("=" * 60)
    print(" Historical Data Download")
    print("=" * 60)

    for i, job in enumerate(jobs, start=1):
        symbol    = job["symbol"]
        timeframe = job["timeframe"]
        start     = job["start"]
        end       = job["end"]

        label = f"{symbol} {timeframe} [{start.strftime('%Y-%m-%d')} -> {end.strftime('%Y-%m-%d')}]"
        print(f"\n[{i}/{len(jobs)}] {label}")

        if dry_run:
            print("  (dry-run — skipping download)")
            summary.append({"job": label, "inserted": 0, "skipped": 0, "total": 0})
            continue

        try:
            # ── download ─────────────────────────────────────────────────
            print(f"  Downloading...", flush=True)
            df = await pipeline.download_historical(symbol, timeframe, start, end)
            print(f"  Downloaded {len(df):,} bars", flush=True)

            # ── save ─────────────────────────────────────────────────────
            print(f"  Saving to DB...", flush=True)

            source = "mt5" if mt5_available else "yfinance"

            async with _get_session_factory()() as session:
                stats = await pipeline.save_to_db(df, symbol, timeframe, source, session)

            print(
                f"  Done: {stats['inserted']:,} inserted, "
                f"{stats['skipped']:,} already existed",
                flush=True,
            )
            summary.append({"job": label, **stats})

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Progress saved — re-run to resume.")
            _print_summary(summary)
            sys.exit(0)
        except Exception as e:
            logger.error("Job failed: %s — %s", label, e, exc_info=True)
            summary.append({"job": label, "inserted": 0, "skipped": 0, "total": 0, "error": str(e)})
            print(f"  ERROR: {e}", flush=True)

    _print_summary(summary)

    # ── MT5 shutdown ──────────────────────────────────────────────────────────
    if mt5_available:
        await mt5_client.shutdown()


def _print_summary(summary: list[dict]) -> None:
    print()
    print("=" * 60)
    print(" Summary")
    print("=" * 60)
    total_inserted = 0
    total_skipped = 0
    for row in summary:
        status = f"ERROR: {row['error']}" if "error" in row else (
            f"{row['inserted']:>7,} inserted  {row['skipped']:>7,} skipped"
        )
        print(f"  {row['job']}")
        print(f"    {status}")
        total_inserted += row.get("inserted", 0)
        total_skipped  += row.get("skipped", 0)
    print()
    print(f"  TOTAL inserted : {total_inserted:,}")
    print(f"  TOTAL skipped  : {total_skipped:,}")
    print("=" * 60)


# ════════════════════════════════════════════════════════════════════════════
# Entrypoint
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical OHLCV data into Supabase")
    parser.add_argument("--h1-years",  type=float, default=5.0, help="Lookback years for H1 data (default: 5)")
    parser.add_argument("--m15-years", type=float, default=2.0, help="Lookback years for M15 data (default: 2)")
    parser.add_argument("--dry-run",   action="store_true",     help="Print plan without downloading")
    args = parser.parse_args()

    jobs = build_jobs(h1_years=args.h1_years, m15_years=args.m15_years)

    # Show plan
    print()
    print("Download plan:")
    for job in jobs:
        bars_est = {
            "H1":  int(args.h1_years * 365 * 8),   # ~8 bars/day (forex hours)
            "M15": int(args.m15_years * 365 * 32),  # ~32 bars/day
        }.get(job["timeframe"], 0)
        print(
            f"  {job['symbol']:8s} {job['timeframe']:4s}  "
            f"{job['start'].strftime('%Y-%m-%d')} -> {job['end'].strftime('%Y-%m-%d')}  "
            f"(~{bars_est:,} bars est.)"
        )

    if args.dry_run:
        print("\n(dry-run mode — no data will be downloaded)")

    print()

    try:
        asyncio.run(run(jobs, dry_run=args.dry_run))
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
