from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class TradeResponse(BaseModel):
    id: UUID
    symbol: str
    direction: str
    lot_size: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    exit_price: Decimal | None
    profit: Decimal | None
    commission: Decimal
    swap: Decimal
    strategy: str
    timeframe: str
    mt5_ticket: int | None
    status: str
    opened_at: datetime
    closed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int
