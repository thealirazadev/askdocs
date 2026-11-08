import json

import anthropic
import httpx
import pytest

from app.errors import ModelApiError
from app.services.claude_client import MAX_TOKENS, ClaudeClient


def client_with(handler) -> ClaudeClient:
    client = ClaudeClient("test-key", "claude-opus-5-5")
    client._client = anthropic.Anthropic(
        api_key="test-key",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return client


def test_complete_sends_one_request_and_joins_text_blocks():
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "Thirty "}, {"type": "text", "text": "days."}],
                "usage": {"input_tokens": 10, "output_tokens": 3},
            },
        )

    assert client_with(handler).complete("system", "question") == "Thirty days."
    assert sent[0]["model"] == "claude-opus-5-5"
    assert sent[0]["max_tokens"] == MAX_TOKENS
    assert sent[0]["system"] == "system"


def test_api_errors_become_a_friendly_model_error():
    def handler(request):
        return httpx.Response(500, json={"type": "error", "error": {"type": "api_error"}})

    with pytest.raises(ModelApiError):
        client_with(handler).complete("system", "question")
