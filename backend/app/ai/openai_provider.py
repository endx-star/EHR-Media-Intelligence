
"""OpenAI API integration."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

from app.ai.base import BaseLLMProvider, LLMProviderError


class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")

        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            timeout=45.0,
            max_retries=2,
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            content = response.choices[0].message.content

            if not content:
                raise LLMProviderError(
                    "OpenAI returned an empty response."
                )

            result = json.loads(content)

            if not isinstance(result, dict):
                raise LLMProviderError(
                    "OpenAI returned an invalid JSON object."
                )

            return result

        except (OpenAIError, json.JSONDecodeError) as exc:
            raise LLMProviderError(
                "OpenAI summarization request failed."
            ) from exc
