from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy: str = Field(default="fibonacci")
    symbol: str = Field(default="EURUSD")
    timeframe: str = Field(default="H1")
    # Legacy mode (bar count)
    bars: int | None = Field(default=None, ge=100, le=50000)
    # Date range mode
    date_from: str | None = Field(default=None, description="ISO format: 2025-01-01T00:00:00")
    date_to: str | None = Field(default=None, description="ISO format: 2025-06-30T23:59:59")
    timezone: str = Field(default="America/Bogota")
    warmup_bars: int = Field(default=200, ge=50, le=500)
    initial_balance: float = Field(default=10000.0, ge=100)
    risk_per_trade: float = Field(default=1.0, ge=0.1, le=5.0)
    lot_mode: str = Field(default="percent_risk")
    strategy_params: dict | None = None


class BacktestEstimateRequest(BaseModel):
    timeframe: str = Field(default="H1")
    date_from: str = Field(description="ISO format: 2025-01-01T00:00:00")
    date_to: str = Field(description="ISO format: 2025-06-30T23:59:59")
    timezone: str = Field(default="America/Bogota")
    warmup_bars: int = Field(default=200, ge=50, le=500)


class OptimizeRequest(BaseModel):
    strategy: str = Field(default="fibonacci")
    symbol: str = Field(default="EURUSD")
    timeframe: str = Field(default="H1")
    bars: int = Field(default=5000, ge=100, le=50000)
    param_grid: dict = Field(
        description="Parameter grid for optimization",
        default={"swing_lookback": [30, 50, 70], "tp_extension": [1.272, 1.618, 2.0]},
    )
    rank_by: str = Field(default="sharpe_ratio")


class TradeAuditMetadata(BaseModel):
    """Signal metadata from strategy (all optional for backward compat)."""
    daily_bias: str | None = None
    pdh: float | None = None
    pdl: float | None = None
    manipulation_type: str | None = None
    manipulation_level: float | None = None
    choch_detected: bool | None = None
    entropy: float | None = None
    entropy_zscore: float | None = None
    ml_confidence: float | None = None
    risk_percent: float | None = None
    fvg_tp: float | None = None


class TradeAudit(BaseModel):
    """Individual trade with full audit metadata."""
    entry_price: float
    exit_price: float
    direction: str
    lot_size: float
    profit: float
    commission: float
    gross_profit: float
    stop_loss: float
    take_profit: float
    bar_index: int
    exit_reason: str = ""
    entry_time: str | None = None
    risk_reward: float = 0.0
    effective_risk: float = 1.0
    signal_metadata: TradeAuditMetadata = Field(
        default_factory=TradeAuditMetadata
    )


class SessionMetrics(BaseModel):
    trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_profit: float = 0.0


class SessionAnalysis(BaseModel):
    london: SessionMetrics = Field(default_factory=SessionMetrics)
    ny: SessionMetrics = Field(default_factory=SessionMetrics)


class BuySellDistribution(BaseModel):
    buy_count: int = 0
    sell_count: int = 0
    buy_pct: float = 0.0
    sell_pct: float = 0.0
    ratio: float = 0.0


class BacktestResponse(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    total_trades: int
    win_rate: float
    net_profit: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    max_drawdown_percent: float
    initial_balance: float
    final_balance: float
    return_percent: float
    total_bars: int
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    expectancy: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_loss: float
    equity_curve: list[float] = []
    trades: list[TradeAudit] = []
    # Date range fields
    date_from: str | None = None
    date_to: str | None = None
    warmup_bars: int = 0
    # Analysis
    session_analysis: SessionAnalysis | None = None
    buy_sell_distribution: BuySellDistribution | None = None
