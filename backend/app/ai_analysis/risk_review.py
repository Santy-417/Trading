"""AI-powered risk anomaly detection and review."""

import logging

from app.ai_analysis.llm_client import BaseLLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a risk management specialist for Forex trading. Analyze the provided
risk data and identify anomalies, concerning patterns, and potential improvements.
Focus on:
- Unusual position sizing
- Correlation between losses and specific conditions
- Circuit breaker trigger analysis
- Overtrading patterns
- Drawdown progression

Be precise and highlight severity (LOW, MEDIUM, HIGH, CRITICAL). Respond in the same language."""


class RiskReview:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    async def review_risk_events(self, risk_events: list[dict]) -> str:
        if not risk_events:
            return "No risk events to review."

        prompt = "Review these risk events and identify patterns or concerns:\n\n"
        for i, event in enumerate(risk_events[-30:], 1):
            prompt += f"Event {i}: {event}\n"
        return await self.llm.chat(SYSTEM_PROMPT, prompt)

    async def review_position_sizing(self, trades: list[dict], account_info: dict) -> str:
        prompt = (
            f"Review position sizing for this account:\n"
            f"Account: {account_info}\n\n"
            f"Recent trades (last 20):\n"
        )
        for trade in trades[-20:]:
            prompt += f"  {trade}\n"
        prompt += "\nAre position sizes appropriate for the account? Any concerns?"
        return await self.llm.chat(SYSTEM_PROMPT, prompt)
