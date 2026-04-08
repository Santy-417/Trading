from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class OHLCVBarCreate(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    source: str  # "mt5" | "yfinance"


class OHLCVBarRead(BaseModel):
    id: UUID
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class OHLCVBarQuery(BaseModel):
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
