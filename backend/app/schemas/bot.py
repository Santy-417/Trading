from pydantic import BaseModel, Field


class BotStartRequest(BaseModel):
    strategy: str = Field(default="fibonacci", description="Strategy name")
    symbols: list[str] = Field(default=["EURUSD", "XAUUSD"])
    timeframe: str = Field(default="H1")
    risk_per_trade: float = Field(default=1.0, ge=0.1, le=5.0)
    lot_mode: str = Field(default="percent_risk")
    fixed_lot: float = Field(default=0.01, ge=0.01)
    loop_interval: int = Field(default=60, ge=10, le=3600)
    strategy_params: dict | None = None


class BotStopRequest(BaseModel):
    pass


class BotKillRequest(BaseModel):
    close_positions: bool = Field(default=True)
    reason: str = Field(default="Manual kill switch")


class BotStatusResponse(BaseModel):
    state: str
    strategy: str | None
    symbols: list[str]
    timeframe: str
    risk: dict


class BotKillResponse(BaseModel):
    message: str
    positions_closed: list[dict]
    error: str | None = None


class AccountInfoResponse(BaseModel):
    balance: float
    equity: float
    profit: float
    margin: float
    free_margin: float
    leverage: int
    currency: str
    name: str
    server: str


class BotLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    symbol: str | None = None
