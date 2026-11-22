
"""Construct the configured LLM provider."""

from app.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
)

from app.ai.base import BaseLLMProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.groq_provider import GroqProvider
from app.ai.mock_provider import MockProvider


def get_llm_provider() -> BaseLLMProvider:
    provider = LLM_PROVIDER

    if provider == "openai":
        return OpenAIProvider(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
        )

    if provider == "groq":
        return GroqProvider(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
        )

    if provider == "mock":
        return MockProvider()

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider}"
    )
