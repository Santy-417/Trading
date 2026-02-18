"""Analyze trading patterns and provide AI-driven insights."""

import logging

from app.ai_analysis.llm_client import BaseLLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional Forex trading analyst. Analyze the provided trading data
and give clear, actionable insights. Focus on:
- Pattern recognition in winning vs losing trades
- Risk management effectiveness
- Strategy performance comparison
- Time-of-day and session analysis
- Suggested improvements

Be concise, data-driven, and specific. Use bullet points. Respond in the same language as the user."""


class TradeAnalyzer:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    async def analyze_trades(self, trades_data: dict) -> str:
        user_prompt = self._build_trades_prompt(trades_data)
        logger.info("Requesting trade analysis from LLM")
        return await self.llm.chat(SYSTEM_PROMPT, user_prompt)

    async def explain_drawdown(self, drawdown_data: dict) -> str:
        prompt = (
            "Analyze this drawdown event and explain what likely caused it. "
            "Suggest risk management adjustments to prevent similar events.\n\n"
            f"Drawdown data:\n{_format_dict(drawdown_data)}"
        )
        return await self.llm.chat(SYSTEM_PROMPT, prompt)

    async def suggest_parameters(self, performance_data: dict) -> str:
        prompt = (
            "Based on the following trading performance, suggest optimal parameter adjustments "
            "for risk per trade, max daily loss, and strategy settings.\n\n"
            f"Performance:\n{_format_dict(performance_data)}"
        )
        return await self.llm.chat(SYSTEM_PROMPT, prompt)

    def _build_trades_prompt(self, data: dict) -> str:
        lines = ["Analyze the following trading activity:\n"]
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 20:
                lines.append(f"- {key}: [{len(value)} items, showing last 20]")
                for item in value[-20:]:
                    lines.append(f"  {item}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)


def _format_dict(d: dict) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in d.items())
