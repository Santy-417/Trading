from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class BotConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bot_config"

    name: Mapped[str] = mapped_column(String(100), default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="fibonacci")
    symbols: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["EURUSD", "XAUUSD"]
    )
    timeframe: Mapped[str] = mapped_column(String(10), default="H1")
    risk_per_trade: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1.0")
    )
    lot_mode: Mapped[str] = mapped_column(
        String(20), default="percent_risk"
    )  # fixed / percent_risk / dynamic
    fixed_lot: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0.01")
    )
    max_trades_per_hour: Mapped[int] = mapped_column(default=10)
    strategy_params: Mapped[dict] = mapped_column(JSONB, default={})
