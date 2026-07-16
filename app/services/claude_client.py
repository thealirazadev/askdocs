"""Thin wrapper around the Anthropic SDK for answer composition.

The only place the anthropic package is imported. A single non-streaming messages.create call
per question; no second LLM provider, no streaming.
"""

import anthropic

from app.errors import ModelApiError

MAX_TOKENS = 1024


class ClaudeClient:
    def __init__(self, api_key: str, model: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user_message: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APIError as exc:
            raise ModelApiError("The Claude API request failed. Please try again.") from exc
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
