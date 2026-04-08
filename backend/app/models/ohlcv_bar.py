import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OHLCVBar(Base):
    """
    Persisted OHLCV candles for backtesting independence from live MT5.

    A unique constraint on (symbol, timeframe, timestamp) prevents duplicate
    bars from being inserted when re-syncing the same date range.
    """

    __tablename__ = "ohlcv_bars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    open: Mapped[float] = mapped_column(Numeric(18, 5), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 5), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 5), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 5), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    source: Mapped[str] = mapped_column(String(10), nullable=False)  # "mt5" | "yfinance"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_ohlcv_symbol_tf_ts"),
        Index("ix_ohlcv_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
        Index("ix_ohlcv_symbol_tf", "symbol", "timeframe"),
    )
