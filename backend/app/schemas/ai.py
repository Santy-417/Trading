from pydantic import BaseModel, Field


class AnalyzeTradesRequest(BaseModel):
    symbol: str | None = None
    strategy: str | None = None
    days: int = Field(default=7, ge=1, le=90)


class ExplainDrawdownRequest(BaseModel):
    peak_balance: float
    trough_balance: float
    drawdown_percent: float
    period_start: str
    period_end: str
    trades_during: int = 0


class SuggestParametersRequest(BaseModel):
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    current_risk_per_trade: float = 1.0


class RiskReviewRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=90)


class PerformanceSummaryRequest(BaseModel):
    period: str = Field(default="weekly", pattern="^(weekly|monthly)$")


class StrategyComparisonRequest(BaseModel):
    strategies: list[str] = Field(min_length=2, max_length=5)
    days: int = Field(default=30, ge=7, le=90)


class AIResponse(BaseModel):
    analysis: str
    model_used: str = "gpt-4o-mini"
