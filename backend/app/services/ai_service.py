"""AI Analysis service — orchestrates LLM-based trade analysis."""

import logging

from app.ai_analysis.llm_client import get_llm_client
from app.ai_analysis.performance_summary import PerformanceSummary
from app.ai_analysis.risk_review import RiskReview
from app.ai_analysis.trade_analyzer import TradeAnalyzer

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.llm = get_llm_client()
        self.trade_analyzer = TradeAnalyzer(self.llm)
        self.risk_review = RiskReview(self.llm)
        self._perf_summary = PerformanceSummary(self.llm)

    async def analyze_trades(self, trades_data: dict) -> str:
        logger.info("AI analyzing trades")
        return await self.trade_analyzer.analyze_trades(trades_data)

    async def explain_drawdown(self, drawdown_data: dict) -> str:
        logger.info("AI explaining drawdown")
        return await self.trade_analyzer.explain_drawdown(drawdown_data)

    async def suggest_parameters(self, performance_data: dict) -> str:
        logger.info("AI suggesting parameters")
        return await self.trade_analyzer.suggest_parameters(performance_data)

    async def review_risk(self, risk_events: list[dict]) -> str:
        logger.info("AI reviewing risk events: count=%d", len(risk_events))
        return await self.risk_review.review_risk_events(risk_events)

    async def performance_summary(self, metrics: dict, period: str = "weekly") -> str:
        logger.info("AI generating %s performance summary", period)
        if period == "monthly":
            return await self._perf_summary.monthly_report(metrics)
        return await self._perf_summary.weekly_summary(metrics)

    async def compare_strategies(self, strategies_data: dict) -> str:
        logger.info("AI comparing strategies: %s", list(strategies_data.keys()))
        return await self._perf_summary.strategy_comparison(strategies_data)
