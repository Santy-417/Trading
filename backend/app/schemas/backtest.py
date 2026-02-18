from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy: str = Field(default="fibonacci")
    symbol: str = Field(default="EURUSD")
    timeframe: str = Field(default="H1")
    bars: int = Field(default=5000, ge=100, le=50000)
    initial_balance: float = Field(default=10000.0, ge=100)
    risk_per_trade: float = Field(default=1.0, ge=0.1, le=5.0)
    lot_mode: str = Field(default="percent_risk")
    strategy_params: dict | None = None


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


class BacktestResponse(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    total_trades: int
    win_rate: float
    net_profit: float
    profit_factor: float
    sharpe_ratio: float
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
