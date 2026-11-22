
"""Groq API integration using the OpenAI-compatible SDK."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

from app.ai.base import BaseLLMProvider, LLMProviderError


class GroqProvider(BaseLLMProvider):
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")

        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
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
                    "Groq returned an empty response."
                )

            result = json.loads(content)

            if not isinstance(result, dict):
                raise LLMProviderError(
                    "Groq returned an invalid JSON object."
                )

            return result

        except (OpenAIError, json.JSONDecodeError) as exc:
            raise LLMProviderError(
                "Groq summarization request failed."
            ) from exc
