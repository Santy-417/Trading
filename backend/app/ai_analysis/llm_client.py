"""LLM client abstraction — currently OpenAI, designed for future Claude/Local support."""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        ...


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or get_settings().openai_api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key is not configured")

        temperature = kwargs.get("temperature", 0.3)
        max_tokens = kwargs.get("max_tokens", 2000)

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class MockLLMClient(BaseLLMClient):
    """Mock client for testing without an API key."""

    async def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return (
            "AI analysis is not available — no API key configured. "
            "Set OPENAI_API_KEY in your .env to enable AI-powered analysis."
        )


def get_llm_client() -> BaseLLMClient:
    settings = get_settings()
    if settings.openai_api_key:
        logger.info("Using OpenAI LLM client (model=gpt-4o-mini)")
        return OpenAIClient()
    logger.warning("No OpenAI API key found, using mock LLM client")
    return MockLLMClient()
