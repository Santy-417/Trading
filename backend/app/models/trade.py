from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Trade(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "trades"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    lot_size: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    swap: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    mt5_ticket: Mapped[int | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open"
    )  # open / closed / cancelled
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_trades_symbol", "symbol"),
        Index("ix_trades_status", "status"),
        Index("ix_trades_opened_at", "opened_at"),
        Index("ix_trades_strategy", "strategy"),
    )
