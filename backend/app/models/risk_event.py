from decimal import Decimal

from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class RiskEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_events"

    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # daily_loss_breach / max_drawdown / overtrading / kill_switch
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="warning"
    )  # warning / critical / emergency
    message: Mapped[str] = mapped_column(Text, nullable=False)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    action_taken: Mapped[str] = mapped_column(
        String(50), default="none"
    )  # none / bot_stopped / positions_closed

    __table_args__ = (
        Index("ix_risk_events_type", "event_type"),
        Index("ix_risk_events_severity", "severity"),
        Index("ix_risk_events_created", "created_at"),
    )