
"""Common interface for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot complete a request."""


class BaseLLMProvider(ABC):
    """Contract implemented by all summarization providers."""

    @abstractmethod
    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON object from the supplied prompts."""
        raise NotImplementedError
