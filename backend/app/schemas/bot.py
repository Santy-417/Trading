import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


# ── Bot Config ────────────────────────────────────────────────────────────────

_VALID_STRATEGIES = {"bias", "fibonacci", "ict", "hybrid_ml", "manual"}
_VALID_TIMEFRAMES  = {"M5", "M15", "M30", "H1", "H4", "D1"}
_VALID_LOT_MODES   = {"fixed", "percent_risk", "dynamic"}
_VALID_SYMBOLS     = {"EURUSD", "XAUUSD", "DXY", "USDCAD", "GBPUSD", "AUDCAD", "EURJPY", "USDJPY", "EURGBP"}


class BotConfigResponse(BaseModel):
    """Full bot_config row returned by GET /bot/config and PATCH /bot/config."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    strategy: str
    symbols: list[str]
    timeframe: str
    risk_per_trade: float
    lot_mode: str
    fixed_lot: float
    max_trades_per_hour: int
    strategy_params: dict[str, Any]
    error_state: bool
    last_error: str | None
    last_heartbeat: datetime | None
    crash_count: int
    created_at: datetime
    updated_at: datetime
    # Not persisted — computed on PATCH, always False on GET
    requires_restart: bool = False


class StrategyParamsUpdate(BaseModel):
    """Partial update for strategy_params JSONB. All fields optional."""

    entropy_threshold:    float | None = Field(default=None, ge=2.0,  le=4.0)
    choch_lookback:       int   | None = Field(default=None, ge=10,   le=200)
    min_rr:               float | None = Field(default=None, ge=1.0,  le=5.0)
    sl_pips_base:         float | None = Field(default=None, ge=5.0,  le=100.0)
    sweep_tolerance_pips: float | None = Field(default=None, ge=1.0,  le=20.0)


class SignalStatusResponse(BaseModel):
    """Response for GET /bot/signal-status."""

    # Bot state
    bot_state: str                    # "ACTIVO" | "DETENIDO" | "ERROR"
    is_running: bool

    # Strategy internal state (only meaningful when bot is running)
    block_reason: str | None          # e.g. "sin_sweep", "fuera_sesion_ny"
    block_detail: str | None          # Human-readable explanation
    daily_bias: str | None            # "BULLISH" | "BEARISH" | "NEUTRAL"
    sweep_detected: bool

    # Last executed trade
    last_trade: dict | None

    # Current session (calculated server-side from UTC)
    current_session: str              # "london" | "ny" | "overlap" | "closed"
    ny_open_minutes: int | None       # Minutes until NY opens (None if already open)


class BotConfigUpdateRequest(BaseModel):
    """
    PATCH /bot/config body — all fields optional, only sent fields are updated.

    Top-level range validation is enforced by Field constraints.
    strategy_params is merged into the existing JSONB (not replaced).
    """

    strategy:             str | None = Field(default=None)
    symbols:              list[str] | None = Field(default=None, min_length=1)
    timeframe:            str | None = Field(default=None)
    risk_per_trade:       float | None = Field(default=None, ge=0.1,  le=5.0)
    lot_mode:             str | None = Field(default=None)
    fixed_lot:            float | None = Field(default=None, ge=0.01, le=100.0)
    max_trades_per_hour:  int   | None = Field(default=None, ge=1,    le=20)
    strategy_params:      StrategyParamsUpdate | None = None
