from types import SimpleNamespace

import httpx
from openai import RateLimitError

from app.ai import providers
from app.ai.config import settings


def test_chat_completion_fails_over_from_mocked_groq_429_to_huggingface(monkeypatch):
    providers._circuit_until.clear()
    providers._provider_failures.clear()
    monkeypatch.setattr(settings, "llm_provider_order", "groq,hf,ollama")
    monkeypatch.setattr(settings, "groq_api_key", "test-groq-key")
    monkeypatch.setattr(settings, "groq_model", "test-groq-model")
    monkeypatch.setattr(settings, "hf_token", "test-hf-token")
    monkeypatch.setattr(settings, "hf_model", "test-hf-model")
    monkeypatch.setattr(settings, "llm_max_retries", 0)

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request, headers={"Retry-After": "0"})
    rate_limit = RateLimitError("rate limited", response=response, body={"error": "rate limited"})
    contacted = []

    class MockClient:
        def __init__(self, *, base_url, **_kwargs):
            self.base_url = str(base_url)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **_kwargs):
            contacted.append(self.base_url)
            if "groq" in self.base_url:
                raise rate_limit
            message = SimpleNamespace(content="fallback provider", tool_calls=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(providers, "OpenAI", MockClient)
    result = providers.chat_completion([{"role": "user", "content": "hello"}], [])

    assert result[0] == "hf"
    assert result[1] == "test-hf-model"
    assert contacted == ["https://api.groq.com/openai/v1", "https://router.huggingface.co/v1"]
    assert providers._circuit_until["groq"] > providers.monotonic()
