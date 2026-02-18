"""Generate natural language performance summaries."""

import logging

from app.ai_analysis.llm_client import BaseLLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional trading performance analyst. Generate clear, concise
performance summaries. Structure your response with:
1. Executive Summary (2-3 sentences)
2. Key Metrics Highlights
3. Strengths
4. Areas for Improvement
5. Actionable Recommendations

Use professional tone. Include specific numbers from the data. Respond in the same language."""


class PerformanceSummary:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    async def weekly_summary(self, metrics: dict) -> str:
        prompt = (
            "Generate a weekly trading performance summary based on this data:\n\n"
            + _format_metrics(metrics)
        )
        return await self.llm.chat(SYSTEM_PROMPT, prompt)

    async def strategy_comparison(self, strategies_data: dict) -> str:
        prompt = "Compare the performance of these trading strategies:\n\n"
        for name, data in strategies_data.items():
            prompt += f"Strategy '{name}':\n"
            prompt += _format_metrics(data) + "\n"
        prompt += "Which strategy is performing best and why?"
        return await self.llm.chat(SYSTEM_PROMPT, prompt)

    async def monthly_report(self, monthly_data: dict) -> str:
        prompt = (
            "Generate a comprehensive monthly trading report:\n\n"
            + _format_metrics(monthly_data)
        )
        return await self.llm.chat(SYSTEM_PROMPT, prompt, max_tokens=3000)


def _format_metrics(data: dict) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:.2f}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)
