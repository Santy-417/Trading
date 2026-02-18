from pydantic import BaseModel, Field


class MarketOrderRequest(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., EURUSD)")
    direction: str = Field(description="BUY or SELL")
    volume: float | None = Field(default=None, description="Lot size (auto-calculated if None)")
    stop_loss: float | None = Field(default=None)
    take_profit: float | None = Field(default=None)
    comment: str = Field(default="")


class LimitOrderRequest(BaseModel):
    symbol: str
    direction: str = Field(description="BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP")
    volume: float
    price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    comment: str = ""


class ClosePositionRequest(BaseModel):
    ticket: int


class OrderResponse(BaseModel):
    success: bool
    ticket: int | None = None
    price: float | None = None
    volume: float | None = None
    comment: str = ""
    retcode: int | None = None


class PositionResponse(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    swap: float
    commission: float
    comment: str
