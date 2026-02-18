"""AI Analysis endpoints — LLM never executes trades, only analyzes."""

import logging

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.ai import (
    AIResponse,
    AnalyzeTradesRequest,
    ExplainDrawdownRequest,
    PerformanceSummaryRequest,
    RiskReviewRequest,
    StrategyComparisonRequest,
    SuggestParametersRequest,
)
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Analysis"])


def _get_ai_service() -> AIService:
    return AIService()


@router.post("/analyze-trades", response_model=AIResponse)
async def analyze_trades(
    request: AnalyzeTradesRequest,
    _user=Depends(get_current_user),
    service: AIService = Depends(_get_ai_service),
):
    trades_data = {
        "symbol": request.symbol or "all",
        "strategy": request.strategy or "all",
        "period_days": request.days,
    }
    result = await service.analyze_trades(trades_data)
    return AIResponse(analysis=result)


@router.post("/explain-drawdown", response_model=AIResponse)
async def explain_drawdown(
    request: ExplainDrawdownRequest,
    _user=Depends(get_current_user),
    service: AIService = Depends(_get_ai_service),
):
    result = await service.explain_drawdown(request.model_dump())
    return AIResponse(analysis=result)


@router.post("/suggest-parameters", response_model=AIResponse)
async def suggest_parameters(
    request: SuggestParametersRequest,
    _user=Depends(get_current_user),
    service: AIService = Depends(_get_ai_service),
):
    result = await service.suggest_parameters(request.model_dump())
    return AIResponse(analysis=result)


@router.post("/risk-review", response_model=AIResponse)
async def risk_review(
    request: RiskReviewRequest,
    _user=Depends(get_current_user),
    service: AIService = Depends(_get_ai_service),
):
    result = await service.review_risk([])
    return AIResponse(analysis=result)


@router.post("/performance-summary", response_model=AIResponse)
async def performance_summary(
    request: PerformanceSummaryRequest,
    _user=Depends(get_current_user),
    service: AIService = Depends(_get_ai_service),
):
    metrics = {"period": request.period}
    result = await service.performance_summary(metrics, request.period)
    return AIResponse(analysis=result)


@router.post("/compare-strategies", response_model=AIResponse)
async def compare_strategies(
    request: StrategyComparisonRequest,
    _user=Depends(get_current_user),
    service: AIService = Depends(_get_ai_service),
):
    strategies_data = {s: {} for s in request.strategies}
    result = await service.compare_strategies(strategies_data)
    return AIResponse(analysis=result)
