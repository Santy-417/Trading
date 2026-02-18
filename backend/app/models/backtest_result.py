from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class BacktestResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "backtest_results"

    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    total_trades: Mapped[int] = mapped_column(default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    net_profit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    sharpe_ratio: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    max_drawdown_percent: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    initial_balance: Mapped[float] = mapped_column(Numeric(18, 2), default=10000)
    final_balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    params: Mapped[dict | None] = mapped_column(JSONB)
    full_metrics: Mapped[dict | None] = mapped_column(JSONB)
