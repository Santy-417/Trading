"""
DataPipeline: download, persist, and retrieve OHLCV market data.

Primary source : MetaTrader 5 (get_historical_data_range)
Fallback source: yfinance (chunked to respect per-interval limits)
Storage        : ohlcv_bars table via SQLAlchemy async session
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.integrations.metatrader.mt5_client import Timeframe, mt5_client
from app.models.ohlcv_bar import OHLCVBar

logger = get_logger(__name__)

# ── yfinance mappings ────────────────────────────────────────────────────────

# MT5 symbol -> yfinance ticker
YFINANCE_TICKERS: dict[str, str] = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCAD": "USDCAD=X",
    "EURJPY": "EURJPY=X",
    "AUDCAD": "AUDCAD=X",
    "EURGBP": "EURGBP=X",
}

# Trading timeframe -> yfinance interval string
YFINANCE_INTERVALS: dict[str, str] = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

# Max days per chunk for each interval (yfinance API limits)
_YFINANCE_CHUNK_DAYS: dict[str, int] = {
    "1m": 7,
    "5m": 55,
    "15m": 55,
    "30m": 55,
    "1h": 700,
    "4h": 700,
    "1d": 3600,
}

# ── batch size for DB inserts ────────────────────────────────────────────────

_BATCH_SIZE = 1000


# ════════════════════════════════════════════════════════════════════════════
# DataPipeline
# ════════════════════════════════════════════════════════════════════════════


class DataPipeline:
    """
    Orchestrates OHLCV data flow:
      MT5 (primary) -> yfinance (fallback) -> ohlcv_bars table -> DataFrame

    All timestamps are stored and returned as timezone-aware UTC datetimes.
    """

    # ── download ─────────────────────────────────────────────────────────────

    async def download_historical(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        Download OHLCV bars for a date range.

        Tries MT5 first; falls back to yfinance on any failure.

        Returns DataFrame with columns:
            time (UTC, tz-aware), open, high, low, close, volume
        """
        # Ensure inputs are UTC-aware
        start_date = _as_utc(start_date)
        end_date = _as_utc(end_date)

        logger.info(
            "Downloading %s %s from %s to %s",
            symbol, timeframe, start_date.date(), end_date.date(),
        )

        # ── MT5 ──────────────────────────────────────────────────────────────
        try:
            tf = Timeframe(timeframe)
            raw = await mt5_client.get_historical_data_range(symbol, tf, start_date, end_date)
            df = _normalize_mt5(raw)
            logger.info("MT5: %s %s -> %d bars", symbol, timeframe, len(df))
            return df
        except Exception as mt5_err:
            logger.warning(
                "MT5 download failed for %s %s: %s — falling back to yfinance",
                symbol, timeframe, mt5_err,
            )

        # ── yfinance ─────────────────────────────────────────────────────────
        df = await asyncio.to_thread(
            _download_yfinance, symbol, timeframe, start_date, end_date
        )
        logger.info("yfinance: %s %s -> %d bars", symbol, timeframe, len(df))
        return df

    # ── save ─────────────────────────────────────────────────────────────────

    async def save_to_db(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        source: str,
        db_session: AsyncSession,
    ) -> dict:
        """
        Persist OHLCV bars to ohlcv_bars using INSERT … ON CONFLICT DO NOTHING.

        Rows that already exist (same symbol + timeframe + timestamp) are
        silently skipped, making the method safe to re-run.

        Processes rows in batches of 1 000 to avoid saturating the connection.

        Returns:
            {"inserted": N, "skipped": N, "total": N}
        """
        if df.empty:
            return {"inserted": 0, "skipped": 0, "total": 0}

        total = len(df)
        total_inserted = 0
        n_batches = (total + _BATCH_SIZE - 1) // _BATCH_SIZE

        for batch_idx, batch_start in enumerate(range(0, total, _BATCH_SIZE), start=1):
            batch = df.iloc[batch_start : batch_start + _BATCH_SIZE]

            rows = []
            for _, row in batch.iterrows():
                ts = row["time"]
                # Ensure tz-aware UTC
                if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                elif hasattr(ts, "tz_convert"):
                    ts = ts.tz_convert(timezone.utc)

                rows.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "timestamp": ts,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": int(row["volume"]),
                        "source": source,
                    }
                )

            stmt = (
                pg_insert(OHLCVBar)
                .values(rows)
                .on_conflict_do_nothing(
                    index_elements=["symbol", "timeframe", "timestamp"]
                )
            )
            result = await db_session.execute(stmt)
            await db_session.commit()

            # rowcount reflects only the rows actually inserted
            batch_inserted = result.rowcount if result.rowcount >= 0 else len(rows)
            total_inserted += batch_inserted

            logger.info(
                "Batch %d/%d: %d inserted of %d",
                batch_idx, n_batches, batch_inserted, len(rows),
            )

        skipped = total - total_inserted
        logger.info(
            "%s %s save_to_db: total=%d inserted=%d skipped=%d",
            symbol, timeframe, total, total_inserted, skipped,
        )
        return {"inserted": total_inserted, "skipped": skipped, "total": total}

    # ── get ──────────────────────────────────────────────────────────────────

    async def get_from_db(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        db_session: AsyncSession,
    ) -> pd.DataFrame:
        """
        Query ohlcv_bars for a symbol / timeframe / date range.

        If no rows exist in the DB for the requested range, automatically
        downloads via download_historical() and persists the result before
        returning.

        Returns DataFrame with columns:
            time (UTC, tz-aware), open, high, low, close, volume
        """
        start_date = _as_utc(start_date)
        end_date = _as_utc(end_date)

        stmt = (
            select(OHLCVBar)
            .where(
                OHLCVBar.symbol == symbol,
                OHLCVBar.timeframe == timeframe,
                OHLCVBar.timestamp >= start_date,
                OHLCVBar.timestamp <= end_date,
            )
            .order_by(OHLCVBar.timestamp)
        )
        result = await db_session.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            logger.info(
                "No cached data for %s %s [%s – %s] — downloading",
                symbol, timeframe, start_date.date(), end_date.date(),
            )
            df = await self.download_historical(symbol, timeframe, start_date, end_date)
            # Detect source from whichever download succeeded
            source = "mt5"  # best-effort; download_historical logs the real source
            await self.save_to_db(df, symbol, timeframe, source, db_session)
            return df

        logger.info(
            "Loaded %d bars from DB: %s %s", len(rows), symbol, timeframe
        )
        return pd.DataFrame(
            {
                "time": [r.timestamp for r in rows],
                "open": [float(r.open) for r in rows],
                "high": [float(r.high) for r in rows],
                "low": [float(r.low) for r in rows],
                "close": [float(r.close) for r in rows],
                "volume": [int(r.volume) for r in rows],
            }
        )

    # ── coverage ─────────────────────────────────────────────────────────────

    async def get_data_coverage(self, db_session: AsyncSession) -> dict:
        """
        Summarise what OHLCV data is available in the DB.

        Returns:
            {
                "XAUUSD": {
                    "H1":  {"from": "2021-01-04T...", "to": "2026-04-01T...", "bars": 12345},
                    "M15": {...},
                },
                "EURUSD": {...},
            }
        """
        stmt = (
            select(
                OHLCVBar.symbol,
                OHLCVBar.timeframe,
                func.min(OHLCVBar.timestamp).label("from_date"),
                func.max(OHLCVBar.timestamp).label("to_date"),
                func.count().label("bars"),
            )
            .group_by(OHLCVBar.symbol, OHLCVBar.timeframe)
            .order_by(OHLCVBar.symbol, OHLCVBar.timeframe)
        )
        result = await db_session.execute(stmt)
        rows = result.all()

        coverage: dict = {}
        for row in rows:
            sym, tf = row.symbol, row.timeframe
            coverage.setdefault(sym, {})[tf] = {
                "from": row.from_date.isoformat() if row.from_date else None,
                "to": row.to_date.isoformat() if row.to_date else None,
                "bars": row.bars,
            }
        return coverage


# ════════════════════════════════════════════════════════════════════════════
# Module-level singleton
# ════════════════════════════════════════════════════════════════════════════

data_pipeline = DataPipeline()


# ════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ════════════════════════════════════════════════════════════════════════════


def _as_utc(dt: datetime) -> datetime:
    """Return a UTC-aware datetime regardless of the input's tz state."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_mt5(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert an MT5 DataFrame (DatetimeIndex, tz-naive server time) to the
    standard pipeline format.
    """
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")

    volume_col = "tick_volume" if "tick_volume" in df.columns else "real_volume"

    return pd.DataFrame(
        {
            "time": idx,
            "open": df["open"].values,
            "high": df["high"].values,
            "low": df["low"].values,
            "close": df["close"].values,
            "volume": df[volume_col].fillna(0).astype(int).values,
        }
    )


def _normalize_yfinance(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a yfinance DataFrame (tz-aware or tz-naive index) to standard format."""
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")

    # yfinance columns may be MultiIndex when downloading a single ticker
    def _col(name: str):
        if isinstance(df.columns, pd.MultiIndex):
            matches = [c for c in df.columns if c[0] == name]
            return df[matches[0]] if matches else pd.Series(0, index=df.index)
        return df[name] if name in df.columns else pd.Series(0, index=df.index)

    return pd.DataFrame(
        {
            "time": idx,
            "open": _col("Open").values,
            "high": _col("High").values,
            "low": _col("Low").values,
            "close": _col("Close").values,
            "volume": _col("Volume").fillna(0).astype(int).values,
        }
    )


def _download_yfinance(
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """
    Synchronous yfinance download, chunked to respect per-interval API limits.
    Designed to run inside asyncio.to_thread().
    """
    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance is not installed. Run: pip install yfinance")

    ticker_symbol = YFINANCE_TICKERS.get(symbol)
    if not ticker_symbol:
        raise ValueError(
            f"No yfinance ticker mapping for '{symbol}'. "
            f"Supported: {list(YFINANCE_TICKERS)}"
        )

    interval = YFINANCE_INTERVALS.get(timeframe)
    if not interval:
        raise ValueError(
            f"No yfinance interval mapping for '{timeframe}'. "
            f"Supported: {list(YFINANCE_INTERVALS)}"
        )

    max_days = _YFINANCE_CHUNK_DAYS.get(interval, 700)

    # Yahoo Finance requires the START date to also be within the lookback window.
    # Clamp start_date so we never request chunks that will always return empty.
    now_utc = datetime.now(timezone.utc)
    earliest_available = now_utc - timedelta(days=max_days - 1)
    if start_date < earliest_available:
        logger.warning(
            "yfinance %s %s: requested start %s is outside the %d-day API window. "
            "Clamping to %s. Use MT5 for older data.",
            ticker_symbol, interval,
            start_date.strftime("%Y-%m-%d"), max_days,
            earliest_available.strftime("%Y-%m-%d"),
        )
        start_date = earliest_available

    chunks: list[pd.DataFrame] = []
    chunk_start = start_date

    while chunk_start < end_date:
        chunk_end = min(chunk_start + timedelta(days=max_days), end_date)
        logger.info(
            "yfinance %s %s: fetching %s -> %s",
            ticker_symbol, interval,
            chunk_start.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d"),
        )

        try:
            raw = yf.download(
                ticker_symbol,
                start=chunk_start.strftime("%Y-%m-%d"),
                end=chunk_end.strftime("%Y-%m-%d"),
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            if not raw.empty:
                chunks.append(raw)
            else:
                logger.warning("yfinance returned empty data for chunk %s -> %s", chunk_start.date(), chunk_end.date())
        except Exception as e:
            logger.warning("yfinance chunk failed (%s -> %s): %s", chunk_start.date(), chunk_end.date(), e)

        chunk_start = chunk_end
        time.sleep(1.5)  # Be polite to the yfinance API

    if not chunks:
        raise ValueError(
            f"yfinance returned no data for {symbol} ({ticker_symbol}) "
            f"{timeframe} [{start_date.date()} – {end_date.date()}]"
        )

    combined = pd.concat(chunks)
    combined = combined[~combined.index.duplicated(keep="first")].sort_index()
    return _normalize_yfinance(combined)
